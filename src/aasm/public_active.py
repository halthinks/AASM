from __future__ import annotations

from copy import deepcopy

from . import public_v56 as _base

for _name in dir(_base):
    if not _name.startswith("_"):
        globals()[_name] = getattr(_base, _name)

from .calibration import (
    CALIBRATION_CONTRACT_ID,
    CALIBRATION_CONTRACT_VERSION,
    CALIBRATION_KINDS,
    CALIBRATION_STABILITY,
    CalibrationCertificate,
    CalibrationRevocation,
    calibration_contract,
)
from .calibration_runtime import (
    CALIBRATION_CAPABILITIES,
    CALIBRATION_RUNTIME_CONTRACT_ID,
    CALIBRATION_RUNTIME_CONTRACT_VERSION,
    CALIBRATION_RUNTIME_STABILITY,
    calibration_runtime_contract,
    project_calibration_evidence,
)
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
from .execution_environment import (
    ENVIRONMENT_BINDING_OBJECT_KINDS,
    EXECUTION_ENVIRONMENT_BINDING_CONTRACT_ID,
    EXECUTION_ENVIRONMENT_BINDING_CONTRACT_VERSION,
    EXECUTION_ENVIRONMENT_CONTRACT_ID,
    EXECUTION_ENVIRONMENT_CONTRACT_VERSION,
    EXECUTION_ENVIRONMENT_LEVELS,
    EXECUTION_ENVIRONMENT_STABILITY,
    EnvironmentEvidenceBinding,
    ExecutionEnvironment,
    environment_level_accepted,
    execution_environment_contract,
)
from .execution_environment_runtime import (
    EXECUTION_ENVIRONMENT_CAPABILITIES,
    EXECUTION_ENVIRONMENT_RUNTIME_CONTRACT_ID,
    EXECUTION_ENVIRONMENT_RUNTIME_CONTRACT_VERSION,
    EXECUTION_ENVIRONMENT_RUNTIME_STABILITY,
    execution_environment_runtime_contract,
    project_execution_environment_evidence,
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
from .physical_identity import (
    PHYSICAL_IDENTITY_CLASSES,
    PHYSICAL_IDENTITY_CONTRACT_ID,
    PHYSICAL_IDENTITY_CONTRACT_VERSION,
    PHYSICAL_IDENTITY_STABILITY,
    PhysicalIdentity,
    physical_identity_contract,
)
from .physical_identity_runtime import (
    PHYSICAL_IDENTITY_CAPABILITIES,
    PHYSICAL_IDENTITY_RUNTIME_CONTRACT_ID,
    PHYSICAL_IDENTITY_RUNTIME_CONTRACT_VERSION,
    PHYSICAL_IDENTITY_RUNTIME_STABILITY,
    physical_identity_runtime_contract,
    project_physical_identity_evidence,
)
from .physical_preemption import (
    AUTHORITY_PREEMPTION_CONTRACT_ID,
    AUTHORITY_PREEMPTION_CONTRACT_VERSION,
    AUTHORITY_PREEMPTION_STABILITY,
    AuthorityPreemption,
    authority_preemption_contract,
)
from .source_trust import (
    SOURCE_KINDS,
    SOURCE_TRUST_CONTRACT_ID,
    SOURCE_TRUST_CONTRACT_VERSION,
    SOURCE_TRUST_DISPOSITIONS,
    SOURCE_TRUST_STABILITY,
    SourceTrustAssertion,
    SourceTrustRevocation,
    source_trust_contract,
)
from .source_trust_runtime import (
    SOURCE_TRUST_CAPABILITIES,
    SOURCE_TRUST_RUNTIME_CONTRACT_ID,
    SOURCE_TRUST_RUNTIME_CONTRACT_VERSION,
    SOURCE_TRUST_RUNTIME_STABILITY,
    project_source_trust_evidence,
    source_trust_runtime_contract,
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
    "physical_identity_contract_report",
    "record_physical_identity",
    "physical_identity_report",
    "physical_identities_report",
    "calibration_contract_report",
    "record_calibration",
    "revoke_calibration",
    "calibration_report",
    "calibrations_report",
    "source_trust_contract_report",
    "record_source_trust",
    "revoke_source_trust",
    "source_trust_report",
    "source_trust_assertions_report",
    "execution_environment_contract_report",
    "record_execution_environment",
    "bind_machine_observation_environment",
    "execution_environment_report",
    "execution_environment_binding_report",
    "execution_environments_report",
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
    "PHYSICAL_IDENTITY_CONTRACT_ID",
    "PHYSICAL_IDENTITY_CONTRACT_VERSION",
    "PHYSICAL_IDENTITY_STABILITY",
    "PHYSICAL_IDENTITY_CLASSES",
    "PhysicalIdentity",
    "physical_identity_contract",
    "PHYSICAL_IDENTITY_RUNTIME_CONTRACT_ID",
    "PHYSICAL_IDENTITY_RUNTIME_CONTRACT_VERSION",
    "PHYSICAL_IDENTITY_RUNTIME_STABILITY",
    "PHYSICAL_IDENTITY_CAPABILITIES",
    "project_physical_identity_evidence",
    "physical_identity_runtime_contract",
    "CALIBRATION_CONTRACT_ID",
    "CALIBRATION_CONTRACT_VERSION",
    "CALIBRATION_STABILITY",
    "CALIBRATION_KINDS",
    "CalibrationCertificate",
    "CalibrationRevocation",
    "calibration_contract",
    "CALIBRATION_RUNTIME_CONTRACT_ID",
    "CALIBRATION_RUNTIME_CONTRACT_VERSION",
    "CALIBRATION_RUNTIME_STABILITY",
    "CALIBRATION_CAPABILITIES",
    "project_calibration_evidence",
    "calibration_runtime_contract",
    "SOURCE_TRUST_CONTRACT_ID",
    "SOURCE_TRUST_CONTRACT_VERSION",
    "SOURCE_TRUST_STABILITY",
    "SOURCE_KINDS",
    "SOURCE_TRUST_DISPOSITIONS",
    "SourceTrustAssertion",
    "SourceTrustRevocation",
    "source_trust_contract",
    "SOURCE_TRUST_RUNTIME_CONTRACT_ID",
    "SOURCE_TRUST_RUNTIME_CONTRACT_VERSION",
    "SOURCE_TRUST_RUNTIME_STABILITY",
    "SOURCE_TRUST_CAPABILITIES",
    "project_source_trust_evidence",
    "source_trust_runtime_contract",
    "EXECUTION_ENVIRONMENT_CONTRACT_ID",
    "EXECUTION_ENVIRONMENT_CONTRACT_VERSION",
    "EXECUTION_ENVIRONMENT_BINDING_CONTRACT_ID",
    "EXECUTION_ENVIRONMENT_BINDING_CONTRACT_VERSION",
    "EXECUTION_ENVIRONMENT_STABILITY",
    "EXECUTION_ENVIRONMENT_LEVELS",
    "ENVIRONMENT_BINDING_OBJECT_KINDS",
    "ExecutionEnvironment",
    "EnvironmentEvidenceBinding",
    "environment_level_accepted",
    "execution_environment_contract",
    "EXECUTION_ENVIRONMENT_RUNTIME_CONTRACT_ID",
    "EXECUTION_ENVIRONMENT_RUNTIME_CONTRACT_VERSION",
    "EXECUTION_ENVIRONMENT_RUNTIME_STABILITY",
    "EXECUTION_ENVIRONMENT_CAPABILITIES",
    "project_execution_environment_evidence",
    "execution_environment_runtime_contract",
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
    "physical-identity",
    "calibration",
    "source-trust",
    "execution-environment",
]))
SUPPORTED_PUBLIC_IMPORTS = list(dict.fromkeys([*getattr(_base, "SUPPORTED_PUBLIC_IMPORTS", []), *_NEW_IMPORTS]))

