from __future__ import annotations

from copy import deepcopy

from . import public_v56 as _base

for _name in dir(_base):
    if not _name.startswith("_"):
        globals()[_name] = getattr(_base, _name)

from .effect_capability import (
    EFFECT_CAPABILITY_CONTRACT_ID,
    EFFECT_CAPABILITY_CONTRACT_VERSION,
    EFFECT_CAPABILITY_STABILITY,
    EffectCapability,
    NumericInterval,
    effect_capability_contract,
    normalize_numeric_bounds,
    numeric_bounds_subset,
)
from .effect_capability_runtime import (
    EFFECT_CAPABILITY_CAPABILITIES,
    EFFECT_CAPABILITY_RUNTIME_CONTRACT_ID,
    EFFECT_CAPABILITY_RUNTIME_CONTRACT_VERSION,
    EFFECT_CAPABILITY_RUNTIME_STABILITY,
    effect_capability_runtime_contract,
    project_effect_capability_evidence,
)
from .effect_capability_use import (
    EFFECT_CAPABILITY_USE_CONTRACT_ID,
    EFFECT_CAPABILITY_USE_CONTRACT_VERSION,
    EFFECT_CAPABILITY_USE_STABILITY,
    EffectCapabilityUse,
    effect_capability_use_contract,
)
from .event_causality import (
    CAUSAL_RELATIONS,
    CLOCK_QUALITIES,
    CLOCK_QUALITY_RANK,
    EVENT_CAUSALITY_CONTRACT_ID,
    EVENT_CAUSALITY_CONTRACT_VERSION,
    EVENT_CAUSALITY_STABILITY,
    PORTABLE_U63_MAX,
    CausalEventIdentity,
    CausalRelation,
    event_causality_contract,
)
from .event_causality_runtime import (
    EVENT_CAUSALITY_CAPABILITIES,
    EVENT_CAUSALITY_RUNTIME_CONTRACT_ID,
    EVENT_CAUSALITY_RUNTIME_CONTRACT_VERSION,
    EVENT_CAUSALITY_RUNTIME_STABILITY,
    event_causality_runtime_contract,
    project_event_causality_evidence,
)
from .observation_freshness import (
    FRESHNESS_AGE_BASES,
    FRESHNESS_REASONS,
    FRESHNESS_STATUSES,
    OBSERVATION_FRESHNESS_CONTRACT_ID,
    OBSERVATION_FRESHNESS_CONTRACT_VERSION,
    OBSERVATION_FRESHNESS_STABILITY,
    ObservationFreshnessAssessment,
    assess_freshness,
    observation_freshness_contract,
)
from .observation_freshness_runtime import (
    OBSERVATION_FRESHNESS_CAPABILITIES,
    OBSERVATION_FRESHNESS_RUNTIME_CONTRACT_ID,
    OBSERVATION_FRESHNESS_RUNTIME_CONTRACT_VERSION,
    OBSERVATION_FRESHNESS_RUNTIME_STABILITY,
    observation_freshness_runtime_contract,
    project_observation_freshness_evidence,
)
from .physical_control_fencing_runtime import (
    PHYSICAL_CONTROL_FENCING_CAPABILITIES,
    PHYSICAL_CONTROL_FENCING_RUNTIME_CONTRACT_ID,
    PHYSICAL_CONTROL_FENCING_RUNTIME_CONTRACT_VERSION,
    PHYSICAL_CONTROL_FENCING_RUNTIME_STABILITY,
    physical_control_fencing_runtime_contract,
    project_physical_control_fencing_evidence,
)
from .physical_effect_binding import (
    PHYSICAL_EFFECT_AUTHORITY_BINDING_CONTRACT_ID,
    PHYSICAL_EFFECT_AUTHORITY_BINDING_CONTRACT_VERSION,
    PHYSICAL_EFFECT_AUTHORITY_BINDING_STABILITY,
    PhysicalEffectAuthorityBinding,
    physical_effect_authority_binding_contract,
)
from .physical_effect_integration_runtime import (
    PHYSICAL_EFFECT_INTEGRATION_CAPABILITIES,
    PHYSICAL_EFFECT_INTEGRATION_RUNTIME_CONTRACT_ID,
    PHYSICAL_EFFECT_INTEGRATION_RUNTIME_CONTRACT_VERSION,
    PHYSICAL_EFFECT_INTEGRATION_RUNTIME_STABILITY,
    physical_effect_integration_runtime_contract,
    project_physical_effect_integration_evidence,
)
from .physical_preemption import (
    AUTHORITY_PREEMPTION_CONTRACT_ID,
    AUTHORITY_PREEMPTION_CONTRACT_VERSION,
    AUTHORITY_PREEMPTION_STABILITY,
    AuthorityPreemption,
    authority_preemption_contract,
)
from .state_conflict import (
    STATE_CONFLICT_ACTUAL_KINDS,
    STATE_CONFLICT_CONTRACT_ID,
    STATE_CONFLICT_CONTRACT_VERSION,
    STATE_CONFLICT_EXPECTATION_KINDS,
    STATE_CONFLICT_REASONS,
    STATE_CONFLICT_STABILITY,
    StateConflict,
    state_conflict_contract,
    state_conflict_reasons,
)
from .state_conflict_runtime import (
    STATE_CONFLICT_CAPABILITIES,
    STATE_CONFLICT_RUNTIME_CONTRACT_ID,
    STATE_CONFLICT_RUNTIME_CONTRACT_VERSION,
    STATE_CONFLICT_RUNTIME_STABILITY,
    project_state_conflict_evidence,
    state_conflict_runtime_contract,
)
from .runtime_v56 import AASMEngine


