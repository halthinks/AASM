from __future__ import annotations

from copy import deepcopy

from . import public_v55 as _v55

for _name in dir(_v55):
    if not _name.startswith("_"):
        globals()[_name] = getattr(_v55, _name)

from ._runtime_v56_provenance import (
    SOLVER_PROVENANCE_RUNTIME_CONTRACT_ID,
    SOLVER_PROVENANCE_RUNTIME_CONTRACT_VERSION,
    SOLVER_PROVENANCE_RUNTIME_STABILITY,
    solver_provenance_runtime_contract,
)
from ._runtime_v56_solver_outcome import (
    SOLVER_OUTCOME_V2_RUNTIME_CONTRACT_ID,
    SOLVER_OUTCOME_V2_RUNTIME_CONTRACT_VERSION,
    SOLVER_OUTCOME_V2_RUNTIME_STABILITY,
    solver_outcome_v2_runtime_contract,
)
from .external_machine import (
    EXTERNAL_MACHINE_STABILITY,
    MACHINE_BINDING_CONTRACT_ID,
    MACHINE_BINDING_CONTRACT_VERSION,
    MACHINE_STATE_OBSERVATION_CONTRACT_ID,
    MACHINE_STATE_OBSERVATION_CONTRACT_VERSION,
    MachineBinding,
    MachineStateObservation,
    external_machine_contract,
)
from .external_machine_postcondition import (
    MACHINE_POSTCONDITION_VERIFICATION_CONTRACT_ID,
    MACHINE_POSTCONDITION_VERIFICATION_CONTRACT_VERSION,
    MACHINE_POSTCONDITION_VERIFICATION_STABILITY,
    POSTCONDITION_VERDICTS,
    MachinePostconditionVerification,
    machine_postcondition_verification_contract,
)
from .external_machine_postcondition_runtime import (
    MACHINE_POSTCONDITION_CAPABILITIES,
    MACHINE_POSTCONDITION_RUNTIME_CONTRACT_ID,
    MACHINE_POSTCONDITION_RUNTIME_CONTRACT_VERSION,
    MACHINE_POSTCONDITION_RUNTIME_STABILITY,
    machine_postcondition_runtime_contract,
    project_machine_postcondition_evidence,
)
from .external_machine_runtime import (
    EXTERNAL_MACHINE_CAPABILITIES,
    EXTERNAL_MACHINE_RUNTIME_CONTRACT_ID,
    EXTERNAL_MACHINE_RUNTIME_CONTRACT_VERSION,
    EXTERNAL_MACHINE_RUNTIME_STABILITY,
    external_machine_runtime_contract,
    project_external_machine_evidence,
)
from .external_machine_transition import (
    MACHINE_TRANSITION_CONTRACT_ID,
    MACHINE_TRANSITION_CONTRACT_VERSION,
    MACHINE_TRANSITION_STABILITY,
    MachineTransitionIntent,
    machine_transition_contract,
)
from .external_machine_transition_runtime import (
    MACHINE_TRANSITION_CAPABILITIES,
    MACHINE_TRANSITION_RUNTIME_CONTRACT_ID,
    MACHINE_TRANSITION_RUNTIME_CONTRACT_VERSION,
    MACHINE_TRANSITION_RUNTIME_STABILITY,
    machine_transition_runtime_contract,
    project_machine_transition_evidence,
)
from .provider_status_v2 import (
    PROVIDER_STATUS_MAP_CONTRACT_ID, PROVIDER_STATUS_MAP_CONTRACT_VERSION,
    ProviderStatusMap, ProviderStatusMapping, ProviderStatusRule,
    default_provider_status_map, highs_status_map, map_provider_status, map_provider_termination,
    ortools_cp_sat_status_map, provider_status_map_contract, pysat_cadical_status_map,
)
from .runtime_v56 import AASMEngine
from .solver_execution_observation import (
    SOLVER_EXECUTION_OBSERVATION_CONTRACT_ID, SOLVER_EXECUTION_OBSERVATION_CONTRACT_VERSION,
    SolverExecutionObservation, execution_observation_for_convex, execution_observation_for_optimization,
    runtime_environment_fingerprint, runtime_platform_identity,
)
from .solver_outcome_v2 import (
    SOLVER_EVIDENCE_GRADE_CONTRACT_ID, SOLVER_LEGACY_PROJECTION_CONTRACT_ID,
    SOLVER_OUTCOME_V2_CONTRACT_ID, SOLVER_OUTCOME_V2_CONTRACT_VERSION,
    SOLVER_STATUS_V2_CONTRACT_ID, SOLVER_STATUS_V2_CONTRACT_VERSION,
    SOLVER_TERMINATION_V2_CONTRACT_ID, INCUMBENT_VALIDATION_STATUSES, NORMALIZED_STATUSES,
    LegacyStatusProjection, ProviderTermination, SolverEvidenceGrade, SolverOutcomeV2,
    legacy_termination, normalize_optimization_result_v2, project_v2_to_legacy_status,
    solver_outcome_v2_contract,
)
from .solver_provenance import (
    SOLVER_EXECUTION_PROFILE_CONTRACT_ID, SOLVER_EXECUTION_PROFILE_CONTRACT_VERSION,
    SOLVER_PROFILE_EVALUATION_CONTRACT_ID, SOLVER_PROFILE_EVALUATION_CONTRACT_VERSION,
    SOLVER_RUNTIME_PROVENANCE_CONTRACT_ID, SOLVER_RUNTIME_PROVENANCE_CONTRACT_VERSION,
    DETERMINISM_POLICIES, SolverExecutionProfile, SolverProfileEvaluation, SolverRuntimeProvenance,
    build_solver_runtime_provenance, evaluate_solver_execution_profile, solver_provenance_contract,
)
from .state_authority import (
    FACT_AUTHORITY_CONTRACT_ID,
    FACT_AUTHORITY_CONTRACT_VERSION,
    STATE_AUTHORITY_STABILITY,
    STATE_CLAIM_CONTRACT_ID,
    STATE_CLAIM_CONTRACT_VERSION,
    STATE_CLAIM_KINDS,
    FactAuthority,
    StateClaim,
    fact_authority_matches_claim,
    state_authority_contract,
)
from .state_authority_runtime import (
    STATE_AUTHORITY_CAPABILITIES,
    STATE_AUTHORITY_RUNTIME_CONTRACT_ID,
    STATE_AUTHORITY_RUNTIME_CONTRACT_VERSION,
    STATE_AUTHORITY_RUNTIME_STABILITY,
    project_state_authority_evidence,
    state_authority_runtime_contract,
)