PUBLIC_API_CONTRACT = deepcopy(_base.PUBLIC_API_CONTRACT)
PUBLIC_API_CONTRACT.update({
    "contract_version": "0.32.12",
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
    "dependent_effect_integration": PHYSICAL_EFFECT_INTEGRATION_RUNTIME_CONTRACT_ID,
}
PUBLIC_API_CONTRACT["physical_control_fencing"] = {
    **physical_control_fencing_runtime_contract(),
    "effect_capability_use": effect_capability_use_contract(),
    "authority_preemption": authority_preemption_contract(),
    "preemption_recovery": "EXISTING_EVIDENCE_REPLAY_REPAIRS_MISSING_CANONICAL_LEASE_REVOCATION",
    "dependent_effect_integration": PHYSICAL_EFFECT_INTEGRATION_RUNTIME_CONTRACT_ID,
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
PUBLIC_API_CONTRACT["physical_identity"] = {
    **physical_identity_contract(),
    "runtime": physical_identity_runtime_contract(),
}
PUBLIC_API_CONTRACT["calibration"] = {
    **calibration_contract(),
    "runtime": calibration_runtime_contract(),
}
PUBLIC_API_CONTRACT["source_trust"] = {
    **source_trust_contract(),
    "runtime": source_trust_runtime_contract(),
}
PUBLIC_API_CONTRACT["execution_environment"] = {
    **execution_environment_contract(),
    "runtime": execution_environment_runtime_contract(),
}
PUBLIC_API_CONTRACT["distribution"]["version"] = __version__
PUBLIC_API_CONTRACT["distribution"]["stability"] = PUBLIC_RELEASE_STABILITY


def public_api_contract():
    return deepcopy(PUBLIC_API_CONTRACT)


def validate_public_api_contract():
    parent = _base.validate_public_api_contract()
    errors: list[str] = []
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
    if PUBLIC_API_CONTRACT.get("contract_version") != "0.32.12":
        errors.append("active adoption contract mismatch")

    capability = PUBLIC_API_CONTRACT.get("effect_capability", {})
    if capability.get("capability_existence_grants_effect_authority") is not False:
        errors.append("effect capability existence incorrectly grants effect authority")
    if capability.get("dependent_effect_integration") != PHYSICAL_EFFECT_INTEGRATION_RUNTIME_CONTRACT_ID:
        errors.append("effect capability missing inherited physical-effect integration")
    cap_runtime = capability.get("runtime", {})
    if cap_runtime.get("authority") != "EXISTING_AASM_SCOPED_AUTHORITY_ONLY":
        errors.append("effect capability introduced parallel authority evaluator")
    if cap_runtime.get("effect_dispatch") != "NONE" or cap_runtime.get("parallel_effect_lifecycle") != "NONE":
        errors.append("effect capability introduced effect execution/lifecycle")

    fencing = PUBLIC_API_CONTRACT.get("physical_control_fencing", {})
    if fencing.get("use_validation_grants_effect_authority") is not False or fencing.get("preemption_grants_effect_authority") is not False:
        errors.append("physical-control evidence incorrectly grants effect authority")
    if fencing.get("parallel_authority_evaluator") != "NONE" or fencing.get("parallel_effect_lifecycle") != "NONE":
        errors.append("physical-control fencing introduced a parallel authority/effect plane")
    if fencing.get("effect_capability_use", {}).get("validation_is_reusable_authorization_token") is not False:
        errors.append("capability-use validation became a reusable authorization token")

    integration = PUBLIC_API_CONTRACT.get("physical_effect_integration", {})
    integration_runtime = integration.get("runtime", {})
    if integration.get("contract_id") != PHYSICAL_EFFECT_AUTHORITY_BINDING_CONTRACT_ID:
        errors.append("physical effect binding contract missing")
    if integration.get("binding_existence_grants_effect_authority") is not False:
        errors.append("physical effect binding incorrectly grants effect authority")
    if integration.get("prior_use_validation_is_authorization") is not False:
        errors.append("prior capability-use validation became authorization")
    if integration_runtime.get("effect_authority") != "EXISTING_V53_EFFECT_AUTHORIZE_AND_EFFECT_EXECUTE_REMAIN_REQUIRED":
        errors.append("physical effect integration replaced existing effect authority")
    for key in ("parallel_authority_evaluator", "parallel_effect_store", "parallel_effect_lifecycle", "parallel_dispatcher"):
        if integration_runtime.get(key) != "NONE":
            errors.append(f"physical effect integration introduced {key}")

    conflict = PUBLIC_API_CONTRACT.get("state_conflict", {})
    if conflict.get("contract_id") != STATE_CONFLICT_CONTRACT_ID:
        errors.append("S3 state-conflict contract missing")
    if conflict.get("conflict_grants_fact_authority") is not False or conflict.get("conflict_grants_effect_authority") is not False:
        errors.append("state conflict incorrectly grants authority")
    if conflict.get("conflict_mutates_machine_state") is not False or conflict.get("conflict_mutates_state_claims") is not False:
        errors.append("state conflict incorrectly mutates state")
    if conflict.get("runtime", {}).get("parallel_truth_table") != "NONE":
        errors.append("state conflict introduced parallel truth")

    causal = PUBLIC_API_CONTRACT.get("event_causality", {})
    causal_runtime = causal.get("runtime", {})
    if causal.get("contract_id") != EVENT_CAUSALITY_CONTRACT_ID:
        errors.append("S3 event-causality contract missing")
    if causal.get("receipt_order_implies_source_order") is not False:
        errors.append("receipt order incorrectly became source order")
    if causal.get("event_identity_grants_authority") is not False:
        errors.append("causal identity incorrectly grants authority")
    if causal_runtime.get("core_aasm_event_log") != "UNCHANGED_AND_REMAINS_REPLAY_LEDGER":
        errors.append("causality replaced the existing AASM event ledger")
    if causal_runtime.get("parallel_event_ledger") != "NONE" or causal_runtime.get("parallel_truth_table") != "NONE":
        errors.append("causality introduced a parallel event/truth plane")

    freshness = PUBLIC_API_CONTRACT.get("observation_freshness", {})
    freshness_runtime = freshness.get("runtime", {})
    if freshness.get("contract_id") != OBSERVATION_FRESHNESS_CONTRACT_ID:
        errors.append("S3 observation-freshness contract missing")
    if freshness.get("freshness_grants_fact_authority") is not False or freshness.get("freshness_grants_effect_authority") is not False:
        errors.append("freshness incorrectly grants authority")
    if freshness.get("freshness_is_universal_admission") is not False:
        errors.append("freshness incorrectly became universal admission")
    if freshness_runtime.get("reference_time_source") != "EXPLICIT_CALLER_POLICY_INPUT_NOT_HOST_NOW":
        errors.append("freshness runtime uses implicit host time")
    if freshness_runtime.get("parallel_observation_store") != "NONE" or freshness_runtime.get("parallel_truth_table") != "NONE":
        errors.append("freshness introduced a parallel observation/truth plane")

    identity = PUBLIC_API_CONTRACT.get("physical_identity", {})
    identity_runtime = identity.get("runtime", {})
    if identity.get("contract_id") != PHYSICAL_IDENTITY_CONTRACT_ID:
        errors.append("S3 physical-identity contract missing")
    if identity.get("role") != "EXACT_EXTERNAL_SUBJECT_INSTANCE_CONFIGURATION_REFERENCE_NOT_TRUTH_OR_AUTHORITY_BY_EXISTENCE":
        errors.append("physical identity role drift")
    if identity.get("identity_existence_grants_fact_authority") is not False or identity.get("identity_existence_grants_effect_authority") is not False:
        errors.append("physical identity incorrectly grants authority")
    if identity.get("identity_existence_grants_source_trust") is not False:
        errors.append("physical identity incorrectly grants source trust")
    if identity.get("host_wall_clock_in_identity") is not False or identity.get("python_object_identity_in_identity") is not False:
        errors.append("physical identity is not portable")
    if identity_runtime.get("authority") != "EXISTING_AASM_SCOPED_AUTHORITY_ONLY":
        errors.append("physical identity introduced parallel authority")
    if identity_runtime.get("source_trust") != "NONE_IDENTITY_IS_ONLY_AN_EXACT_REFERENCE":
        errors.append("physical identity implicitly grants source trust")
    if identity_runtime.get("parallel_identity_registry") != "NONE_EVIDENCE_PROJECTION_ONLY" or identity_runtime.get("parallel_truth_table") != "NONE":
        errors.append("physical identity introduced a parallel registry/truth plane")

    calibration = PUBLIC_API_CONTRACT.get("calibration", {})
    calibration_runtime = calibration.get("runtime", {})
    if calibration.get("contract_id") != CALIBRATION_CONTRACT_ID:
        errors.append("S3 calibration contract missing")
    if calibration.get("identity_binding") != "EXACT_PHYSICAL_IDENTITY_ID_AND_FINGERPRINT_REQUIRED":
        errors.append("calibration identity binding drift")
    if calibration.get("selection") != "EXPLICIT_CALIBRATION_ID_NO_HIDDEN_CURRENT_CALIBRATION_POINTER":
        errors.append("calibration acquired hidden current selection")
    if calibration.get("transform_application") != "NOT_IMPLEMENTED_IN_S3_FOUNDATION":
        errors.append("calibration silently applies transforms")
    if calibration.get("calibration_existence_grants_fact_authority") is not False or calibration.get("calibration_existence_grants_effect_authority") is not False:
        errors.append("calibration incorrectly grants authority")
    if calibration.get("calibration_existence_grants_source_trust") is not False or calibration.get("calibration_mutates_observation") is not False:
        errors.append("calibration incorrectly grants trust or rewrites observation")
    if calibration_runtime.get("validity_reference") != "EXPLICIT_CALLER_NANOSECOND_TIME_ONLY":
        errors.append("calibration validity uses implicit time")
    if calibration_runtime.get("parallel_calibration_store") != "NONE_EVIDENCE_PROJECTION_ONLY" or calibration_runtime.get("parallel_truth_table") != "NONE":
        errors.append("calibration introduced a parallel store/truth plane")

    trust = PUBLIC_API_CONTRACT.get("source_trust", {})
    trust_runtime = trust.get("runtime", {})
    if trust.get("contract_id") != SOURCE_TRUST_CONTRACT_ID:
        errors.append("S3 source-trust contract missing")
    if trust.get("role") != "EXPLICIT_POLICY_INPUT_ABOUT_A_SOURCE_NOT_FACT_AUTHORITY_OR_EFFECT_AUTHORITY":
        errors.append("source trust role drift")
    if trust.get("aggregation") != "NONE_NO_TRUST_SCORE_NO_VOTING_NO_AUTOMATIC_LATEST_ASSERTION":
        errors.append("source trust acquired aggregation/reputation")
    if trust.get("trusted_disposition_grants_fact_authority") is not False or trust.get("trusted_disposition_grants_effect_authority") is not False:
        errors.append("trusted disposition incorrectly grants authority")
    if trust.get("trusted_disposition_makes_claim_authoritative") is not False or trust.get("source_trust_is_universal_admission") is not False:
        errors.append("source trust incorrectly admits claims")
    if trust_runtime.get("fact_authority") != "EXISTING_FACT_AUTHORITY_REMAINS_SEPARATE_AND_REQUIRED":
        errors.append("source trust replaced FactAuthority")
    if trust_runtime.get("reputation_score") != "NONE" or trust_runtime.get("parallel_authority_evaluator") != "NONE":
        errors.append("source trust introduced reputation/parallel authority")
    if trust_runtime.get("parallel_trust_registry") != "NONE_EVIDENCE_PROJECTION_ONLY" or trust_runtime.get("parallel_truth_table") != "NONE":
        errors.append("source trust introduced a parallel trust/truth plane")

    environment = PUBLIC_API_CONTRACT.get("execution_environment", {})
    environment_runtime = environment.get("runtime", {})
    if environment.get("contract_id") != EXECUTION_ENVIRONMENT_CONTRACT_ID:
        errors.append("S3 execution-environment contract missing")
    if environment.get("level_ordering") != "NONE":
        errors.append("execution environment acquired ordinal level semantics")
    if environment.get("higher_level_implies_truth") is not False or environment.get("higher_level_implies_authority") is not False:
        errors.append("execution environment level incorrectly implies truth/authority")
    if environment.get("automatic_level_upgrade") is not False:
        errors.append("execution environment permits automatic level upgrade")
    if environment.get("simulation_as_physical") != "REJECT_EXACT_ACCEPTED_LEVELS_ONLY":
        errors.append("execution environment simulation-as-physical firewall drift")
    if environment.get("environment_existence_grants_fact_authority") is not False or environment.get("environment_existence_grants_effect_authority") is not False:
        errors.append("execution environment existence incorrectly grants authority")
    if environment.get("environment_existence_grants_source_trust") is not False or environment.get("environment_level_is_universal_admission") is not False:
        errors.append("execution environment incorrectly grants trust/admission")
    if environment_runtime.get("authority") != "EXISTING_AASM_SCOPED_AUTHORITY_ONLY_FOR_RECORD_BIND_NOT_ENVIRONMENT_TRUTH":
        errors.append("execution environment record authority became environment truth authority")
    if environment_runtime.get("level_acceptance") != "EXACT_ACCEPTED_LEVEL_SET_MEMBERSHIP_NO_ORDINAL_INFERENCE":
        errors.append("execution environment level acceptance drift")
    if environment_runtime.get("environment_level_authority") != "NONE":
        errors.append("execution environment level acquired authority")
    if environment_runtime.get("parallel_environment_store") != "NONE_EVIDENCE_PROJECTION_ONLY" or environment_runtime.get("parallel_truth_table") != "NONE":
        errors.append("execution environment introduced parallel store/truth")
    if environment_runtime.get("parallel_authority_evaluator") != "NONE":
        errors.append("execution environment introduced parallel authority evaluator")

    return {"valid": not errors, "errors": errors, "contract": public_api_contract()}


from . import demo_stack as _demo_stack
_demo_stack.AASMEngine = AASMEngine
_demo_stack._runtime_version = lambda: __version__