__version__ = _base.__version__
PUBLIC_RELEASE_STABILITY = _base.PUBLIC_RELEASE_STABILITY
REMOTE_PROTOCOL_NAME = _base.REMOTE_PROTOCOL_NAME
REMOTE_PROTOCOL_VERSION = _base.REMOTE_PROTOCOL_VERSION

_NEW_ENGINE_METHODS = [
    "effect_capability_contract_report",
    "issue_effect_capability",
    "delegate_effect_capability",
    "revoke_effect_capability",
    "effect_capability_report",
    "effect_capabilities_report",
    "physical_control_fencing_contract_report",
    "validate_effect_capability_use",
    "preempt_authority_lease",
    "effect_capability_use_report",
    "authority_preemption_report",
    "physical_control_fencing_report",
    "physical_effect_integration_contract_report",
    "bind_physical_effect_authority",
    "physical_effect_binding_report",
    "physical_effect_integration_report",
    "state_conflict_contract_report",
    "build_state_conflict",
    "record_state_conflict",
    "state_conflict_report",
    "state_conflicts_report",
    "event_causality_contract_report",
    "record_causal_event",
    "record_machine_observation_causal_event",
    "record_causal_relation",
    "causal_event_report",
    "causal_relation_report",
    "event_causality_report",
    "observation_freshness_contract_report",
    "assess_machine_observation_freshness",
    "observation_freshness_assessment_report",
    "observation_freshness_report",
]