__version__ = "0.56.1"
PUBLIC_RELEASE_STABILITY = "ACTIVE_DEVELOPMENT"
REMOTE_PROTOCOL_NAME = _v55.REMOTE_PROTOCOL_NAME
REMOTE_PROTOCOL_VERSION = _v55.REMOTE_PROTOCOL_VERSION

_NEW_ENGINE_METHODS = [
    "solver_outcome_v2_runtime_contract_report", "record_solver_outcome_v2", "solver_outcome_v2_report",
    "solver_provenance_runtime_contract_report", "register_solver_execution_profile",
    "record_solver_runtime_provenance", "record_convex_solver_runtime_provenance",
    "evaluate_solver_runtime_profile", "solver_provenance_report",
    "state_authority_contract_report", "register_fact_authority", "revoke_fact_authority",
    "record_state_claim", "state_claim_report", "state_authority_report",
    "external_machine_contract_report", "register_machine_binding", "record_machine_state_observation",
    "machine_binding_report", "machine_state_observation_report", "external_machine_report",
    "machine_transition_contract_report", "propose_machine_transition", "machine_transition_report",
    "machine_transitions_report", "machine_postcondition_contract_report",
    "verify_machine_transition_postconditions", "machine_postcondition_verification_report",
    "machine_postconditions_report",
]

