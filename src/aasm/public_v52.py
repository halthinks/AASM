from copy import deepcopy

from . import public_v51 as _v51

for _name in dir(_v51):
    if not _name.startswith("_"):
        globals()[_name] = getattr(_v51, _name)

from .multi_objective import (
    FRONTIER_CONTRACT_ID,
    FRONTIER_CONTRACT_VERSION,
    FRONTIER_MODES,
    MULTI_OBJECTIVE_CONTRACT_ID,
    MULTI_OBJECTIVE_CONTRACT_VERSION,
    MULTI_OBJECTIVE_STABILITY,
    LexicographicResult,
    LexicographicStage,
    MultiObjectiveProblem,
    ObjectivePoint,
    OrderedObjective,
    ParetoFrontier,
    ParetoFrontierCertificate,
    dominates,
    frontier_contract,
    multi_objective_contract,
    solve_exact_finite_pareto_frontier,
    solve_lexicographic_finite,
    verify_exact_finite_pareto_frontier,
    verify_lexicographic_result,
)
from .resource_governance import (
    RESOURCE_CAPACITY_CONTRACT_ID,
    RESOURCE_DEMAND_CONTRACT_ID,
    RESOURCE_OBSERVATION_CONTRACT_ID,
    RESOURCE_GOVERNANCE_CONTRACT_VERSION,
    CapacityWindowKind,
    MeasurementAuthority,
    ResourceCapacity,
    ResourceDemandEstimate,
    ResourceObservation,
)
from .resource_routing import (
    RESOURCE_ROUTING_CONTRACT_ID,
    RESOURCE_ROUTING_CONTRACT_VERSION,
    RESOURCE_ROUTING_OBJECTIVE_IDS,
    RESOURCE_ROUTING_STABILITY,
    ResourceAwareCandidate,
    ResourceReservation,
    ResourceRoutingDecision,
    ResourceRoutingObjective,
    ResourceRoutingPolicy,
    default_resource_routing_objectives,
    planning_allocatable,
    resource_candidate_dominates,
    resource_candidate_objective_vector,
    resource_candidate_pareto_frontier,
    reserve_candidate_resources,
    select_resource_aware_candidate,
)
from .runtime_v52 import AASMEngine
from .sii_v52 import (
    SII_RESOURCE_AWARE_PROPOSAL_CONTRACT_ID,
    SII_RESOURCE_AWARE_PROPOSAL_CONTRACT_VERSION,
    SII_RESOURCE_AWARE_PROPOSAL_STABILITY,
    ResourceAwareStructuredProposal,
)

__version__ = "0.52.0"
PUBLIC_RELEASE_STABILITY = "PRE_RELEASE"
REMOTE_PROTOCOL_NAME = _v51.REMOTE_PROTOCOL_NAME
REMOTE_PROTOCOL_VERSION = _v51.REMOTE_PROTOCOL_VERSION

_NEW_ENGINE_METHODS = [
    "register_resource_capacity",
    "record_resource_observation",
    "resource_governance_report",
    "select_and_reserve_resource_candidate",
    "reestimate_resource_reservation",
    "release_resource_reservation",
    "settle_resource_reservation",
    "submit_resource_aware_sii_proposal",
    "resource_aware_sii_proposal_report",
    "route_resource_aware_sii_proposals",
    "record_resource_candidate_pareto_frontier",
    "resource_candidate_pareto_report",
    "pareto_resource_aware_sii_proposals",
    "resource_routing_explanation_report",
    "resource_consumption_calibration_report",
    "solve_lexicographic_multi_objective",
    "solve_exact_pareto_multi_objective",
    "multi_objective_report",
]