_NEW_IMPORTS = [
    "EFFECT_CAPABILITY_CONTRACT_ID",
    "EFFECT_CAPABILITY_CONTRACT_VERSION",
    "EFFECT_CAPABILITY_STABILITY",
    "NumericInterval",
    "EffectCapability",
    "normalize_numeric_bounds",
    "numeric_bounds_subset",
    "effect_capability_contract",
    "EFFECT_CAPABILITY_RUNTIME_CONTRACT_ID",
    "EFFECT_CAPABILITY_RUNTIME_CONTRACT_VERSION",
    "EFFECT_CAPABILITY_RUNTIME_STABILITY",
    "EFFECT_CAPABILITY_CAPABILITIES",
    "project_effect_capability_evidence",
    "effect_capability_runtime_contract",
    "EFFECT_CAPABILITY_USE_CONTRACT_ID",
    "EFFECT_CAPABILITY_USE_CONTRACT_VERSION",
    "EFFECT_CAPABILITY_USE_STABILITY",
    "EffectCapabilityUse",
    "effect_capability_use_contract",
    "AUTHORITY_PREEMPTION_CONTRACT_ID",
    "AUTHORITY_PREEMPTION_CONTRACT_VERSION",
    "AUTHORITY_PREEMPTION_STABILITY",
    "AuthorityPreemption",
    "authority_preemption_contract",
    "PHYSICAL_CONTROL_FENCING_RUNTIME_CONTRACT_ID",
    "PHYSICAL_CONTROL_FENCING_RUNTIME_CONTRACT_VERSION",
    "PHYSICAL_CONTROL_FENCING_RUNTIME_STABILITY",
    "PHYSICAL_CONTROL_FENCING_CAPABILITIES",
    "project_physical_control_fencing_evidence",
    "physical_control_fencing_runtime_contract",
    "PHYSICAL_EFFECT_AUTHORITY_BINDING_CONTRACT_ID",
    "PHYSICAL_EFFECT_AUTHORITY_BINDING_CONTRACT_VERSION",
    "PHYSICAL_EFFECT_AUTHORITY_BINDING_STABILITY",
    "PhysicalEffectAuthorityBinding",
    "physical_effect_authority_binding_contract",
    "PHYSICAL_EFFECT_INTEGRATION_RUNTIME_CONTRACT_ID",
    "PHYSICAL_EFFECT_INTEGRATION_RUNTIME_CONTRACT_VERSION",
    "PHYSICAL_EFFECT_INTEGRATION_RUNTIME_STABILITY",
    "PHYSICAL_EFFECT_INTEGRATION_CAPABILITIES",
    "project_physical_effect_integration_evidence",
    "physical_effect_integration_runtime_contract",
    "STATE_CONFLICT_CONTRACT_ID",
    "STATE_CONFLICT_CONTRACT_VERSION",
    "STATE_CONFLICT_STABILITY",
    "STATE_CONFLICT_EXPECTATION_KINDS",
    "STATE_CONFLICT_ACTUAL_KINDS",
    "STATE_CONFLICT_REASONS",
    "StateConflict",
    "state_conflict_reasons",
    "state_conflict_contract",
    "STATE_CONFLICT_RUNTIME_CONTRACT_ID",
    "STATE_CONFLICT_RUNTIME_CONTRACT_VERSION",
    "STATE_CONFLICT_RUNTIME_STABILITY",
    "STATE_CONFLICT_CAPABILITIES",
    "project_state_conflict_evidence",
    "state_conflict_runtime_contract",
    "EVENT_CAUSALITY_CONTRACT_ID",
    "EVENT_CAUSALITY_CONTRACT_VERSION",
    "EVENT_CAUSALITY_STABILITY",
    "PORTABLE_U63_MAX",
    "CLOCK_QUALITIES",
    "CLOCK_QUALITY_RANK",
    "CAUSAL_RELATIONS",
    "CausalEventIdentity",
    "CausalRelation",
    "event_causality_contract",
    "EVENT_CAUSALITY_RUNTIME_CONTRACT_ID",
    "EVENT_CAUSALITY_RUNTIME_CONTRACT_VERSION",
    "EVENT_CAUSALITY_RUNTIME_STABILITY",
    "EVENT_CAUSALITY_CAPABILITIES",
    "project_event_causality_evidence",
    "event_causality_runtime_contract",
    "OBSERVATION_FRESHNESS_CONTRACT_ID",
    "OBSERVATION_FRESHNESS_CONTRACT_VERSION",
    "OBSERVATION_FRESHNESS_STABILITY",
    "FRESHNESS_STATUSES",
    "FRESHNESS_AGE_BASES",
    "FRESHNESS_REASONS",
    "ObservationFreshnessAssessment",
    "assess_freshness",
    "observation_freshness_contract",
    "OBSERVATION_FRESHNESS_RUNTIME_CONTRACT_ID",
    "OBSERVATION_FRESHNESS_RUNTIME_CONTRACT_VERSION",
    "OBSERVATION_FRESHNESS_RUNTIME_STABILITY",
    "OBSERVATION_FRESHNESS_CAPABILITIES",
    "project_observation_freshness_evidence",
    "observation_freshness_runtime_contract",
]