_NEW_IMPORTS = [
    "SOLVER_OUTCOME_V2_CONTRACT_ID", "SOLVER_OUTCOME_V2_CONTRACT_VERSION",
    "SOLVER_STATUS_V2_CONTRACT_ID", "SOLVER_STATUS_V2_CONTRACT_VERSION",
    "SOLVER_TERMINATION_V2_CONTRACT_ID", "SOLVER_EVIDENCE_GRADE_CONTRACT_ID",
    "SOLVER_LEGACY_PROJECTION_CONTRACT_ID", "NORMALIZED_STATUSES", "INCUMBENT_VALIDATION_STATUSES",
    "ProviderTermination", "SolverEvidenceGrade", "LegacyStatusProjection", "SolverOutcomeV2",
    "legacy_termination", "project_v2_to_legacy_status", "normalize_optimization_result_v2", "solver_outcome_v2_contract",
    "PROVIDER_STATUS_MAP_CONTRACT_ID", "PROVIDER_STATUS_MAP_CONTRACT_VERSION", "ProviderStatusRule", "ProviderStatusMap",
    "ProviderStatusMapping", "map_provider_status", "map_provider_termination", "ortools_cp_sat_status_map",
    "highs_status_map", "pysat_cadical_status_map", "default_provider_status_map", "provider_status_map_contract",
    "SOLVER_OUTCOME_V2_RUNTIME_CONTRACT_ID", "SOLVER_OUTCOME_V2_RUNTIME_CONTRACT_VERSION",
    "SOLVER_OUTCOME_V2_RUNTIME_STABILITY", "solver_outcome_v2_runtime_contract",
    "SOLVER_EXECUTION_PROFILE_CONTRACT_ID", "SOLVER_EXECUTION_PROFILE_CONTRACT_VERSION",
    "SOLVER_RUNTIME_PROVENANCE_CONTRACT_ID", "SOLVER_RUNTIME_PROVENANCE_CONTRACT_VERSION",
    "SOLVER_PROFILE_EVALUATION_CONTRACT_ID", "SOLVER_PROFILE_EVALUATION_CONTRACT_VERSION",
    "DETERMINISM_POLICIES", "SolverExecutionProfile", "SolverRuntimeProvenance", "SolverProfileEvaluation",
    "build_solver_runtime_provenance", "evaluate_solver_execution_profile", "solver_provenance_contract",
    "SOLVER_EXECUTION_OBSERVATION_CONTRACT_ID", "SOLVER_EXECUTION_OBSERVATION_CONTRACT_VERSION",
    "SolverExecutionObservation", "execution_observation_for_optimization", "execution_observation_for_convex",
    "runtime_platform_identity", "runtime_environment_fingerprint",
    "SOLVER_PROVENANCE_RUNTIME_CONTRACT_ID", "SOLVER_PROVENANCE_RUNTIME_CONTRACT_VERSION",
    "SOLVER_PROVENANCE_RUNTIME_STABILITY", "solver_provenance_runtime_contract",
    "FACT_AUTHORITY_CONTRACT_ID", "FACT_AUTHORITY_CONTRACT_VERSION", "STATE_CLAIM_CONTRACT_ID",
    "STATE_CLAIM_CONTRACT_VERSION", "STATE_AUTHORITY_STABILITY", "STATE_CLAIM_KINDS",
    "FactAuthority", "StateClaim", "fact_authority_matches_claim", "state_authority_contract",
    "STATE_AUTHORITY_RUNTIME_CONTRACT_ID", "STATE_AUTHORITY_RUNTIME_CONTRACT_VERSION",
    "STATE_AUTHORITY_RUNTIME_STABILITY", "STATE_AUTHORITY_CAPABILITIES",
    "project_state_authority_evidence", "state_authority_runtime_contract",
    "MACHINE_BINDING_CONTRACT_ID", "MACHINE_BINDING_CONTRACT_VERSION",
    "MACHINE_STATE_OBSERVATION_CONTRACT_ID", "MACHINE_STATE_OBSERVATION_CONTRACT_VERSION",
    "EXTERNAL_MACHINE_STABILITY", "MachineBinding", "MachineStateObservation", "external_machine_contract",
    "EXTERNAL_MACHINE_RUNTIME_CONTRACT_ID", "EXTERNAL_MACHINE_RUNTIME_CONTRACT_VERSION",
    "EXTERNAL_MACHINE_RUNTIME_STABILITY", "EXTERNAL_MACHINE_CAPABILITIES",
    "project_external_machine_evidence", "external_machine_runtime_contract",
    "MACHINE_TRANSITION_CONTRACT_ID", "MACHINE_TRANSITION_CONTRACT_VERSION", "MACHINE_TRANSITION_STABILITY",
    "MachineTransitionIntent", "machine_transition_contract", "MACHINE_TRANSITION_RUNTIME_CONTRACT_ID",
    "MACHINE_TRANSITION_RUNTIME_CONTRACT_VERSION", "MACHINE_TRANSITION_RUNTIME_STABILITY",
    "MACHINE_TRANSITION_CAPABILITIES", "project_machine_transition_evidence", "machine_transition_runtime_contract",
    "MACHINE_POSTCONDITION_VERIFICATION_CONTRACT_ID", "MACHINE_POSTCONDITION_VERIFICATION_CONTRACT_VERSION",
    "MACHINE_POSTCONDITION_VERIFICATION_STABILITY", "POSTCONDITION_VERDICTS", "MachinePostconditionVerification",
    "machine_postcondition_verification_contract", "MACHINE_POSTCONDITION_RUNTIME_CONTRACT_ID",
    "MACHINE_POSTCONDITION_RUNTIME_CONTRACT_VERSION", "MACHINE_POSTCONDITION_RUNTIME_STABILITY",
    "MACHINE_POSTCONDITION_CAPABILITIES", "project_machine_postcondition_evidence", "machine_postcondition_runtime_contract",
]

