from __future__ import annotations

import json
from pathlib import Path

from aasm.discrete_ir import (
    CARDINALITY_LINEARIZATION_ID,
    DISCRETE_BOOLEAN_MODEL_CONTRACT_ID,
    DISCRETE_LINEARIZATION_CHECKER_ID,
    DISCRETE_LINEARIZATION_CONTRACT_ID,
    DISCRETE_LOWERING_CERTIFICATE_CONTRACT_ID,
    PSEUDO_BOOLEAN_LINEARIZATION_ID,
    CardinalityConstraint,
    DiscreteBooleanModel,
    PseudoBooleanConstraint,
    WeightedBooleanLiteral,
    discrete_ir_contract,
    lower_discrete_boolean_model,
)
from aasm.model_features import (
    ModelFeatureRequirement,
    ModelFeatureSet,
    ProviderCapabilityManifest,
    ProviderFeatureSupport,
    evaluate_model_admission,
)
from aasm.optimization import BooleanLiteral


ROOT = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def main() -> None:
    contract = discrete_ir_contract()
    require(contract["model_contract_id"] == DISCRETE_BOOLEAN_MODEL_CONTRACT_ID, "discrete model contract drift")
    require(contract["linearization_contract_id"] == DISCRETE_LINEARIZATION_CONTRACT_ID, "discrete linearization contract drift")
    require(contract["certificate_contract_id"] == DISCRETE_LOWERING_CERTIFICATE_CONTRACT_ID, "discrete lowering certificate drift")
    require(contract["checker_id"] == DISCRETE_LINEARIZATION_CHECKER_ID, "discrete checker identity drift")
    require(contract["approximation"] == "NOT_SUPPORTED_BY_THIS_CONTRACT", "v0.55 discrete foundation must not silently approximate")
    require(contract["truth_authority"] == "NONE", "discrete lowering may not grant truth authority")

    schemas = {
        "discrete-boolean-model.schema.json": DISCRETE_BOOLEAN_MODEL_CONTRACT_ID,
        "discrete-linearization.schema.json": DISCRETE_LINEARIZATION_CONTRACT_ID,
        "discrete-lowering-certificate.schema.json": DISCRETE_LOWERING_CERTIFICATE_CONTRACT_ID,
    }
    for filename, contract_id in schemas.items():
        data = json.loads((ROOT / "schemas" / filename).read_text(encoding="utf-8"))
        require(data["properties"]["contract_id"]["const"] == contract_id, f"schema contract drift: {filename}")

    source = DiscreteBooleanModel(
        "v55 exact discrete gate",
        ("place_usb", "place_rf", "route_alt"),
        pseudo_boolean_constraints=(
            PseudoBooleanConstraint(
                (
                    WeightedBooleanLiteral("place_usb", True, 3),
                    WeightedBooleanLiteral("place_rf", False, 2),
                    WeightedBooleanLiteral("route_alt", True, 1),
                ),
                "<=",
                4,
                source_reference_fingerprints=("textpcb:req:power",),
                constraint_id="pb-power",
            ),
        ),
        cardinality_constraints=(
            CardinalityConstraint(
                (
                    BooleanLiteral("place_usb"),
                    BooleanLiteral("place_rf"),
                    BooleanLiteral("route_alt"),
                ),
                min_count=1,
                max_count=2,
                source_reference_fingerprints=("textpcb:req:placement",),
                constraint_id="card-placement",
            ),
        ),
    )
    features = ModelFeatureSet(
        source.fingerprint,
        (
            ModelFeatureRequirement("PSEUDO_BOOLEAN", "EXACT_ONLY"),
            ModelFeatureRequirement("CARDINALITY", "EXACT_ONLY"),
        ),
    )
    manifest = ProviderCapabilityManifest(
        "v55-discrete-gate-provider",
        "1",
        "aasm.discrete-gate",
        "1",
        (
            ProviderFeatureSupport("PSEUDO_BOOLEAN", "EXACT_TRANSLATED", transformation_id=PSEUDO_BOOLEAN_LINEARIZATION_ID),
            ProviderFeatureSupport("CARDINALITY", "EXACT_TRANSLATED", transformation_id=CARDINALITY_LINEARIZATION_ID),
        ),
        solver_families=("MILP",),
    )
    admission = evaluate_model_admission(features, manifest)
    require(admission.admitted and admission.exact, "exact discrete provider admission must pass")
    lowering, certificate = lower_discrete_boolean_model(
        source,
        feature_set=features,
        provider_manifest=manifest,
        admission_report=admission,
        target_family="MILP",
    )
    require(certificate.status == "PASS" and certificate.exact, "reference discrete linearization must be independently certified exact")
    require(certificate.mapping_complete and certificate.lineage_preserved, "discrete lowering must preserve complete requirement lineage")
    require(lowering.target_model.solver_family == "MILP", "reference discrete linearization target family drift")
    require({row.source_constraint_id for row in lowering.mappings} == {"pb-power", "card-placement"}, "reference discrete source mapping is incomplete")
    print("v0.55 exact pseudo-Boolean/cardinality IR contracts: PASS")


if __name__ == "__main__":
    main()
