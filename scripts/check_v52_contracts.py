from __future__ import annotations

import json
from pathlib import Path


def require(path: Path, tokens: list[str]) -> None:
    text = path.read_text()
    missing = [token for token in tokens if token not in text]
    if missing:
        raise SystemExit(f"{path}: missing v0.52 contract tokens {missing}")


def forbid(path: Path, tokens: list[str]) -> None:
    text = path.read_text()
    present = [token for token in tokens if token in text]
    if present:
        raise SystemExit(f"{path}: forbidden v0.52 pre-release side effects {present}")


def schema(root: Path, name: str) -> dict:
    path = root / "schemas" / name
    if not path.exists():
        raise SystemExit(f"missing v0.52 schema: {name}")
    data = json.loads(path.read_text())
    if not str(data.get("$schema", "")).startswith("https://json-schema.org/"):
        raise SystemExit(f"invalid schema declaration: {name}")
    return data


def main() -> None:
    root = Path(__file__).resolve().parents[1]

    # Exact finite multi-objective semantics must stay on the v0.51 certified
    # enumeration substrate and must preserve the Evidence-only boundary.
    require(root / "src/aasm/multi_objective.py", [
        'MULTI_OBJECTIVE_CONTRACT_ID = "aasm.optimization.multi-objective.v1"',
        'FRONTIER_CONTRACT_ID = "aasm.optimization.frontier.v1"',
        '"exact_finite_basis": "V0.51_COMPLETE_FINITE_ENUMERATION_CERTIFICATE_REQUIRED"',
        '"result_authority": "EVIDENCE_ONLY"',
        '"truth_authority": "EXISTING_AASM_POLICY_ONLY"',
        "solve_lexicographic_finite",
        "solve_exact_finite_pareto_frontier",
        "verify_exact_finite_pareto_frontier",
        "expected_by_id = {row.solution_id: row.to_dict() for row in expected}",
        "actual_by_id = {row.solution_id: row.to_dict() for row in frontier.points}",
        "exact_points_match = actual_by_id == expected_by_id",
        "enumeration_certificate.certificate_id != independent_certificate.certificate_id",
        "left <= right + objective.tolerance",
        "left >= right - objective.tolerance",
        "left < right - objective.tolerance",
        "left > right + objective.tolerance",
    ])

    # Resource routing must expose the complete known product vector explicitly,
    # not infer provider quota burn from resource names/provider strings.
    require(root / "src/aasm/resource_routing.py", [
        'RESOURCE_ROUTING_CONTRACT_ID = "aasm.resource.routing.v1"',
        '"correctness"',
        '"evidence_quality"',
        '"expected_progress"',
        '"provider_quota_burn"',
        '"monetary_cost"',
        '"wall_time_seconds"',
        '"scarce_expert_usage"',
        "ResourceRoutingObjective",
        "default_resource_routing_objectives",
        "resource_candidate_pareto_frontier",
        '"authority": "EVIDENCE_ONLY"',
    ])

    require(root / "src/aasm/sii_v52.py", [
        'SII_RESOURCE_AWARE_PROPOSAL_CONTRACT_ID = "aasm.sii.resource-aware-proposal.v1"',
        "expected_provider_quota_burn",
        '"expected_provider_quota_burn": self.expected_provider_quota_burn',
        "provider_quota_burn=float(self.expected_provider_quota_burn or 0.0)",
    ])

    require(root / "src/aasm/runtime_v52.py", [
        "solve_lexicographic_multi_objective",
        "solve_exact_pareto_multi_objective",
        "record_resource_candidate_pareto_frontier",
        "pareto_resource_aware_sii_proposals",
        "resource_routing_explanation_report",
        '"candidate_objectives"',
        '"objectives": [row.to_dict() for row in policy.objectives]',
        '"authority": "EVIDENCE_ONLY"',
        "uncertified lexicographic result is not durable-admissible",
        "uncertified exact Pareto frontier is not durable-admissible",
    ])

    # Re-estimation/replay/resource-state semantics must remain on the ordinary
    # AASM Evidence/event path and keep scope/resource rights distinct.
    require(root / "src/aasm/_runtime_v52_resources.py", [
        'RESOURCE_RUNTIME_CONTRACT_ID = "aasm.resource.runtime.v1"',
        '"durability": "EXISTING_AASM_EVIDENCE_EVENT_REPLAY"',
        '"authority": "RESOURCE_STATE_NEVER_GRANTS_AUTHORITY"',
        '"truth": "RESOURCE_OBSERVATIONS_REMAIN_EVIDENCE"',
        "reestimate_resource_reservation",
        '"REPLAN_REQUIRED"',
        "release_resource_reservation",
        "settle_resource_reservation",
    ])

    # v0.52 public surface is intentionally defined and testable before release
    # promotion. The installed/default package remains on v0.51 until promotion.
    public_v52 = root / "src/aasm/public_v52.py"
    require(public_v52, [
        '__version__ = "0.52.0"',
        'PUBLIC_RELEASE_STABILITY = "PRE_RELEASE"',
        '"contract_version": "0.28.0"',
        "from .runtime_v52 import AASMEngine",
        '"multi_objective"',
        '"pareto_frontier"',
        '"resource_governance"',
        '"resource_aware_sii"',
        '"resource_state_authority": "NEVER_GRANTS_AUTHORITY"',
        '"observation_truth": "EVIDENCE_ONLY"',
        '"candidate_frontier_scope": "EXACT_OVER_SUPPLIED_ELIGIBLE_CANDIDATE_SET_ONLY"',
        '"authority_reward": "NEVER"',
        'if PUBLIC_RELEASE_STABILITY != "PRE_RELEASE"',
    ])
    forbid(public_v52, [
        "_demo_stack.AASMEngine = AASMEngine",
        "_demo_stack._runtime_version = lambda: __version__",
    ])
    require(root / "src/aasm/cli_v52.py", [
        "multi-objective-contract",
        "pareto-frontier-contract",
        "resource-routing-contract",
        '"candidate_frontier_scope": "EXACT_OVER_SUPPLIED_ELIGIBLE_CANDIDATE_SET_ONLY"',
        '"result_authority": "EVIDENCE_ONLY"',
        '"resource_state_authority": "NEVER_GRANTS_AUTHORITY"',
    ])
    require(root / "tests/test_v52_public.py", [
        "test_v52_pre_release_public_contract_is_additive_and_valid",
        "test_v52_public_surface_preserves_v51_parent_contract_without_promoting_it",
        "test_v52_pre_release_import_does_not_mutate_active_demo_stack",
        "test_v52_public_surface_exposes_product_backward_resource_objective_vector",
        "test_v52_cli_contract_commands_are_inspection_only_public_commands",
        'assert public_v51.__version__ == "0.51.0"',
        'assert public_v52.PUBLIC_RELEASE_STABILITY == "PRE_RELEASE"',
        "assert demo_stack.AASMEngine is public_v51.AASMEngine",
        "assert demo_stack.AASMEngine is not public_v52.AASMEngine",
    ])

    required_schemas = {
        "multi-objective-problem.schema.json",
        "lexicographic-result.schema.json",
        "pareto-frontier.schema.json",
        "pareto-frontier-certificate.schema.json",
        "resource-capacity.schema.json",
        "resource-observation.schema.json",
        "resource-demand.schema.json",
        "resource-routing-policy.schema.json",
        "sii-resource-aware-proposal.schema.json",
    }
    parsed = {name: schema(root, name) for name in sorted(required_schemas)}

    proposal_properties = parsed["sii-resource-aware-proposal.schema.json"]["properties"]
    if "expected_provider_quota_burn" not in proposal_properties:
        raise SystemExit("resource-aware SII schema lost expected_provider_quota_burn")

    policy_objectives = parsed["resource-routing-policy.schema.json"]["properties"]["objectives"]["items"]["properties"]["objective_id"]["enum"]
    expected_objectives = {
        "correctness",
        "evidence_quality",
        "expected_progress",
        "provider_quota_burn",
        "scarce_expert_usage",
        "monetary_cost",
        "wall_time_seconds",
    }
    if set(policy_objectives) != expected_objectives:
        raise SystemExit(f"resource-routing objective schema drift: {policy_objectives}")

    exact_match = parsed["pareto-frontier-certificate.schema.json"]["properties"]["exact_solution_set_match"]
    description = exact_match.get("description", "")
    if "solution IDs" not in description or "assignments" not in description or "objective vectors" not in description:
        raise SystemExit("Pareto certificate schema no longer defines exact_solution_set_match as full-point equality")

    problem_schema = parsed["multi-objective-problem.schema.json"]
    tolerance_description = problem_schema["properties"]["objectives"]["items"]["properties"]["tolerance"].get("description", "")
    if "Pareto dominance" not in tolerance_description or "strict improvement beyond tolerance" not in tolerance_description:
        raise SystemExit("multi-objective schema no longer freezes tolerance-aware Pareto dominance")

    require(root / "docs/RESOURCE_GOVERNED_DECISION_FOUNDATION.md", [
        "provider quota burn",
        "Two Pareto semantics",
        "exact equality of **solution IDs, assignments, and objective vectors**",
        "Resource-candidate Pareto frontier",
        "central Principal/Workspace/Scope authority/delegation layer",
    ])
    require(root / "ROADMAP.md", [
        "v0.52 under active implementation and freeze review",
        "Delivered v0.52 semantic core",
        "provider_quota_burn",
        "v0.52 freeze blockers",
    ])

    print("v0.52 contract check: PASS")


if __name__ == "__main__":
    main()