_NEW_IMPORTS = [
    "MULTI_OBJECTIVE_CONTRACT_ID", "MULTI_OBJECTIVE_CONTRACT_VERSION",
    "FRONTIER_CONTRACT_ID", "FRONTIER_CONTRACT_VERSION", "MULTI_OBJECTIVE_STABILITY", "FRONTIER_MODES",
    "OrderedObjective", "MultiObjectiveProblem", "ObjectivePoint", "LexicographicStage", "LexicographicResult",
    "ParetoFrontierCertificate", "ParetoFrontier", "multi_objective_contract", "frontier_contract",
    "solve_lexicographic_finite", "verify_lexicographic_result", "dominates",
    "solve_exact_finite_pareto_frontier", "verify_exact_finite_pareto_frontier",
    "RESOURCE_CAPACITY_CONTRACT_ID", "RESOURCE_OBSERVATION_CONTRACT_ID", "RESOURCE_DEMAND_CONTRACT_ID",
    "RESOURCE_GOVERNANCE_CONTRACT_VERSION", "CapacityWindowKind", "MeasurementAuthority",
    "ResourceObservation", "ResourceCapacity", "ResourceDemandEstimate",
    "RESOURCE_ROUTING_CONTRACT_ID", "RESOURCE_ROUTING_CONTRACT_VERSION", "RESOURCE_ROUTING_STABILITY",
    "RESOURCE_ROUTING_OBJECTIVE_IDS", "ResourceAwareCandidate", "ResourceReservation", "ResourceRoutingDecision",
    "ResourceRoutingObjective", "ResourceRoutingPolicy", "default_resource_routing_objectives", "planning_allocatable",
    "resource_candidate_dominates", "resource_candidate_objective_vector", "resource_candidate_pareto_frontier",
    "reserve_candidate_resources", "select_resource_aware_candidate",
    "SII_RESOURCE_AWARE_PROPOSAL_CONTRACT_ID", "SII_RESOURCE_AWARE_PROPOSAL_CONTRACT_VERSION",
    "SII_RESOURCE_AWARE_PROPOSAL_STABILITY", "ResourceAwareStructuredProposal",
]

SUPPORTED_ENGINE_METHODS = list(dict.fromkeys([*getattr(_v51, "SUPPORTED_ENGINE_METHODS", []), *_NEW_ENGINE_METHODS]))
SUPPORTED_CLI_COMMANDS = list(dict.fromkeys([
    *getattr(_v51, "SUPPORTED_CLI_COMMANDS", []),
    "multi-objective-contract", "pareto-frontier-contract", "resource-routing-contract",
]))
SUPPORTED_INSPECTION_SURFACES = list(dict.fromkeys([
    *getattr(_v51, "SUPPORTED_INSPECTION_SURFACES", []),
    "multi-objective-results", "pareto-frontiers", "resource-capacity", "resource-routing",
    "resource-candidate-frontiers", "resource-calibration",
]))
SUPPORTED_PUBLIC_IMPORTS = list(dict.fromkeys([*getattr(_v51, "SUPPORTED_PUBLIC_IMPORTS", []), *_NEW_IMPORTS]))

PUBLIC_API_CONTRACT = deepcopy(_v51.PUBLIC_API_CONTRACT)
PUBLIC_API_CONTRACT.update({
    "contract_version": "0.28.0",
    "runtime_version": __version__,
    "release_stability": PUBLIC_RELEASE_STABILITY,
    "supported_imports": SUPPORTED_PUBLIC_IMPORTS,
    "supported_engine_methods": SUPPORTED_ENGINE_METHODS,
    "supported_cli_commands": SUPPORTED_CLI_COMMANDS,
    "supported_inspection_surfaces": SUPPORTED_INSPECTION_SURFACES,
})
PUBLIC_API_CONTRACT["multi_objective"] = multi_objective_contract()
PUBLIC_API_CONTRACT["pareto_frontier"] = frontier_contract()
PUBLIC_API_CONTRACT["resource_governance"] = {
    "capacity_contract_id": RESOURCE_CAPACITY_CONTRACT_ID,
    "observation_contract_id": RESOURCE_OBSERVATION_CONTRACT_ID,
    "demand_contract_id": RESOURCE_DEMAND_CONTRACT_ID,
    "contract_version": RESOURCE_GOVERNANCE_CONTRACT_VERSION,
    "routing_contract_id": RESOURCE_ROUTING_CONTRACT_ID,
    "routing_contract_version": RESOURCE_ROUTING_CONTRACT_VERSION,
    "resource_state_authority": "NEVER_GRANTS_AUTHORITY",
    "observation_truth": "EVIDENCE_ONLY",
    "candidate_frontier_scope": "EXACT_OVER_SUPPLIED_ELIGIBLE_CANDIDATE_SET_ONLY",
}
PUBLIC_API_CONTRACT["resource_aware_sii"] = {
    "contract_id": SII_RESOURCE_AWARE_PROPOSAL_CONTRACT_ID,
    "contract_version": SII_RESOURCE_AWARE_PROPOSAL_CONTRACT_VERSION,
    "stability": SII_RESOURCE_AWARE_PROPOSAL_STABILITY,
    "parent": "aasm.sii.v1/0.3.0",
    "authority_reward": "NEVER",
}
PUBLIC_API_CONTRACT["distribution"]["version"] = __version__
PUBLIC_API_CONTRACT["distribution"]["stability"] = PUBLIC_RELEASE_STABILITY


