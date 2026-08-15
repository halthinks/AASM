from __future__ import annotations

import json
from pathlib import Path

from aasm.model_features import (
    ModelFeatureRequirement,
    ModelFeatureSet,
    ProviderCapabilityManifest,
    ProviderFeatureSupport,
    evaluate_model_admission,
)
from aasm.scheduling_ir import (
    SCHEDULING_MODEL_CONTRACT_ID,
    SCHEDULING_PROVIDER_BINDING_CONTRACT_ID,
    SCHEDULING_VALIDATION_CONTRACT_ID,
    CumulativeResourceConstraint,
    NoOverlapConstraint,
    PrecedenceConstraint,
    SchedulingAssignment,
    SchedulingModel,
    SchedulingTask,
    bind_scheduling_provider,
    scheduling_ir_contract,
    validate_scheduling_assignment,
)

ROOT = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def main() -> None:
    contract = scheduling_ir_contract()
    require(contract["model_contract_id"] == SCHEDULING_MODEL_CONTRACT_ID, "scheduling model contract drift")
    require(contract["validation_contract_id"] == SCHEDULING_VALIDATION_CONTRACT_ID, "scheduling validation contract drift")
    require(contract["provider_binding_contract_id"] == SCHEDULING_PROVIDER_BINDING_CONTRACT_ID, "scheduling provider binding contract drift")
    require(contract["execution_adapter"] == "NOT_CLAIMED_BY_THIS_FOUNDATION", "scheduling foundation must not overclaim provider execution")
    require(contract["provider_admission"] == "GLOBAL_SCHEDULING_EXACT_NATIVE_REQUIRED", "scheduling provider admission must fail closed")
    require(contract["truth_authority"] == "NONE", "scheduling foundation may not grant truth authority")

    schema_contracts = {
        "scheduling-model.schema.json": SCHEDULING_MODEL_CONTRACT_ID,
        "scheduling-validation.schema.json": SCHEDULING_VALIDATION_CONTRACT_ID,
        "scheduling-provider-binding.schema.json": SCHEDULING_PROVIDER_BINDING_CONTRACT_ID,
    }
    for filename, contract_id in schema_contracts.items():
        data = json.loads((ROOT / "schemas" / filename).read_text(encoding="utf-8"))
        require(data["properties"]["contract_id"]["const"] == contract_id, f"schema contract drift: {filename}")

    model = SchedulingModel(
        "v55 scheduling gate",
        16,
        (
            SchedulingTask("place", 3, source_reference_fingerprints=("textpcb:req:place",)),
            SchedulingTask("route", 4, source_reference_fingerprints=("textpcb:req:route",)),
            SchedulingTask("verify", 2, source_reference_fingerprints=("textpcb:req:verify",)),
        ),
        precedences=(PrecedenceConstraint("place", "route", min_lag=1, constraint_id="place-before-route"),),
        no_overlaps=(NoOverlapConstraint(("route", "verify"), constraint_id="shared-station"),),
        cumulative_resources=(CumulativeResourceConstraint("expert", 2, {"route": 2, "verify": 1}, constraint_id="expert-capacity"),),
    )
    assignment = SchedulingAssignment(model.model_id, model.fingerprint, {"place": 0, "route": 4, "verify": 8})
    validation = validate_scheduling_assignment(model, assignment)
    require(validation.valid, "reference scheduling assignment must independently validate")

    features = ModelFeatureSet(model.fingerprint, (ModelFeatureRequirement("GLOBAL_SCHEDULING", "EXACT_ONLY"),))
    manifest = ProviderCapabilityManifest(
        "v55-cpsat-scheduler",
        "1",
        "aasm.cpsat-scheduling",
        "1",
        (ProviderFeatureSupport("GLOBAL_SCHEDULING", "EXACT_NATIVE"),),
        solver_families=("CP_SAT",),
        environment_fingerprint="scheduling-env",
    )
    admission = evaluate_model_admission(features, manifest)
    require(admission.admitted and admission.exact, "reference scheduling provider must receive exact admission")
    binding = bind_scheduling_provider(model, feature_set=features, provider_manifest=manifest, admission_report=admission)
    require(binding.model_fingerprint == model.fingerprint, "scheduling provider binding must pin exact model")
    require(binding.provider_manifest_fingerprint == manifest.fingerprint, "scheduling provider binding must pin exact manifest")
    print("v0.55 portable global scheduling IR contracts: PASS")


if __name__ == "__main__":
    main()