SUPPORTED_ENGINE_METHODS = list(dict.fromkeys([*getattr(_v55, "SUPPORTED_ENGINE_METHODS", []), *_NEW_ENGINE_METHODS]))
SUPPORTED_CLI_COMMANDS = list(getattr(_v55, "SUPPORTED_CLI_COMMANDS", []))
SUPPORTED_INSPECTION_SURFACES = list(dict.fromkeys([
    *getattr(_v55, "SUPPORTED_INSPECTION_SURFACES", []),
    "solver-outcome-v2", "solver-provenance", "state-authority", "external-machine", "machine-transition", "machine-postcondition",
]))
SUPPORTED_PUBLIC_IMPORTS = list(dict.fromkeys([*getattr(_v55, "SUPPORTED_PUBLIC_IMPORTS", []), *_NEW_IMPORTS]))

PUBLIC_API_CONTRACT = deepcopy(_v55.PUBLIC_API_CONTRACT)
PUBLIC_API_CONTRACT.update({
    "contract_version": "0.32.5", "runtime_version": __version__, "release_stability": PUBLIC_RELEASE_STABILITY,
    "supported_imports": SUPPORTED_PUBLIC_IMPORTS, "supported_engine_methods": SUPPORTED_ENGINE_METHODS,
    "supported_cli_commands": SUPPORTED_CLI_COMMANDS, "supported_inspection_surfaces": SUPPORTED_INSPECTION_SURFACES,
})
PUBLIC_API_CONTRACT["solver_outcome_v2"] = {
    **solver_outcome_v2_contract(), "provider_status_map": provider_status_map_contract(), "runtime": solver_outcome_v2_runtime_contract(),
}
PUBLIC_API_CONTRACT["solver_provenance"] = {
    **solver_provenance_contract(), "runtime": solver_provenance_runtime_contract(),
    "execution_observation_contract_id": SOLVER_EXECUTION_OBSERVATION_CONTRACT_ID,
    "provider_fixtures": ["cadical/pysat", "ortools-cp-sat", "highs", "cvxpy"],
    "interrupted_provenance_v2": "DORMANT_NON_AUTHORITATIVE_NOT_EXPOSED",
}
PUBLIC_API_CONTRACT["state_authority"] = {
    **state_authority_contract(),
    "runtime": state_authority_runtime_contract(),
}
PUBLIC_API_CONTRACT["external_machine"] = {
    **external_machine_contract(),
    "runtime": external_machine_runtime_contract(),
}
PUBLIC_API_CONTRACT["machine_transition"] = {
    **machine_transition_contract(),
    "runtime": machine_transition_runtime_contract(),
}
PUBLIC_API_CONTRACT["machine_postcondition"] = {
    **machine_postcondition_verification_contract(),
    "runtime": machine_postcondition_runtime_contract(),
}
PUBLIC_API_CONTRACT["distribution"]["version"] = __version__
PUBLIC_API_CONTRACT["distribution"]["stability"] = PUBLIC_RELEASE_STABILITY