SUPPORTED_ENGINE_METHODS = list(dict.fromkeys([*getattr(_base, "SUPPORTED_ENGINE_METHODS", []), *_NEW_ENGINE_METHODS]))
SUPPORTED_CLI_COMMANDS = list(getattr(_base, "SUPPORTED_CLI_COMMANDS", []))
SUPPORTED_INSPECTION_SURFACES = list(dict.fromkeys([
    *getattr(_base, "SUPPORTED_INSPECTION_SURFACES", []),
    "effect-capability",
    "physical-control-fencing",
    "physical-effect-integration",
    "state-conflict",
    "event-causality",
    "observation-freshness",
]))
SUPPORTED_PUBLIC_IMPORTS = list(dict.fromkeys([*getattr(_base, "SUPPORTED_PUBLIC_IMPORTS", []), *_NEW_IMPORTS]))

PUBLIC_API_CONTRACT = deepcopy(_base.PUBLIC_API_CONTRACT)
PUBLIC_API_CONTRACT.update({
    "contract_version": "0.32.10",
    "runtime_version": __version__,
    "release_stability": PUBLIC_RELEASE_STABILITY,
    "supported_imports": SUPPORTED_PUBLIC_IMPORTS,
    "supported_engine_methods": SUPPORTED_ENGINE_METHODS,
    "supported_cli_commands": SUPPORTED_CLI_COMMANDS,
    "supported_inspection_surfaces": SUPPORTED_INSPECTION_SURFACES,
})
PUBLIC_API_CONTRACT["effect_capability"] = {
    **effect_capability_contract(),
    "runtime": effect_capability_runtime_contract(),
    "dependent_effect_integration": "aasm.effect.physical-authority-integration.runtime.v1",
}
PUBLIC_API_CONTRACT["physical_control_fencing"] = {
    **physical_control_fencing_runtime_contract(),
    "effect_capability_use": effect_capability_use_contract(),
    "authority_preemption": authority_preemption_contract(),
    "preemption_recovery": "EXISTING_EVIDENCE_REPLAY_REPAIRS_MISSING_CANONICAL_LEASE_REVOCATION",
    "dependent_effect_integration": "aasm.effect.physical-authority-integration.runtime.v1",
}
PUBLIC_API_CONTRACT["physical_effect_integration"] = {
    **physical_effect_authority_binding_contract(),
    "runtime": physical_effect_integration_runtime_contract(),
}
PUBLIC_API_CONTRACT["state_conflict"] = {
    **state_conflict_contract(),
    "runtime": state_conflict_runtime_contract(),
}
PUBLIC_API_CONTRACT["event_causality"] = {
    **event_causality_contract(),
    "runtime": event_causality_runtime_contract(),
}
PUBLIC_API_CONTRACT["observation_freshness"] = {
    **observation_freshness_contract(),
    "runtime": observation_freshness_runtime_contract(),
}
PUBLIC_API_CONTRACT["distribution"]["version"] = __version__
PUBLIC_API_CONTRACT["distribution"]["stability"] = PUBLIC_RELEASE_STABILITY


def public_api_contract():
    return deepcopy(PUBLIC_API_CONTRACT)


