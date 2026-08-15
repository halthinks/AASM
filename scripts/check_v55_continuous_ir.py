from __future__ import annotations

import json
from pathlib import Path

from aasm.continuous_ir import (
    CONTINUOUS_MODEL_CONTRACT_ID,
    CONTINUOUS_PROVIDER_BINDING_CONTRACT_ID,
    CONTINUOUS_VALIDATION_CONTRACT_ID,
    NUMERIC_TOLERANCE_CONTRACT_ID,
    ContinuousAssignment,
    ContinuousModel,
    ContinuousVariable,
    LinearExpression,
    NumericTolerancePolicy,
    QuadraticConstraint,
    QuadraticExpression,
    QuadraticTerm,
    SecondOrderConeConstraint,
    bind_continuous_provider,
    continuous_ir_contract,
    validate_continuous_assignment,
)
from aasm.model_features import (
    ModelFeatureRequirement,
    ModelFeatureSet,
    ProviderCapabilityManifest,
    ProviderFeatureSupport,
    evaluate_model_admission,
)

ROOT = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def main() -> None:
    contract = continuous_ir_contract()
    require(contract["model_contract_id"] == CONTINUOUS_MODEL_CONTRACT_ID, "continuous model contract drift")
    require(contract["validation_contract_id"] == CONTINUOUS_VALIDATION_CONTRACT_ID, "continuous validation contract drift")
    require(contract["provider_binding_contract_id"] == CONTINUOUS_PROVIDER_BINDING_CONTRACT_ID, "continuous provider binding contract drift")
    require(contract["numeric_tolerance_contract_id"] == NUMERIC_TOLERANCE_CONTRACT_ID, "numeric tolerance contract drift")
    require(contract["number_encoding"] == "CANONICAL_FINITE_DECIMAL_STRINGS", "continuous numeric encoding must remain deterministic")
    require(contract["execution_adapter"] == "NOT_CLAIMED_BY_THIS_FOUNDATION", "continuous IR foundation must not overclaim execution")
    require(contract["optimality_proof"] == "NOT_CLAIMED_BY_ASSIGNMENT_VALIDATION", "continuous assignment validation must not imply proof")
    require(contract["truth_authority"] == "NONE", "continuous IR may not grant truth authority")

    schemas = {
        "continuous-model.schema.json": CONTINUOUS_MODEL_CONTRACT_ID,
        "continuous-validation.schema.json": CONTINUOUS_VALIDATION_CONTRACT_ID,
        "continuous-provider-binding.schema.json": CONTINUOUS_PROVIDER_BINDING_CONTRACT_ID,
        "numeric-tolerance.schema.json": NUMERIC_TOLERANCE_CONTRACT_ID,
    }
    for filename, contract_id in schemas.items():
        data = json.loads((ROOT / "schemas" / filename).read_text(encoding="utf-8"))
        require(data["properties"]["contract_id"]["const"] == contract_id, f"schema contract drift: {filename}")

    model = ContinuousModel(
        "v55 continuous gate",
        (
            ContinuousVariable("x", "-2", "2"),
            ContinuousVariable("y", "-2", "2"),
            ContinuousVariable("t", "0", "2"),
        ),
        quadratic_constraints=(
            QuadraticConstraint(
                QuadraticExpression(terms=(QuadraticTerm("x", "x", "1"), QuadraticTerm("y", "y", "1"))),
                "<=",
                "1",
                source_reference_fingerprints=("textpcb:req:quadratic-envelope",),
                constraint_id="quadratic-envelope",
            ),
        ),
        conic_constraints=(
            SecondOrderConeConstraint(
                (LinearExpression({"x": "1"}), LinearExpression({"y": "1"})),
                LinearExpression({"t": "1"}),
                source_reference_fingerprints=("textpcb:req:conic-envelope",),
                constraint_id="conic-envelope",
            ),
        ),
    )
    policy = NumericTolerancePolicy("0", "0", precision=60)
    assignment = ContinuousAssignment(model.model_id, model.fingerprint, {"x": "0.6", "y": "0.8", "t": "1"})
    validation = validate_continuous_assignment(model, assignment, policy)
    require(validation.valid, "reference quadratic/conic assignment must independently validate")
    require(validation.tolerance_policy_fingerprint == policy.fingerprint, "continuous validation must pin numeric tolerance policy")

    features = ModelFeatureSet(
        model.fingerprint,
        tuple(ModelFeatureRequirement(feature_id, "EXACT_ONLY") for feature_id in model.required_feature_ids),
    )
    manifest = ProviderCapabilityManifest(
        "v55-continuous-provider",
        "1",
        "aasm.continuous-gate",
        "1",
        tuple(ProviderFeatureSupport(feature_id, "EXACT_NATIVE") for feature_id in model.required_feature_ids),
        environment_fingerprint="continuous-env",
    )
    admission = evaluate_model_admission(features, manifest)
    require(admission.admitted and admission.exact, "reference continuous provider must be exactly admitted")
    binding = bind_continuous_provider(
        model,
        feature_set=features,
        provider_manifest=manifest,
        admission_report=admission,
        tolerance_policy=policy,
    )
    require(binding.model_fingerprint == model.fingerprint, "continuous provider binding must pin exact model")
    require(binding.provider_manifest_fingerprint == manifest.fingerprint, "continuous provider binding must pin exact provider manifest")
    require(binding.tolerance_policy_fingerprint == policy.fingerprint, "continuous provider binding must pin exact tolerance policy")
    print("v0.55 deterministic quadratic/conic IR contracts: PASS")


if __name__ == "__main__":
    main()
