from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def text(path: str) -> str:
    target = ROOT / path
    require(target.exists(), f"missing S5.1 refinement file: {path}")
    return target.read_text(encoding="utf-8")


def main() -> None:
    model = text("src/aasm/refinement.py")
    proposal_schema = json.loads(text("schemas/refinement-proposal.schema.json"))
    loop_schema = json.loads(text("schemas/refinement-loop.schema.json"))
    tests = text("tests/test_refinement_foundation.py")
    workflow = text(".github/workflows/refinement.yml")
    semantic_evolution = text("src/aasm/semantic_evolution.py")
    runtime = text("src/aasm/runtime_v56_foundation.py")
    public = text("src/aasm/public_active_degraded_operation.py")

    for token in (
        'REFINEMENT_PROPOSAL_CONTRACT_ID = "aasm.refinement.proposal.v1"',
        'REFINEMENT_LOOP_CONTRACT_ID = "aasm.refinement.loop.v1"',
        '"NO_GOOD"',
        '"BOUND_TIGHTENING"',
        '"NEW_CONSTRAINT"',
        '"DOMAIN_RESTRICTION"',
        '"OBJECTIVE_CORRECTION"',
        '"REQUIRED_OBSERVATION"',
        '"VERIFICATION_ESCALATION"',
        '"MODEL_CORRECTION"',
        '"SCENARIO_ADDITION"',
        '"RULE_APPLICABILITY_CORRECTION"',
        '"GOAL_SATISFIED"',
        '"NO_PROGRESS"',
        '"OSCILLATION"',
        '"RESOURCE_EXHAUSTED"',
        '"INCONCLUSIVE"',
        '"CONFLICT"',
        '"MANUAL_HOLD"',
        "class RefinementApplicability",
        "class RefinementResourceEstimate",
        "class RefinementSemanticEffect",
        "class RefinementProposal",
        "class RefinementValidation",
        "class RefinementApplication",
        "class RefinementLoopTermination",
        "def validate_refinement_validation",
        "def validate_refinement_delta",
        "def validate_refinement_application",
        "def refinement_application_key",
        "def refinement_contract",
        '"FORBIDDEN_ALWAYS_EVALUATOR_OR_PRODUCER_CANNOT_APPLY_OWN_DELTA"',
        '"EXISTING_PROBLEM_DELTA_CAUSED_BY_REFINEMENT_ID_REQUIRED"',
        '"EXISTING_COMMIT_PROBLEM_REVISION_TRANSITION_ONLY_NO_PARALLEL_REVISION_SYSTEM"',
        '"FAIL_CLOSED_EXACT_BASE_REVISION_ID_AND_FINGERPRINT_REQUIRED"',
        '"FORBIDDEN_EXACT_EXPECTED_SEMANTIC_EFFECT_MUST_MATCH_PROBLEM_DELTA"',
        '"PORTABLE_ESTIMATE_ONLY_EXISTING_RESOURCE_GOVERNANCE_REMAINS_REQUIRED"',
        '"resource_estimate_reserves_resources": False',
        '"resource_exhaustion_means_success": False',
        '"inconclusive_means_success": False',
        '"goal_satisfied_termination_mints_truth": False',
        '"proposal_existence_grants_fact_authority": False',
        '"proposal_existence_grants_effect_authority": False',
        '"validation_is_reusable_authorization_token": False',
        '"application_record_grants_fact_authority": False',
        '"application_record_grants_effect_authority": False',
        '"parallel_refinement_store": "NONE_EVIDENCE_PROJECTION_ONLY"',
        '"parallel_problem_revision_system": "NONE"',
        '"parallel_authority_evaluator": "NONE"',
        '"parallel_resource_plane": "NONE"',
        '"parallel_effect_lifecycle": "NONE"',
        '"runtime_admission": "PRE_ADMISSION_ONLY"',
        '"public_admission": "PRE_ADMISSION_ONLY"',
    ):
        require(token in model, f"S5.1 refinement model missing token: {token}")

    for token in (
        "FactAuthority(",
        "StateClaim(",
        "authorize_scoped_request(",
        ".authorize_effect(",
        ".execute_effect(",
        "dispatch_effect(",
        "reserve_resource(",
        "settle_resource(",
        "current_refinement",
        "REFINEMENT_REGISTRY =",
        "REFINEMENT_STORE =",
        "PROBLEM_REVISION_STORE =",
        "datetime.now(",
        "time.time(",
        "random.",
        "eval(",
        "exec(",
    ):
        require(token not in model, f"S5.1 refinement model violates pre-admission firewall: {token}")

    require(
        "from .semantic_evolution import ExternalReference, ProblemDelta, ProblemRevision" in model,
        "S5.1 refinement does not reuse existing semantic-evolution types",
    )
    require(
        "from .semantic_dependencies import SemanticNodeRef" in model,
        "S5.1 refinement does not reuse SemanticNodeRef",
    )
    require(
        'caused_by_refinement_id: str = ""' in semantic_evolution,
        "existing ProblemDelta refinement-lineage field is missing",
    )
    require(
        '"caused_by_refinement_id": self.caused_by_refinement_id' in semantic_evolution,
        "ProblemDelta refinement lineage is not part of durable identity",
    )

    for source, label in ((runtime, "runtime_v56_foundation"), (public, "active public root")):
        require("from .refinement" not in source, f"S5.1 refinement leaked into {label} before admission")
        require("RefinementProposal" not in source, f"S5.1 refinement proposal leaked into {label} before admission")
        require("aasm.refinement.proposal.v1" not in source, f"S5.1 refinement contract leaked into {label} before admission")

    require(proposal_schema.get("additionalProperties") is False, "refinement proposal schema is not closed")
    require(
        proposal_schema["properties"]["contract_id"]["const"] == "aasm.refinement.proposal.v1",
        "refinement proposal schema contract ID drift",
    )
    require(
        proposal_schema["properties"]["contract_version"]["const"] == "0.1.0",
        "refinement proposal schema contract version drift",
    )
    for name, definition in proposal_schema.get("$defs", {}).items():
        require(definition.get("additionalProperties") is False, f"refinement proposal nested schema is not closed: {name}")

    require(len(loop_schema.get("oneOf", [])) == 3, "refinement loop schema must expose exactly validation/application/termination")
    for name in ("validation", "application", "termination"):
        definition = loop_schema["$defs"][name]
        require(definition.get("additionalProperties") is False, f"refinement loop schema is not closed: {name}")
        require(
            definition["properties"]["contract_id"]["const"] == "aasm.refinement.loop.v1",
            f"refinement loop schema contract ID drift: {name}",
        )
        require(
            definition["properties"]["contract_version"]["const"] == "0.1.0",
            f"refinement loop schema contract version drift: {name}",
        )

    for token in (
        "test_refinement_vocabularies_and_contract_are_exact",
        "test_refinement_proposal_identity_is_deterministic_and_round_trips",
        "test_semantic_refinement_identity_ignores_producer_trigger_and_resource_estimate",
        "test_binary_float_payload_metadata_and_resource_estimate_fail_closed",
        "test_applicability_must_bind_exact_base_revision",
        "test_independent_validation_rejects_producer_self_validation",
        "test_valid_validation_is_exact_and_application_eligible",
        "test_validation_fingerprint_tampering_fails_closed",
        "test_exact_refinement_delta_matches_existing_problem_delta_contract",
        "test_delta_cannot_widen_expected_semantic_effect",
        "test_delta_requires_exact_caused_by_refinement_lineage",
        "test_stale_or_wrong_base_revision_fails_closed",
        "test_refinement_dependencies_must_be_applicable_to_base_revision",
        "test_no_progress_and_oscillation_require_existing_blocking_obligation",
        "test_resource_exhausted_and_inconclusive_are_explicit_non_success_terminations",
        "test_application_record_is_provenance_not_authority",
        "test_refinement_schemas_are_closed_and_accept_canonical_documents",
        "test_proposal_schema_rejects_unknown_fields",
    ):
        require(token in tests, f"S5.1 refinement adversarial corpus missing test: {token}")

    for token in (
        "src/aasm/refinement.py",
        "schemas/refinement-proposal.schema.json",
        "schemas/refinement-loop.schema.json",
        "scripts/check_refinement_contracts.py",
        "tests/test_refinement_foundation.py",
        "context='aasm/refinement'",
    ):
        require(token in workflow, f"S5.1 refinement workflow missing token: {token}")

    print("S5.1 governed refinement pre-admission source contracts: PASS")


if __name__ == "__main__":
    main()