def validate_public_api_contract():
    parent = _base.validate_public_api_contract()
    errors = []
    if not parent["valid"]:
        errors.extend(f"v0.56 base: {error}" for error in parent["errors"])

    missing_imports = [name for name in _NEW_IMPORTS if name not in globals()]
    missing_methods = [name for name in _NEW_ENGINE_METHODS if not callable(getattr(AASMEngine, name, None))]
    if missing_imports:
        errors.append(f"missing active governed-reality imports: {missing_imports}")
    if missing_methods:
        errors.append(f"missing active governed-reality engine methods: {missing_methods}")
    if PUBLIC_API_CONTRACT.get("runtime_version") != __version__:
        errors.append("active runtime version mismatch")
    if PUBLIC_API_CONTRACT.get("contract_version") != "0.32.10":
        errors.append("active adoption contract mismatch")

    capability = PUBLIC_API_CONTRACT.get("effect_capability", {})
    if capability.get("capability_existence_grants_effect_authority") is not False:
        errors.append("effect capability existence incorrectly grants effect authority")
    if capability.get("effect_authorization_integration") != "NOT_YET_PR3H":
        errors.append("PR-3C/3D child contract boundary drift")
    if capability.get("dependent_effect_integration") != PHYSICAL_EFFECT_INTEGRATION_RUNTIME_CONTRACT_ID:
        errors.append("effect capability missing PR-3H dependent integration reference")
    cap_runtime = capability.get("runtime", {})
    if cap_runtime.get("authority") != "EXISTING_AASM_SCOPED_AUTHORITY_ONLY":
        errors.append("effect capability introduced parallel authority evaluator")
    if cap_runtime.get("effect_authorization_integration") != "NONE_PR3C_PR3D_FOUNDATION":
        errors.append("PR-3C/3D runtime child boundary drift")
    if cap_runtime.get("effect_dispatch") != "NONE":
        errors.append("effect capability runtime introduced dispatch")
    if cap_runtime.get("parallel_effect_lifecycle") != "NONE":
        errors.append("effect capability runtime introduced parallel effect lifecycle")

    fencing = PUBLIC_API_CONTRACT.get("physical_control_fencing", {})
    if fencing.get("use_validation_grants_effect_authority") is not False:
        errors.append("capability-use validation incorrectly grants effect authority")
    if fencing.get("preemption_grants_effect_authority") is not False:
        errors.append("preemption incorrectly grants effect authority")
    if fencing.get("effect_authorization_integration") != "NONE_PR3E_PR3F_PR3G_FOUNDATION":
        errors.append("PR-3E/F/G child runtime boundary drift")
    if fencing.get("dependent_effect_integration") != PHYSICAL_EFFECT_INTEGRATION_RUNTIME_CONTRACT_ID:
        errors.append("physical control fencing missing PR-3H dependent integration reference")
    if fencing.get("effect_dispatch") != "NONE":
        errors.append("physical control fencing introduced dispatch")
    if fencing.get("parallel_authority_evaluator") != "NONE":
        errors.append("physical control fencing introduced parallel authority evaluator")
    if fencing.get("parallel_effect_lifecycle") != "NONE":
        errors.append("physical control fencing introduced parallel effect lifecycle")
    use = fencing.get("effect_capability_use", {})
    if use.get("validation_is_reusable_authorization_token") is not False:
        errors.append("capability-use validation became reusable authorization token")
    if use.get("required_recheck") != "PR3H_MUST_RECHECK_AT_EFFECT_AUTHORIZATION_AND_EXECUTION_BOUNDARIES":
        errors.append("PR-3H recheck boundary missing")
    preemption = fencing.get("authority_preemption", {})
    if preemption.get("identity_reference_grants_authority") is not False:
        errors.append("preemptor listing incorrectly grants authority")
    if preemption.get("preemption_grants_new_effect_authority") is not False:
        errors.append("preemption incorrectly grants new effect authority")

    integration = PUBLIC_API_CONTRACT.get("physical_effect_integration", {})
    if integration.get("contract_id") != PHYSICAL_EFFECT_AUTHORITY_BINDING_CONTRACT_ID:
        errors.append("physical effect binding contract missing")
    if integration.get("authorization_recheck") != "MANDATORY_AT_EXISTING_AUTHORIZE_EFFECT_BOUNDARY":
        errors.append("physical effect authorization recheck missing")
    if integration.get("execution_recheck") != "MANDATORY_AT_EXISTING_EXECUTE_EFFECT_BOUNDARY":
        errors.append("physical effect execution recheck missing")
    if integration.get("binding_existence_grants_effect_authority") is not False:
        errors.append("physical effect binding incorrectly grants effect authority")
    if integration.get("prior_use_validation_is_authorization") is not False:
        errors.append("prior capability-use validation became authorization")
    integration_runtime = integration.get("runtime", {})
    if integration_runtime.get("contract_id") != PHYSICAL_EFFECT_INTEGRATION_RUNTIME_CONTRACT_ID:
        errors.append("physical effect integration runtime contract missing")
    if integration_runtime.get("effect_authority") != "EXISTING_V53_EFFECT_AUTHORIZE_AND_EFFECT_EXECUTE_REMAIN_REQUIRED":
        errors.append("physical effect integration replaced scoped effect authority")
    if integration_runtime.get("task_lease") != "EXISTING_V54_TASKLEASE_UNCHANGED":
        errors.append("physical effect integration replaced TaskLease")
    if integration_runtime.get("ownership") != "EXISTING_V54_EFFECT_OWNERSHIP_UNCHANGED":
        errors.append("physical effect integration replaced EffectOwnership")
    if integration_runtime.get("unknown_and_reconciliation") != "EXISTING_V54_UNKNOWN_AND_RECONCILIATION_UNCHANGED":
        errors.append("physical effect integration replaced UNKNOWN/reconciliation")
    if integration_runtime.get("parallel_authority_evaluator") != "NONE":
        errors.append("physical effect integration introduced parallel authority evaluator")
    if integration_runtime.get("parallel_effect_store") != "NONE":
        errors.append("physical effect integration introduced parallel effect store")
    if integration_runtime.get("parallel_effect_lifecycle") != "NONE":
        errors.append("physical effect integration introduced parallel effect lifecycle")
    if integration_runtime.get("parallel_dispatcher") != "NONE":
        errors.append("physical effect integration introduced parallel dispatcher")

    conflict = PUBLIC_API_CONTRACT.get("state_conflict", {})
    if conflict.get("contract_id") != STATE_CONFLICT_CONTRACT_ID:
        errors.append("S3 state conflict semantic contract missing")
    if conflict.get("comparison") != "EXACT_CANONICAL_PORTABLE_JSON_VALUE_PLUS_EXACT_REVISION_IDENTITY":
        errors.append("S3 state conflict comparison drift")
    if conflict.get("conflict_grants_fact_authority") is not False:
        errors.append("state conflict incorrectly grants fact authority")
    if conflict.get("conflict_grants_effect_authority") is not False:
        errors.append("state conflict incorrectly grants effect authority")
    if conflict.get("conflict_mutates_machine_state") is not False:
        errors.append("state conflict incorrectly mutates machine state")
    if conflict.get("conflict_mutates_state_claims") is not False:
        errors.append("state conflict incorrectly mutates claims")
    if conflict.get("host_wall_clock_in_identity") is not False:
        errors.append("state conflict portable identity depends on host wall clock")
    if conflict.get("python_object_identity_in_identity") is not False:
        errors.append("state conflict portable identity depends on Python object identity")
    conflict_runtime = conflict.get("runtime", {})
    if conflict_runtime.get("contract_id") != STATE_CONFLICT_RUNTIME_CONTRACT_ID:
        errors.append("S3 state conflict runtime contract missing")
    if conflict_runtime.get("claim_source") != "EXISTING_AASM_STATE_CLAIM_PROJECTION_ONLY":
        errors.append("state conflict bypassed existing state claims")
    if conflict_runtime.get("authority") != "EXISTING_AASM_SCOPED_AUTHORITY_ONLY":
        errors.append("state conflict introduced parallel authority")
    if conflict_runtime.get("observation_authority_elevation") != "NONE":
        errors.append("state conflict elevates observation authority")
    if conflict_runtime.get("parallel_truth_table") != "NONE":
        errors.append("state conflict introduced parallel truth table")
    if conflict_runtime.get("parallel_dependency_graph") != "NONE":
        errors.append("state conflict introduced parallel dependency graph")

    causal = PUBLIC_API_CONTRACT.get("event_causality", {})
    if causal.get("contract_id") != EVENT_CAUSALITY_CONTRACT_ID:
        errors.append("S3 event causality semantic contract missing")
    if causal.get("local_event_identity") != "NODE_ID_PLUS_BOOT_EPOCH_PLUS_MONOTONIC_LOCAL_SEQUENCE":
        errors.append("S3 causal local identity drift")
    if causal.get("receipt_order_implies_source_order") is not False:
        errors.append("receipt order incorrectly became source order")
    if causal.get("host_wall_clock") != "NOT_UNIVERSAL_TRUTH_AND_NEVER_IMPLICITLY_CAPTURED":
        errors.append("host wall clock incorrectly became causal truth")
    if causal.get("event_identity_grants_authority") is not False:
        errors.append("causal event identity incorrectly grants authority")
    if causal.get("relation_grants_fact_authority") is not False or causal.get("relation_grants_effect_authority") is not False:
        errors.append("causal relation incorrectly grants authority")
    if causal.get("parallel_event_ledger") != "NONE":
        errors.append("event causality introduced parallel event ledger")
    causal_runtime = causal.get("runtime", {})
    if causal_runtime.get("contract_id") != EVENT_CAUSALITY_RUNTIME_CONTRACT_ID:
        errors.append("S3 event causality runtime contract missing")
    if causal_runtime.get("core_aasm_event_log") != "UNCHANGED_AND_REMAINS_REPLAY_LEDGER":
        errors.append("event causality replaced core AASM event log")
    if causal_runtime.get("authority") != "EXISTING_AASM_SCOPED_AUTHORITY_ONLY":
        errors.append("event causality introduced parallel authority")
    if causal_runtime.get("same_node_boot_order") != "SEQUENCE_DEFINES_LOCAL_ORDER_INDEPENDENT_OF_INGEST_ORDER":
        errors.append("event causality local sequence semantics drift")
    if causal_runtime.get("parallel_event_ledger") != "NONE":
        errors.append("event causality runtime introduced parallel event ledger")
    if causal_runtime.get("parallel_truth_table") != "NONE":
        errors.append("event causality runtime introduced parallel truth table")

    freshness = PUBLIC_API_CONTRACT.get("observation_freshness", {})
    if freshness.get("contract_id") != OBSERVATION_FRESHNESS_CONTRACT_ID:
        errors.append("S3 observation freshness semantic contract missing")
    if freshness.get("reference_time") != "EXPLICIT_INTEGER_NANOSECONDS_NEVER_IMPLICIT_HOST_NOW":
        errors.append("freshness reference time became implicit")
    if freshness.get("freshness_grants_fact_authority") is not False:
        errors.append("freshness incorrectly grants fact authority")
    if freshness.get("freshness_grants_effect_authority") is not False:
        errors.append("freshness incorrectly grants effect authority")
    if freshness.get("freshness_elevates_observation_authority") is not False:
        errors.append("freshness incorrectly elevates observation authority")
    if freshness.get("freshness_is_universal_admission") is not False:
        errors.append("freshness incorrectly became universal admission")
    freshness_runtime = freshness.get("runtime", {})
    if freshness_runtime.get("contract_id") != OBSERVATION_FRESHNESS_RUNTIME_CONTRACT_ID:
        errors.append("S3 observation freshness runtime contract missing")
    if freshness_runtime.get("observation_source") != "EXISTING_MACHINE_STATE_OBSERVATION_ONLY":
        errors.append("freshness bypassed existing machine observation")
    if freshness_runtime.get("causal_source") != "EXACT_DURABLE_CAUSAL_EVENT_ID_AND_FINGERPRINT":
        errors.append("freshness causal binding drift")
    if freshness_runtime.get("reference_time_source") != "EXPLICIT_CALLER_POLICY_INPUT_NOT_HOST_NOW":
        errors.append("freshness runtime uses implicit host time")
    if freshness_runtime.get("observation_authority_elevation") != "NONE":
        errors.append("freshness runtime elevates observation authority")
    if freshness_runtime.get("universal_admission") != "NONE":
        errors.append("freshness runtime grants universal admission")
    if freshness_runtime.get("parallel_observation_store") != "NONE":
        errors.append("freshness runtime introduced parallel observation store")
    if freshness_runtime.get("parallel_truth_table") != "NONE":
        errors.append("freshness runtime introduced parallel truth table")

    return {"valid": not errors, "errors": errors, "contract": public_api_contract()}


from . import demo_stack as _demo_stack
_demo_stack.AASMEngine = AASMEngine
_demo_stack._runtime_version = lambda: __version__
