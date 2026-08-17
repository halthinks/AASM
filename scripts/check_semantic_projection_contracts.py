from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def text(path: str) -> str:
    target = ROOT / path
    require(target.exists(), f"missing required semantic projection file: {path}")
    return target.read_text(encoding="utf-8")


def main() -> None:
    model = "\n".join((text("src/aasm/semantic_projection.py"), text("src/aasm/_semantic_projection_core.py"), text("src/aasm/_semantic_projection_equivalence.py")))
    schema_text = text("schemas/semantic-projection.schema.json")
    tests = "\n".join((
        text("tests/test_semantic_projection_foundation.py"),
        text("tests/test_semantic_projection_textpcb.py"),
        text("tests/test_semantic_projection_adversarial.py"),
    ))
    runtime = text("src/aasm/runtime_v56_foundation.py")
    public = text("src/aasm/public_active.py")
    quantity = text("src/aasm/quantity.py")
    artifact = text("src/aasm/artifact_lineage.py")
    solver_outcome = text("src/aasm/solver_outcome_v2.py")
    trace = text("src/aasm/trace_conformance.py")
    pools = text("src/aasm/solution_pools.py")
    reuse = text("src/aasm/reuse_validation.py")
    decision_vector = text("src/aasm/decision_vector_ir.py")

    schema = json.loads(schema_text)
    for name in (
        "invariantRef",
        "subjectRef",
        "projectionDefinition",
        "projectionResult",
        "equivalenceAssessment",
    ):
        require(
            schema["$defs"][name].get("additionalProperties") is False,
            f"semantic projection schema nested object is not closed: {name}",
        )
    require(
        schema["$defs"]["projectionDefinition"]["properties"]["contract_id"]["const"]
        == "aasm.semantic.projection.v1",
        "semantic projection schema contract ID drift",
    )
    require(
        schema["$defs"]["equivalenceAssessment"]["properties"]["contract_id"]["const"]
        == "aasm.semantic.equivalence.v1",
        "semantic equivalence schema contract ID drift",
    )
    require(
        schema["$defs"]["invariantRef"]["properties"]["classification"]["enum"]
        == ["REPRESENTATIONAL", "STATIC_PROTOCOL", "DYNAMIC_KERNEL", "EMPIRICAL"],
        "aasm.invariant.v1 classification schema drift",
    )

    required_model_tokens = (
        'SEMANTIC_PROJECTION_CONTRACT_ID = "aasm.semantic.projection.v1"',
        'SEMANTIC_EQUIVALENCE_CONTRACT_ID = "aasm.semantic.equivalence.v1"',
        'INVARIANT_CONTRACT_ID = "aasm.invariant.v1"',
        '"REPRESENTATIONAL"',
        '"STATIC_PROTOCOL"',
        '"DYNAMIC_KERNEL"',
        '"EMPIRICAL"',
        '"EXACT_IDENTITY"',
        '"PROJECTION_EQUIVALENT"',
        '"NON_EQUIVALENT"',
        '"INDETERMINATE"',
        '"UNSUPPORTED"',
        '"LOSSLESS"',
        '"LOSSY"',
        '"EXACT_MATCH_REQUIRED"',
        '"EXPLICIT_CROSS_REVISION"',
        "class InvariantRef",
        "class SemanticSubjectRef",
        "class SemanticProjectionDefinition",
        "class SemanticProjectionResult",
        "class SemanticEquivalenceAssessment",
        "def assess_semantic_equivalence",
        "def invariant_contract",
        "def semantic_projection_contract",
        '"RELATIVE_TO_EXACT_EXPLICIT_PROJECTION_ONLY"',
        '"MUST_DECLARE_DISCARDED_SEMANTICS_OR_INVARIANTS_AND_NEVER_BECOMES_EXACT_IDENTITY"',
        '"REFERENCES_EXISTING_OBJECT_FINGERPRINTS_DOES_NOT_DEFINE_SECOND_OBJECT_IDENTITY_PLANE"',
        '"NOT_REINTERPRETED_OR_ADMITTED_BY_FOUNDATION"',
        '"parallel_projection_registry": "NONE"',
        '"current_projection_pointer": "NONE"',
        '"runtime_admission": "PRE_ADMISSION_ONLY"',
        '"public_admission": "PRE_ADMISSION_ONLY"',
        '"reuse_admission": "NONE"',
        '"proof_authority": "NONE"',
        "binary floating-point values are forbidden in semantic projection portable identity",
    )
    for token in required_model_tokens:
        require(token in model, f"semantic projection model contract missing token: {token}")

    banned_model_tokens = (
        "FactAuthority(",
        "StateClaim(",
        ".authorize_effect(",
        ".execute_effect(",
        "dispatch_effect(",
        "authorize_scoped_request(",
        "register_projection(",
        "PROJECTION_REGISTRY =",
        "projection_registry[",
        "latest_projection",
        "current_projection_store",
        "datetime.now(",
        "time.time(",
        "eval(",
        "exec(",
    )
    for token in banned_model_tokens:
        require(token not in model, f"semantic projection model violates source firewall with token: {token}")

    required_test_tokens = (
        "test_projection_contract_relations_and_invariant_classifications_are_exact",
        "test_invariant_contract_prevents_static_or_representational_equivalence_from_becoming_proof",
        "test_projection_definition_identity_is_deterministic_and_round_trips",
        "test_lossless_projection_rejects_any_declared_discard",
        "test_lossy_projection_requires_explicit_loss_not_a_bare_same_enough_flag",
        "test_portable_identity_rejects_binary_float_metadata",
        "test_exact_identity_requires_same_type_object_fingerprint_and_revision_binding",
        "test_same_projected_fingerprint_is_projection_equivalence_not_exact_identity",
        "test_lossy_textpcb_alternatives_remain_only_projection_equivalent",
        "test_textpcb_cross_format_artifacts_can_be_projection_equivalent_without_becoming_same_artifact",
        "test_projected_fingerprint_difference_is_non_equivalence_only_under_that_projection",
        "test_unsupported_and_indeterminate_projection_results_remain_distinct",
        "test_exact_revision_policy_fails_closed_across_revision_mismatch",
        "test_explicit_cross_revision_policy_allows_only_projection_relative_comparison",
        "test_subject_type_projection_id_and_projection_fingerprint_attacks_fail_closed",
        "test_definition_result_and_assessment_fingerprint_tampering_fail_closed",
        "test_equivalence_assessment_is_symmetric_and_order_independent",
        "test_schema_is_closed_and_carries_exact_projection_equivalence_and_invariant_vocabularies",
        "test_foundation_claim_ceiling_blocks_truth_authority_acceptance_proof_preference_and_reuse",
        "test_existing_projection_substrates_remain_uncomposed_pre_admission",
    )
    for token in required_test_tokens:
        require(token in tests, f"semantic projection adversarial corpus missing test: {token}")

    # S4.3 is deliberately pre-admission. Existing narrow projection/equality
    # mechanisms stay the authoritative implementations for their own domains.
    for source, label in (
        (runtime, "runtime_v56_foundation"),
        (public, "active public root"),
        (quantity, "Quantity foundation"),
        (artifact, "artifact lineage"),
        (solver_outcome, "solver outcome v2"),
        (trace, "trace conformance"),
        (pools, "solution pools"),
        (reuse, "reuse validation"),
        (decision_vector, "decision vector"),
    ):
        require("from .semantic_projection" not in source, f"semantic projection leaked into {label}")
        require("aasm.semantic.projection.v1" not in source, f"semantic projection contract leaked into {label}")
        require("aasm.semantic.equivalence.v1" not in source, f"semantic equivalence contract leaked into {label}")

    require("canonical_projection_fingerprint" in quantity, "Quantity canonical projection seam drift")
    require("semantic_projection_sha256" in artifact, "artifact semantic projection seam drift")
    require("class LegacyStatusProjection" in solver_outcome, "solver legacy projection seam drift")
    require('"lossy": bool(self.lossy)' in solver_outcome, "solver lossy projection declaration drift")
    require('"unknown_transition_policy": "UNSUPPORTED_EXPLICIT"' in trace, "trace unsupported projection policy drift")
    require('"deduplication": "EXACT_CANONICAL_ASSIGNMENT_FINGERPRINT"' in pools, "solution-pool exact identity drift")
    require('"CERTIFIED_EQUIVALENT" in candidate.reusable_modes' in reuse, "existing reuse equivalence seam drift")
    require("class GovernedDecisionVector" in decision_vector, "decision-vector substrate drift")

    print("S4 semantic projection/equivalence pre-admission foundation source contracts: PASS")


if __name__ == "__main__":
    main()