def public_api_contract():
    return deepcopy(PUBLIC_API_CONTRACT)


def validate_public_api_contract():
    parent = _v55.validate_public_api_contract()
    errors = []
    if not parent["valid"]:
        errors.extend(f"v0.55: {error}" for error in parent["errors"])
    missing_imports = [name for name in _NEW_IMPORTS if name not in globals()]
    missing_methods = [name for name in _NEW_ENGINE_METHODS if not callable(getattr(AASMEngine, name, None))]
    if missing_imports:
        errors.append(f"missing v0.56 imports: {missing_imports}")
    if missing_methods:
        errors.append(f"missing v0.56 engine methods: {missing_methods}")
    if PUBLIC_API_CONTRACT.get("runtime_version") != __version__:
        errors.append("v0.56 runtime version mismatch")
    if PUBLIC_API_CONTRACT.get("contract_version") != "0.32.5":
        errors.append("active adoption contract mismatch")
    if PUBLIC_RELEASE_STABILITY != "ACTIVE_DEVELOPMENT":
        errors.append("v0.56 active release stability mismatch")

    outcome = PUBLIC_API_CONTRACT.get("solver_outcome_v2", {})
    if outcome.get("authoritative_detailed_status") != "normalized_status":
        errors.append("solver outcome v2 authoritative status boundary mismatch")
    if outcome.get("legacy_projection") != "V2_TO_V1_ONE_WAY_EXPLICITLY_LOSSY_WHERE_REQUIRED":
        errors.append("solver outcome v2 legacy compatibility projection mismatch")
    if outcome.get("provider_status_map", {}).get("substring_inference") != "FORBIDDEN":
        errors.append("provider status mapping substring-inference boundary mismatch")

    provenance = PUBLIC_API_CONTRACT.get("solver_provenance", {})
    if provenance.get("runtime_provenance_contract_id") != SOLVER_RUNTIME_PROVENANCE_CONTRACT_ID:
        errors.append("solver provenance contract mismatch")
    if provenance.get("effective_options") != "ADAPTER_OBSERVED_ACTUAL_CONFIGURATION_REQUIRED":
        errors.append("solver provenance effective-option boundary mismatch")
    if provenance.get("runtime", {}).get("parallel_provenance_table") != "NONE":
        errors.append("solver provenance parallel-table boundary mismatch")
    if provenance.get("runtime", {}).get("provenance_grants_reproducibility") is not False:
        errors.append("solver provenance reproducibility claim boundary mismatch")
    if provenance.get("truth_authority") != "NONE" or provenance.get("policy_authority") != "NONE":
        errors.append("solver provenance authority boundary mismatch")

    state_authority = PUBLIC_API_CONTRACT.get("state_authority", {})
    if state_authority.get("claim_kinds") != list(STATE_CLAIM_KINDS):
        errors.append("state authority claim-kind boundary mismatch")
    if state_authority.get("observed") != "EMPIRICAL_EVIDENCE_ONLY_NOT_AUTHORITATIVE_BY_EXISTENCE_OR_AGREEMENT":
        errors.append("observed state claim authority boundary mismatch")
    if state_authority.get("authoritative") != "EXPLICIT_MATCHING_FACT_AUTHORITY_AND_SOURCE_CLAIM_REQUIRED":
        errors.append("authoritative state claim boundary mismatch")
    if state_authority.get("fact_authority_grants_effect_authority") is not False:
        errors.append("fact authority effect-authority boundary mismatch")
    if state_authority.get("runtime", {}).get("parallel_truth_table") != "NONE":
        errors.append("state authority parallel-truth-table boundary mismatch")
    if state_authority.get("runtime", {}).get("machine_state_mutation") != "NONE":
        errors.append("state authority machine-state mutation boundary mismatch")
    if state_authority.get("runtime", {}).get("effect_authority") != "NONE":
        errors.append("state authority runtime effect-authority boundary mismatch")

    external = PUBLIC_API_CONTRACT.get("external_machine", {})
    if external.get("binding_role") != "REFERENCE_AND_CORRELATION_ONLY_NOT_EXTERNAL_STATE_COPY":
        errors.append("external machine binding role mismatch")
    if external.get("binding_grants_fact_authority") is not False:
        errors.append("external machine binding fact-authority boundary mismatch")
    if external.get("binding_grants_effect_authority") is not False:
        errors.append("external machine binding effect-authority boundary mismatch")
    if external.get("capability_reference_grants_authority") is not False:
        errors.append("external machine capability-reference authority boundary mismatch")
    if external.get("external_state_table") != "NONE":
        errors.append("external machine parallel-state boundary mismatch")
    if external.get("executor_invocation") != "NONE_BY_THIS_FOUNDATION":
        errors.append("external machine executor-invocation boundary mismatch")
    if external.get("postcondition_achievement_claim") != "NOT_YET_CLAIMED_PR2C":
        errors.append("external machine PR2A postcondition claim boundary mismatch")
    external_runtime = external.get("runtime", {})
    if external_runtime.get("effect_dispatch") != "NONE" or external_runtime.get("executor_invocation") != "NONE":
        errors.append("external machine PR2A dispatch boundary mismatch")
    if external_runtime.get("machine_state_mutation") != "NONE":
        errors.append("external machine machine-state mutation boundary mismatch")

    transition = PUBLIC_API_CONTRACT.get("machine_transition", {})
    if transition.get("effect_proposal") != "EXISTING_AASM_PROPOSE_EFFECT_AND_EFFECT_INTENT_ONLY":
        errors.append("machine transition proposal path mismatch")
    if transition.get("effect_authorization") != "EXISTING_AASM_AUTHORIZE_EFFECT_ONLY_NOT_PERFORMED_BY_THIS_CONTRACT":
        errors.append("machine transition authorization boundary mismatch")
    if transition.get("effect_dispatch") != "EXISTING_AASM_EXECUTE_EFFECT_ONLY_NOT_PERFORMED_BY_THIS_CONTRACT":
        errors.append("machine transition dispatch boundary mismatch")
    if transition.get("parallel_dispatcher") != "NONE" or transition.get("parallel_effect_store") != "NONE":
        errors.append("machine transition parallel effect infrastructure detected")
    if transition.get("command_success_is_achievement") is not False:
        errors.append("machine transition command-success truth boundary mismatch")
    if transition.get("postcondition_verification") != "NOT_IMPLEMENTED_PR2B_RESERVED_FOR_PR2C":
        errors.append("machine transition PR2B postcondition boundary mismatch")
    transition_runtime = transition.get("runtime", {})
    if transition_runtime.get("effect_proposal_path") != "EXISTING_AASM_PROPOSE_EFFECT_ONLY":
        errors.append("machine transition runtime proposal path mismatch")
    if transition_runtime.get("effect_dispatch") != "NOT_PERFORMED_USE_EXISTING_EXECUTE_EFFECT":
        errors.append("machine transition runtime dispatch boundary mismatch")
    if transition_runtime.get("effect_ownership") != "NOT_CREATED_BY_THIS_RUNTIME":
        errors.append("machine transition runtime ownership boundary mismatch")
    if transition_runtime.get("transition_status_store") != "NONE_DERIVE_FROM_EXISTING_EFFECT_RECORD":
        errors.append("machine transition parallel status boundary mismatch")
    if transition_runtime.get("machine_state_mutation") != "NONE":
        errors.append("machine transition proposal mutates machine state")

    postcondition = PUBLIC_API_CONTRACT.get("machine_postcondition", {})
    if postcondition.get("effect_status_requirement") != "EXISTING_AASM_EFFECT_MUST_BE_SUCCEEDED":
        errors.append("machine postcondition effect-status boundary mismatch")
    if postcondition.get("unknown_effect") != "BLOCKED_USE_EXISTING_EFFECT_RECONCILIATION":
        errors.append("machine postcondition UNKNOWN boundary mismatch")
    if postcondition.get("achieved_source") != "PR1_DURABLE_AUTHORITATIVE_STATE_CLAIMS_ONLY":
        errors.append("machine postcondition achieved-state boundary mismatch")
    if postcondition.get("observation_correlation") != "PR2A_MACHINE_STATE_OBSERVATION_CORRELATION_ID_MUST_EQUAL_EXISTING_EFFECT_EXECUTION_ID":
        errors.append("machine postcondition execution-correlation boundary mismatch")
    if postcondition.get("comparison") != "EXACT_CANONICAL_VALUE_EQUALITY_ONLY_NO_TOLERANCE_IN_THIS_FOUNDATION":
        errors.append("machine postcondition comparison boundary mismatch")
    if postcondition.get("effect_success_is_achievement") is not False:
        errors.append("effect success incorrectly grants achievement")
    if postcondition.get("verification_mints_fact_authority") is not False or postcondition.get("verification_mints_state_claim") is not False:
        errors.append("machine postcondition verification mints authority/state")
    if postcondition.get("verification_mutates_effect_outcome") is not False or postcondition.get("verification_mutates_machine_state") is not False:
        errors.append("machine postcondition verification mutates authoritative state")
    if postcondition.get("verification_grants_effect_authority") is not False:
        errors.append("machine postcondition verification grants effect authority")
    if postcondition.get("parallel_truth_table") != "NONE" or postcondition.get("parallel_effect_lifecycle") != "NONE":
        errors.append("machine postcondition parallel truth/effect lifecycle detected")
    post_runtime = postcondition.get("runtime", {})
    if post_runtime.get("effect_source") != "EXISTING_AASM_EFFECT_RECORD_ONLY":
        errors.append("machine postcondition runtime effect source mismatch")
    if post_runtime.get("state_claim_creation") != "NONE" or post_runtime.get("fact_authority_creation") != "NONE":
        errors.append("machine postcondition runtime creates authority/state")
    if post_runtime.get("effect_status_mutation") != "NONE" or post_runtime.get("machine_state_mutation") != "NONE":
        errors.append("machine postcondition runtime mutates effect/machine state")
    if post_runtime.get("effect_authority") != "NONE":
        errors.append("machine postcondition runtime gained effect authority")
    if post_runtime.get("parallel_truth_table") != "NONE" or post_runtime.get("parallel_effect_lifecycle") != "NONE":
        errors.append("machine postcondition runtime parallel truth/effect lifecycle detected")

    return {"valid": not errors, "errors": errors, "contract": public_api_contract()}


from . import demo_stack as _demo_stack
_demo_stack.AASMEngine = AASMEngine
_demo_stack._runtime_version = lambda: __version__