def public_api_contract():
    return deepcopy(PUBLIC_API_CONTRACT)


def validate_public_api_contract():
    parent = _v51.validate_public_api_contract()
    errors = []
    if not parent["valid"]:
        errors.extend(f"v0.51: {error}" for error in parent["errors"])
    missing_imports = [name for name in _NEW_IMPORTS if name not in globals()]
    missing_methods = [name for name in _NEW_ENGINE_METHODS if not callable(getattr(AASMEngine, name, None))]
    if missing_imports:
        errors.append(f"missing v0.52 imports: {missing_imports}")
    if missing_methods:
        errors.append(f"missing v0.52 engine methods: {missing_methods}")
    if PUBLIC_API_CONTRACT.get("runtime_version") != __version__:
        errors.append("runtime version mismatch")
    if PUBLIC_API_CONTRACT.get("contract_version") != "0.28.0":
        errors.append("adoption contract mismatch")
    multi = PUBLIC_API_CONTRACT.get("multi_objective") or {}
    frontier = PUBLIC_API_CONTRACT.get("pareto_frontier") or {}
    resources = PUBLIC_API_CONTRACT.get("resource_governance") or {}
    sii = PUBLIC_API_CONTRACT.get("resource_aware_sii") or {}
    if multi.get("contract_id") != MULTI_OBJECTIVE_CONTRACT_ID or multi.get("contract_version") != MULTI_OBJECTIVE_CONTRACT_VERSION:
        errors.append("multi-objective contract identity mismatch")
    if frontier.get("contract_id") != FRONTIER_CONTRACT_ID or frontier.get("contract_version") != FRONTIER_CONTRACT_VERSION:
        errors.append("Pareto frontier contract identity mismatch")
    if multi.get("result_authority") != "EVIDENCE_ONLY" or multi.get("truth_authority") != "EXISTING_AASM_POLICY_ONLY":
        errors.append("multi-objective authority boundary mismatch")
    if frontier.get("result_authority") != "EVIDENCE_ONLY" or frontier.get("truth_authority") != "EXISTING_AASM_POLICY_ONLY":
        errors.append("frontier authority boundary mismatch")
    if resources.get("resource_state_authority") != "NEVER_GRANTS_AUTHORITY" or resources.get("observation_truth") != "EVIDENCE_ONLY":
        errors.append("resource authority/truth boundary mismatch")
    if resources.get("candidate_frontier_scope") != "EXACT_OVER_SUPPLIED_ELIGIBLE_CANDIDATE_SET_ONLY":
        errors.append("resource candidate frontier scope mismatch")
    if sii.get("contract_id") != SII_RESOURCE_AWARE_PROPOSAL_CONTRACT_ID or sii.get("authority_reward") != "NEVER":
        errors.append("resource-aware SII boundary mismatch")
    if PUBLIC_API_CONTRACT.get("distribution", {}).get("version") != __version__:
        errors.append("distribution version mismatch")
    if PUBLIC_RELEASE_STABILITY != "PRE_RELEASE":
        errors.append("v0.52 must remain PRE_RELEASE before promotion")
    return {"valid": not errors, "errors": errors, "contract": public_api_contract()}


from . import demo_stack as _demo_stack
_demo_stack.AASMEngine = AASMEngine
_demo_stack._runtime_version = lambda: __version__
