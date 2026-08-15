from aasm import public_v51
from aasm import public_v52
from aasm import public_v53
from aasm import public_v54
from aasm import public_v55
from aasm import public_v56
from aasm import demo_stack
from aasm.cli_v52 import build_parser
from aasm.multi_objective import FRONTIER_CONTRACT_ID, MULTI_OBJECTIVE_CONTRACT_ID
from aasm.resource_routing import RESOURCE_ROUTING_CONTRACT_ID, RESOURCE_ROUTING_OBJECTIVE_IDS
from aasm.sii_v52 import SII_RESOURCE_AWARE_PROPOSAL_CONTRACT_ID


def test_v52_versioned_public_contract_is_additive_and_valid():
    report = public_v52.validate_public_api_contract()
    assert report["valid"] is True, report["errors"]
    contract = report["contract"]

    assert public_v52.__version__ == "0.52.0"
    assert public_v52.PUBLIC_RELEASE_STABILITY == "ACTIVE_DEVELOPMENT"
    assert contract["contract_version"] == "0.28.0"
    assert contract["runtime_version"] == "0.52.0"
    assert contract["distribution"]["version"] == "0.52.0"
    assert contract["distribution"]["stability"] == "ACTIVE_DEVELOPMENT"

    assert contract["multi_objective"]["contract_id"] == MULTI_OBJECTIVE_CONTRACT_ID
    assert contract["pareto_frontier"]["contract_id"] == FRONTIER_CONTRACT_ID
    assert contract["resource_governance"]["routing_contract_id"] == RESOURCE_ROUTING_CONTRACT_ID
    assert contract["resource_governance"]["resource_state_authority"] == "NEVER_GRANTS_AUTHORITY"
    assert contract["resource_governance"]["observation_truth"] == "EVIDENCE_ONLY"
    assert contract["resource_governance"]["candidate_frontier_scope"] == "EXACT_OVER_SUPPLIED_ELIGIBLE_CANDIDATE_SET_ONLY"
    assert contract["resource_aware_sii"]["contract_id"] == SII_RESOURCE_AWARE_PROPOSAL_CONTRACT_ID
    assert contract["resource_aware_sii"]["authority_reward"] == "NEVER"


def test_v52_public_surface_preserves_v51_parent_contract():
    parent = public_v51.validate_public_api_contract()
    child = public_v52.validate_public_api_contract()
    assert parent["valid"] is True
    assert child["valid"] is True
    assert public_v51.__version__ == "0.51.0"
    assert public_v51.PUBLIC_RELEASE_STABILITY == "ACTIVE_DEVELOPMENT"
    assert public_v51.PUBLIC_API_CONTRACT["contract_version"] == "0.27.0"

    for name in public_v51.SUPPORTED_PUBLIC_IMPORTS:
        assert name in public_v52.SUPPORTED_PUBLIC_IMPORTS
    for name in public_v51.SUPPORTED_ENGINE_METHODS:
        assert name in public_v52.SUPPORTED_ENGINE_METHODS


def test_v52_parent_no_longer_owns_active_demo_stack_after_v56_promotion():
    assert demo_stack.AASMEngine is public_v56.AASMEngine
    assert demo_stack._runtime_version() == public_v56.__version__
    assert demo_stack.AASMEngine is not public_v52.AASMEngine
    assert demo_stack.AASMEngine is not public_v53.AASMEngine
    assert demo_stack.AASMEngine is not public_v54.AASMEngine
    assert demo_stack.AASMEngine is not public_v55.AASMEngine


def test_v52_public_surface_exposes_product_backward_resource_objective_vector():
    expected = {
        "correctness",
        "evidence_quality",
        "expected_progress",
        "provider_quota_burn",
        "scarce_expert_usage",
        "monetary_cost",
        "wall_time_seconds",
    }
    assert set(RESOURCE_ROUTING_OBJECTIVE_IDS) == expected
    for name in (
        "ResourceRoutingObjective",
        "ResourceRoutingPolicy",
        "ResourceAwareStructuredProposal",
        "MultiObjectiveProblem",
        "ParetoFrontierCertificate",
    ):
        assert name in public_v52.SUPPORTED_PUBLIC_IMPORTS
        assert hasattr(public_v52, name)

    for method in (
        "solve_lexicographic_multi_objective",
        "solve_exact_pareto_multi_objective",
        "record_resource_candidate_pareto_frontier",
        "select_and_reserve_resource_candidate",
        "reestimate_resource_reservation",
        "settle_resource_reservation",
    ):
        assert method in public_v52.SUPPORTED_ENGINE_METHODS
        assert callable(getattr(public_v52.AASMEngine, method, None))


def test_v52_cli_contract_commands_remain_versioned_commands():
    parser = build_parser()
    for command in (
        "multi-objective-contract",
        "pareto-frontier-contract",
        "resource-routing-contract",
    ):
        args = parser.parse_args([command])
        assert callable(args.func)
        assert command in public_v52.SUPPORTED_CLI_COMMANDS
