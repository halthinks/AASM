from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
import re
from typing import Any, Mapping, Sequence

from .effect_capability import EFFECT_CAPABILITY_CONTRACT_ID, EffectCapability
from .semantic_result import semantic_fingerprint


DEGRADED_OPERATION_CONTRACT_ID = "aasm.degraded.operation.v1"
DEGRADED_OPERATION_CONTRACT_VERSION = "0.1.0"
DEGRADED_OPERATION_ASSESSMENT_CONTRACT_ID = "aasm.degraded.operation.assessment.v1"
DEGRADED_OPERATION_ASSESSMENT_CONTRACT_VERSION = "0.1.0"
DEGRADED_OPERATION_STABILITY = "FOUNDATION_EXPERIMENTAL"

DEGRADED_OPERATION_MODES = (
    "FULL_OPERATION",
    "DEGRADED_OPERATION",
    "LOCAL_ONLY",
    "SAFE_HOLD",
    "RETURN_TO_SAFE_STATE",
    "EMERGENCY",
)
DEPENDENCY_STATUSES = ("AVAILABLE", "DEGRADED", "UNAVAILABLE", "UNKNOWN")
EFFECT_POLICIES = ("EXISTING_CAPABILITY_SUBSET_ONLY", "NO_NEW_EFFECTS")
REMOTE_DEPENDENCY_POLICIES = ("ALLOW", "FORBID")
PREEMPTION_REQUIREMENTS = ("NONE", "EXPLICIT_EXISTING_PREEMPTION_REQUIRED")
RECOVERY_INTENTS = ("NONE", "HOLD", "RETURN_TO_SAFE_STATE", "EMERGENCY_RESPONSE")
DEGRADED_ASSESSMENT_STATUSES = ("SELECTED", "FAIL_CLOSED")

_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _required(name: str, value: Any) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError(f"degraded operation {name} is required")
    return text


def _optional(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _sha256(name: str, value: Any) -> str:
    text = _required(name, value).lower()
    if not _SHA256.fullmatch(text):
        raise ValueError(f"degraded operation {name} must be a lowercase 64-hex SHA-256 digest")
    return text


def _uniq(values: Sequence[Any], *, name: str, allow_empty: bool = True) -> tuple[str, ...]:
    normalized = tuple(sorted({_required(name, value) for value in values}))
    if not normalized and not allow_empty:
        raise ValueError(f"degraded operation {name} requires at least one value")
    return normalized


def _jsonable(value: Any) -> Any:
    if hasattr(value, "identity_payload"):
        return _jsonable(value.identity_payload())
    if hasattr(value, "to_dict"):
        return _jsonable(value.to_dict())
    if isinstance(value, Mapping):
        return {
            str(key): _jsonable(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (tuple, list, set)):
        return [_jsonable(item) for item in value]
    if isinstance(value, float):
        raise TypeError("binary floating-point values are forbidden in degraded-operation portable identity")
    if isinstance(value, (str, int, bool)) or value is None:
        return value
    raise TypeError(f"degraded-operation value is not JSON serializable: {type(value)!r}")


def _revision_pair(revision_id: Any, revision_fingerprint: Any, *, prefix: str) -> tuple[str, str]:
    rid = _optional(revision_id)
    rfp = _optional(revision_fingerprint)
    if bool(rid) != bool(rfp):
        raise ValueError(f"degraded operation {prefix} revision id and fingerprint must be supplied together")
    if rfp:
        rfp = _sha256(f"{prefix} revision fingerprint", rfp)
    return rid, rfp


@dataclass(frozen=True)
class DependencyState:
    dependency_id: str
    status: str
    evidence_ids: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        dependency_id = _required("dependency_id", self.dependency_id)
        status = _required("dependency status", self.status).upper()
        if status not in DEPENDENCY_STATUSES:
            raise ValueError(f"unsupported degraded-operation dependency status: {status}")
        object.__setattr__(self, "dependency_id", dependency_id)
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "evidence_ids", _uniq(self.evidence_ids, name="evidence_id"))
        object.__setattr__(self, "metadata", _jsonable(dict(self.metadata)))

    def identity_payload(self) -> dict[str, Any]:
        return {
            "dependency_id": self.dependency_id,
            "status": self.status,
            "evidence_ids": list(self.evidence_ids),
            "metadata": _jsonable(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(self.identity_payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "DependencyState":
        payload = deepcopy(dict(value))
        supplied = str(payload.pop("fingerprint", "")).strip()
        payload["evidence_ids"] = tuple(payload.get("evidence_ids") or ())
        item = cls(**payload)
        if supplied and supplied != item.fingerprint:
            raise ValueError("degraded-operation dependency-state fingerprint mismatch")
        return item


@dataclass(frozen=True)
class DependencyRequirement:
    dependency_id: str
    allowed_statuses: tuple[str, ...]

    def __post_init__(self) -> None:
        dependency_id = _required("dependency requirement id", self.dependency_id)
        statuses = tuple(sorted({_required("allowed dependency status", value).upper() for value in self.allowed_statuses}))
        if not statuses:
            raise ValueError("degraded-operation dependency requirement requires allowed_statuses")
        unknown = sorted(set(statuses) - set(DEPENDENCY_STATUSES))
        if unknown:
            raise ValueError(f"unsupported degraded-operation dependency statuses: {unknown}")
        if "UNKNOWN" in statuses:
            raise ValueError("UNKNOWN dependency status cannot authorize/select an operational mode")
        object.__setattr__(self, "dependency_id", dependency_id)
        object.__setattr__(self, "allowed_statuses", statuses)

    def identity_payload(self) -> dict[str, Any]:
        return {"dependency_id": self.dependency_id, "allowed_statuses": list(self.allowed_statuses)}

    def to_dict(self) -> dict[str, Any]:
        return self.identity_payload()

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "DependencyRequirement":
        return cls(str(value["dependency_id"]), tuple(value.get("allowed_statuses") or ()))


@dataclass(frozen=True)
class DegradedModeEnvelope:
    mode: str
    allowed_operations: tuple[str, ...]
    effect_policy: str = "EXISTING_CAPABILITY_SUBSET_ONLY"
    remote_dependency_policy: str = "ALLOW"
    preemption_requirement: str = "NONE"
    recovery_intent: str = "NONE"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        mode = _required("mode", self.mode).upper()
        if mode not in DEGRADED_OPERATION_MODES:
            raise ValueError(f"unsupported degraded-operation mode: {mode}")
        operations = _uniq(self.allowed_operations, name="allowed operation")
        effect_policy = _required("effect policy", self.effect_policy).upper()
        remote_policy = _required("remote dependency policy", self.remote_dependency_policy).upper()
        preemption = _required("preemption requirement", self.preemption_requirement).upper()
        recovery = _required("recovery intent", self.recovery_intent).upper()
        if effect_policy not in EFFECT_POLICIES:
            raise ValueError(f"unsupported degraded-operation effect policy: {effect_policy}")
        if remote_policy not in REMOTE_DEPENDENCY_POLICIES:
            raise ValueError(f"unsupported degraded-operation remote dependency policy: {remote_policy}")
        if preemption not in PREEMPTION_REQUIREMENTS:
            raise ValueError(f"unsupported degraded-operation preemption requirement: {preemption}")
        if recovery not in RECOVERY_INTENTS:
            raise ValueError(f"unsupported degraded-operation recovery intent: {recovery}")

        if effect_policy == "NO_NEW_EFFECTS" and operations:
            raise ValueError("NO_NEW_EFFECTS degraded envelope cannot carry allowed operations")
        if mode == "SAFE_HOLD":
            if effect_policy != "NO_NEW_EFFECTS" or operations or recovery != "HOLD":
                raise ValueError("SAFE_HOLD requires NO_NEW_EFFECTS, no operations, and HOLD recovery intent")
        if mode == "LOCAL_ONLY" and remote_policy != "FORBID":
            raise ValueError("LOCAL_ONLY must forbid remote dependencies")
        if mode == "RETURN_TO_SAFE_STATE" and recovery != "RETURN_TO_SAFE_STATE":
            raise ValueError("RETURN_TO_SAFE_STATE mode requires matching recovery intent")
        if mode == "EMERGENCY" and recovery != "EMERGENCY_RESPONSE":
            raise ValueError("EMERGENCY mode requires EMERGENCY_RESPONSE recovery intent")
        if mode == "FULL_OPERATION" and recovery != "NONE":
            raise ValueError("FULL_OPERATION cannot carry a recovery intent")

        object.__setattr__(self, "mode", mode)
        object.__setattr__(self, "allowed_operations", operations)
        object.__setattr__(self, "effect_policy", effect_policy)
        object.__setattr__(self, "remote_dependency_policy", remote_policy)
        object.__setattr__(self, "preemption_requirement", preemption)
        object.__setattr__(self, "recovery_intent", recovery)
        object.__setattr__(self, "metadata", _jsonable(dict(self.metadata)))

    def identity_payload(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "allowed_operations": list(self.allowed_operations),
            "effect_policy": self.effect_policy,
            "remote_dependency_policy": self.remote_dependency_policy,
            "preemption_requirement": self.preemption_requirement,
            "recovery_intent": self.recovery_intent,
            "metadata": _jsonable(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(self.identity_payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "DegradedModeEnvelope":
        payload = deepcopy(dict(value))
        supplied = str(payload.pop("fingerprint", "")).strip()
        payload["allowed_operations"] = tuple(payload.get("allowed_operations") or ())
        item = cls(**payload)
        if supplied and supplied != item.fingerprint:
            raise ValueError("degraded-operation mode-envelope fingerprint mismatch")
        return item


@dataclass(frozen=True)
class ModeSelectionRule:
    rule_id: str
    mode: str
    requirements: tuple[DependencyRequirement | Mapping[str, Any], ...]
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        rule_id = _required("selection rule_id", self.rule_id)
        mode = _required("selection mode", self.mode).upper()
        if mode not in DEGRADED_OPERATION_MODES:
            raise ValueError(f"unsupported degraded-operation selection mode: {mode}")
        requirements = tuple(
            value if isinstance(value, DependencyRequirement) else DependencyRequirement.from_dict(value)
            for value in self.requirements
        )
        if not requirements:
            raise ValueError("degraded-operation selection rule requires dependency requirements")
        ids = [value.dependency_id for value in requirements]
        if len(ids) != len(set(ids)):
            raise ValueError("degraded-operation selection rule has duplicate dependency requirements")
        requirements = tuple(sorted(requirements, key=lambda value: value.dependency_id))
        object.__setattr__(self, "rule_id", rule_id)
        object.__setattr__(self, "mode", mode)
        object.__setattr__(self, "requirements", requirements)
        object.__setattr__(self, "metadata", _jsonable(dict(self.metadata)))

    def identity_payload(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "mode": self.mode,
            "requirements": [value.identity_payload() for value in self.requirements],
            "metadata": _jsonable(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(self.identity_payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ModeSelectionRule":
        payload = deepcopy(dict(value))
        supplied = str(payload.pop("fingerprint", "")).strip()
        payload["requirements"] = tuple(payload.get("requirements") or ())
        item = cls(**payload)
        if supplied and supplied != item.fingerprint:
            raise ValueError("degraded-operation selection-rule fingerprint mismatch")
        return item


@dataclass(frozen=True)
class DegradedOperationPolicy:
    policy_name: str
    workspace_id: str
    scope_id: str
    subject_id: str
    base_capability_id: str
    base_capability_fingerprint: str
    problem_revision_id: str
    problem_revision_fingerprint: str
    dependency_ids: tuple[str, ...]
    mode_envelopes: tuple[DegradedModeEnvelope | Mapping[str, Any], ...]
    selection_rules: tuple[ModeSelectionRule | Mapping[str, Any], ...]
    fallback_mode: str = "SAFE_HOLD"
    metadata: Mapping[str, Any] = field(default_factory=dict)
    policy_id: str = ""
    contract_id: str = DEGRADED_OPERATION_CONTRACT_ID
    contract_version: str = DEGRADED_OPERATION_CONTRACT_VERSION

    def __post_init__(self) -> None:
        if self.contract_id != DEGRADED_OPERATION_CONTRACT_ID or self.contract_version != DEGRADED_OPERATION_CONTRACT_VERSION:
            raise ValueError("unsupported degraded-operation contract")
        for name in ("policy_name", "workspace_id", "scope_id", "subject_id", "base_capability_id"):
            object.__setattr__(self, name, _required(name, getattr(self, name)))
        object.__setattr__(self, "base_capability_fingerprint", _sha256("base capability fingerprint", self.base_capability_fingerprint))
        revision_id, revision_fingerprint = _revision_pair(
            self.problem_revision_id,
            self.problem_revision_fingerprint,
            prefix="problem",
        )
        if not revision_id:
            raise ValueError("degraded-operation policy requires exact problem revision binding")
        object.__setattr__(self, "problem_revision_id", revision_id)
        object.__setattr__(self, "problem_revision_fingerprint", revision_fingerprint)

        dependency_ids = _uniq(self.dependency_ids, name="dependency_id", allow_empty=False)
        object.__setattr__(self, "dependency_ids", dependency_ids)

        envelopes = tuple(
            value if isinstance(value, DegradedModeEnvelope) else DegradedModeEnvelope.from_dict(value)
            for value in self.mode_envelopes
        )
        modes = [value.mode for value in envelopes]
        if len(modes) != len(set(modes)):
            raise ValueError("degraded-operation policy has duplicate mode envelopes")
        if set(modes) != set(DEGRADED_OPERATION_MODES):
            raise ValueError("degraded-operation policy must define exactly one envelope for every mode")
        envelopes = tuple(sorted(envelopes, key=lambda value: DEGRADED_OPERATION_MODES.index(value.mode)))
        object.__setattr__(self, "mode_envelopes", envelopes)

        rules = tuple(
            value if isinstance(value, ModeSelectionRule) else ModeSelectionRule.from_dict(value)
            for value in self.selection_rules
        )
        if not rules:
            raise ValueError("degraded-operation policy requires selection rules")
        rule_ids = [value.rule_id for value in rules]
        if len(rule_ids) != len(set(rule_ids)):
            raise ValueError("degraded-operation policy selection rule IDs must be unique")
        required_ids = set(dependency_ids)
        full_rules = []
        for rule in rules:
            rule_dependency_ids = {value.dependency_id for value in rule.requirements}
            if rule_dependency_ids != required_ids:
                raise ValueError("every degraded-operation selection rule must cover the exact policy dependency set")
            if rule.mode == "FULL_OPERATION":
                full_rules.append(rule)
                if any(value.allowed_statuses != ("AVAILABLE",) for value in rule.requirements):
                    raise ValueError("FULL_OPERATION may be selected only when every dependency is AVAILABLE")
        if len(full_rules) != 1:
            raise ValueError("degraded-operation policy requires exactly one nominal FULL_OPERATION selection rule")
        rules = tuple(sorted(rules, key=lambda value: value.rule_id))
        object.__setattr__(self, "selection_rules", rules)

        fallback = _required("fallback_mode", self.fallback_mode).upper()
        if fallback != "SAFE_HOLD":
            raise ValueError("degraded-operation fallback mode must be SAFE_HOLD")
        safe_hold = next(value for value in envelopes if value.mode == "SAFE_HOLD")
        if safe_hold.effect_policy != "NO_NEW_EFFECTS" or safe_hold.allowed_operations:
            raise ValueError("degraded-operation SAFE_HOLD fallback must fail closed to no new effects")
        object.__setattr__(self, "fallback_mode", fallback)
        object.__setattr__(self, "metadata", _jsonable(dict(self.metadata)))

        derived = f"degraded-operation-policy-{semantic_fingerprint(self.identity_payload())[:24]}"
        supplied = _optional(self.policy_id)
        if supplied and supplied != derived:
            raise ValueError("degraded-operation policy_id does not match canonical identity")
        object.__setattr__(self, "policy_id", derived)

    def envelope(self, mode: str) -> DegradedModeEnvelope:
        normalized = str(mode).strip().upper()
        for value in self.mode_envelopes:
            if value.mode == normalized:
                return value
        raise KeyError(normalized)

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "policy_name": self.policy_name,
            "workspace_id": self.workspace_id,
            "scope_id": self.scope_id,
            "subject_id": self.subject_id,
            "base_capability_id": self.base_capability_id,
            "base_capability_fingerprint": self.base_capability_fingerprint,
            "problem_revision_id": self.problem_revision_id,
            "problem_revision_fingerprint": self.problem_revision_fingerprint,
            "dependency_ids": list(self.dependency_ids),
            "mode_envelopes": [value.identity_payload() for value in self.mode_envelopes],
            "selection_rules": [value.identity_payload() for value in self.selection_rules],
            "fallback_mode": self.fallback_mode,
            "metadata": _jsonable(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"policy_id": self.policy_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"policy_id": self.policy_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "DegradedOperationPolicy":
        payload = deepcopy(dict(value))
        supplied = str(payload.pop("fingerprint", "")).strip()
        for name in ("dependency_ids", "mode_envelopes", "selection_rules"):
            payload[name] = tuple(payload.get(name) or ())
        item = cls(**payload)
        if supplied and supplied != item.fingerprint:
            raise ValueError("degraded-operation policy fingerprint mismatch")
        return item


@dataclass(frozen=True)
class DegradedOperationContext:
    workspace_id: str
    scope_id: str
    subject_id: str
    problem_revision_id: str
    problem_revision_fingerprint: str
    dependency_states: tuple[DependencyState | Mapping[str, Any], ...]
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in ("workspace_id", "scope_id", "subject_id"):
            object.__setattr__(self, name, _required(name, getattr(self, name)))
        revision_id, revision_fingerprint = _revision_pair(
            self.problem_revision_id,
            self.problem_revision_fingerprint,
            prefix="context problem",
        )
        if not revision_id:
            raise ValueError("degraded-operation context requires exact problem revision binding")
        object.__setattr__(self, "problem_revision_id", revision_id)
        object.__setattr__(self, "problem_revision_fingerprint", revision_fingerprint)
        states = tuple(
            value if isinstance(value, DependencyState) else DependencyState.from_dict(value)
            for value in self.dependency_states
        )
        ids = [value.dependency_id for value in states]
        if len(ids) != len(set(ids)):
            raise ValueError("degraded-operation context has duplicate dependency states")
        states = tuple(sorted(states, key=lambda value: value.dependency_id))
        object.__setattr__(self, "dependency_states", states)
        object.__setattr__(self, "metadata", _jsonable(dict(self.metadata)))

    def identity_payload(self) -> dict[str, Any]:
        return {
            "workspace_id": self.workspace_id,
            "scope_id": self.scope_id,
            "subject_id": self.subject_id,
            "problem_revision_id": self.problem_revision_id,
            "problem_revision_fingerprint": self.problem_revision_fingerprint,
            "dependency_states": [value.identity_payload() for value in self.dependency_states],
            "metadata": _jsonable(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(self.identity_payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self.identity_payload(), "fingerprint": self.fingerprint}


@dataclass(frozen=True)
class DegradedOperationAssessment:
    policy_id: str
    policy_fingerprint: str
    capability_id: str
    capability_fingerprint: str
    context_fingerprint: str
    mode: str
    status: str
    allowed_operations: tuple[str, ...]
    effect_policy: str
    remote_dependency_policy: str
    preemption_requirement: str
    recovery_intent: str
    matched_rule_id: str = ""
    diagnostics: tuple[str, ...] = ()
    effect_authority_granted: bool = False
    reusable_authorization_token: bool = False
    mode_activation_performed: bool = False
    capability_liveness_checked: bool = False
    assessment_id: str = ""
    contract_id: str = DEGRADED_OPERATION_ASSESSMENT_CONTRACT_ID
    contract_version: str = DEGRADED_OPERATION_ASSESSMENT_CONTRACT_VERSION

    def __post_init__(self) -> None:
        for name in ("policy_id", "capability_id"):
            object.__setattr__(self, name, _required(name, getattr(self, name)))
        for name in ("policy_fingerprint", "capability_fingerprint", "context_fingerprint"):
            object.__setattr__(self, name, _sha256(name, getattr(self, name)))
        if self.contract_id != DEGRADED_OPERATION_ASSESSMENT_CONTRACT_ID or self.contract_version != DEGRADED_OPERATION_ASSESSMENT_CONTRACT_VERSION:
            raise ValueError("unsupported degraded-operation assessment contract")
        mode = _required("assessment mode", self.mode).upper()
        status = _required("assessment status", self.status).upper()
        if mode not in DEGRADED_OPERATION_MODES:
            raise ValueError(f"unsupported degraded-operation assessment mode: {mode}")
        if status not in DEGRADED_ASSESSMENT_STATUSES:
            raise ValueError(f"unsupported degraded-operation assessment status: {status}")
        effect_policy = _required("assessment effect policy", self.effect_policy).upper()
        remote_policy = _required("assessment remote dependency policy", self.remote_dependency_policy).upper()
        preemption = _required("assessment preemption requirement", self.preemption_requirement).upper()
        recovery = _required("assessment recovery intent", self.recovery_intent).upper()
        if effect_policy not in EFFECT_POLICIES or remote_policy not in REMOTE_DEPENDENCY_POLICIES or preemption not in PREEMPTION_REQUIREMENTS or recovery not in RECOVERY_INTENTS:
            raise ValueError("degraded-operation assessment carries unsupported envelope semantics")
        if self.effect_authority_granted or self.reusable_authorization_token or self.mode_activation_performed or self.capability_liveness_checked:
            raise ValueError("degraded-operation assessment cannot claim authority, activation, liveness, or reusable authorization")
        object.__setattr__(self, "mode", mode)
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "allowed_operations", _uniq(self.allowed_operations, name="assessment allowed operation"))
        object.__setattr__(self, "effect_policy", effect_policy)
        object.__setattr__(self, "remote_dependency_policy", remote_policy)
        object.__setattr__(self, "preemption_requirement", preemption)
        object.__setattr__(self, "recovery_intent", recovery)
        object.__setattr__(self, "matched_rule_id", _optional(self.matched_rule_id))
        object.__setattr__(self, "diagnostics", _uniq(self.diagnostics, name="assessment diagnostic"))
        derived = f"degraded-operation-assessment-{semantic_fingerprint(self.identity_payload())[:24]}"
        supplied = _optional(self.assessment_id)
        if supplied and supplied != derived:
            raise ValueError("degraded-operation assessment_id does not match canonical identity")
        object.__setattr__(self, "assessment_id", derived)

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "policy_id": self.policy_id,
            "policy_fingerprint": self.policy_fingerprint,
            "capability_id": self.capability_id,
            "capability_fingerprint": self.capability_fingerprint,
            "context_fingerprint": self.context_fingerprint,
            "mode": self.mode,
            "status": self.status,
            "allowed_operations": list(self.allowed_operations),
            "effect_policy": self.effect_policy,
            "remote_dependency_policy": self.remote_dependency_policy,
            "preemption_requirement": self.preemption_requirement,
            "recovery_intent": self.recovery_intent,
            "matched_rule_id": self.matched_rule_id,
            "diagnostics": list(self.diagnostics),
            "effect_authority_granted": False,
            "reusable_authorization_token": False,
            "mode_activation_performed": False,
            "capability_liveness_checked": False,
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"assessment_id": self.assessment_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"assessment_id": self.assessment_id, **self.identity_payload(), "fingerprint": self.fingerprint}



def _match_rule(rule: ModeSelectionRule, states: Mapping[str, DependencyState]) -> bool:
    return all(states[value.dependency_id].status in value.allowed_statuses for value in rule.requirements)


def evaluate_degraded_operation(
    policy: DegradedOperationPolicy,
    capability: EffectCapability,
    context: DegradedOperationContext,
) -> DegradedOperationAssessment:
    if not isinstance(policy, DegradedOperationPolicy):
        raise TypeError("evaluate_degraded_operation requires DegradedOperationPolicy")
    if not isinstance(capability, EffectCapability):
        raise TypeError("evaluate_degraded_operation requires EffectCapability")
    if not isinstance(context, DegradedOperationContext):
        raise TypeError("evaluate_degraded_operation requires DegradedOperationContext")

    if capability.capability_id != policy.base_capability_id or capability.fingerprint != policy.base_capability_fingerprint:
        raise ValueError("degraded-operation policy does not bind the exact supplied EffectCapability")
    for name in ("workspace_id", "scope_id", "subject_id"):
        if getattr(capability, name) != getattr(policy, name):
            raise ValueError(f"degraded-operation policy {name} does not match base capability")
        if getattr(context, name) != getattr(policy, name):
            raise ValueError(f"degraded-operation context {name} does not match policy")
    if context.problem_revision_id != policy.problem_revision_id or context.problem_revision_fingerprint != policy.problem_revision_fingerprint:
        raise ValueError("degraded-operation context problem revision does not match policy")
    if capability.problem_revision_id and capability.problem_revision_id != policy.problem_revision_id:
        raise ValueError("degraded-operation base capability problem revision does not match policy")

    base_operations = set(capability.allowed_operations)
    for envelope in policy.mode_envelopes:
        if not set(envelope.allowed_operations).issubset(base_operations):
            raise ValueError(f"degraded-operation {envelope.mode} envelope amplifies base EffectCapability operations")
        if envelope.mode == "FULL_OPERATION" and set(envelope.allowed_operations) != base_operations:
            raise ValueError("FULL_OPERATION envelope must preserve the exact base EffectCapability operation set")
    state_map = {value.dependency_id: value for value in context.dependency_states}
    if set(state_map) != set(policy.dependency_ids):
        raise ValueError("degraded-operation context must contain the exact policy dependency set")

    diagnostics: list[str] = []
    matched_rule_id = ""
    selected_mode = policy.fallback_mode
    status = "FAIL_CLOSED"

    unknown = tuple(sorted(value.dependency_id for value in context.dependency_states if value.status == "UNKNOWN"))
    if unknown:
        diagnostics.extend(f"UNKNOWN_DEPENDENCY:{dependency_id}" for dependency_id in unknown)
    else:
        matches = [rule for rule in policy.selection_rules if _match_rule(rule, state_map)]
        if len(matches) == 1:
            selected_mode = matches[0].mode
            matched_rule_id = matches[0].rule_id
            status = "SELECTED"
        elif not matches:
            diagnostics.append("NO_SELECTION_RULE_MATCHED")
        else:
            diagnostics.append("MULTIPLE_SELECTION_RULES_MATCHED")
            diagnostics.extend(f"MATCHED_RULE:{rule.rule_id}" for rule in matches)

    envelope = policy.envelope(selected_mode)
    allowed_operations = envelope.allowed_operations if envelope.effect_policy == "EXISTING_CAPABILITY_SUBSET_ONLY" else ()
    if status == "FAIL_CLOSED" and selected_mode != "SAFE_HOLD":
        raise AssertionError("degraded-operation fail-closed path must select SAFE_HOLD")

    return DegradedOperationAssessment(
        policy.policy_id,
        policy.fingerprint,
        capability.capability_id,
        capability.fingerprint,
        context.fingerprint,
        selected_mode,
        status,
        allowed_operations,
        envelope.effect_policy,
        envelope.remote_dependency_policy,
        envelope.preemption_requirement,
        envelope.recovery_intent,
        matched_rule_id=matched_rule_id,
        diagnostics=tuple(diagnostics),
    )


def degraded_operation_contract() -> dict[str, Any]:
    return {
        "contract_id": DEGRADED_OPERATION_CONTRACT_ID,
        "contract_version": DEGRADED_OPERATION_CONTRACT_VERSION,
        "assessment_contract_id": DEGRADED_OPERATION_ASSESSMENT_CONTRACT_ID,
        "assessment_contract_version": DEGRADED_OPERATION_ASSESSMENT_CONTRACT_VERSION,
        "stability": DEGRADED_OPERATION_STABILITY,
        "modes": list(DEGRADED_OPERATION_MODES),
        "dependency_statuses": list(DEPENDENCY_STATUSES),
        "authority_ceiling": "EXACT_EXISTING_EFFECT_CAPABILITY_ID_AND_FINGERPRINT_ONLY_NEVER_AMPLIFIED",
        "capability_liveness": "NOT_ESTABLISHED_BY_FOUNDATION_EXISTING_POINT_OF_USE_RECHECK_REMAINS_MANDATORY",
        "effect_authorization": "EXISTING_AASM_AUTHORIZE_EFFECT_REMAINS_REQUIRED",
        "effect_dispatch": "EXISTING_AASM_EXECUTE_EFFECT_REMAINS_REQUIRED",
        "physical_authority": "EXISTING_AUTHORITY_DOMAIN_LEASE_EPOCH_REVOCATION_REMAIN_AUTHORITATIVE",
        "preemption": "REQUIREMENT_ONLY_USES_EXISTING_AASM_AUTHORITY_PREEMPTION_PATH_NO_DIRECT_REVOCATION",
        "task_lease": "EXISTING_V54_TASKLEASE_UNCHANGED",
        "resource_governance": "EXISTING_V54_RESOURCE_RESERVATIONS_UNCHANGED",
        "unknown_and_reconciliation": "EXISTING_V54_EFFECT_UNKNOWN_AND_RECONCILIATION_UNCHANGED",
        "dependency_state": "EXPLICIT_POLICY_INPUT_WITH_EVIDENCE_REFERENCES_NOT_FACT_AUTHORITY",
        "full_operation": "EXACT_BASE_CAPABILITY_OPERATIONS_AND_ALL_DECLARED_DEPENDENCIES_AVAILABLE",
        "unknown_ambiguous_or_unmatched": "FAIL_CLOSED_TO_SAFE_HOLD_WITH_NO_NEW_EFFECTS",
        "safe_hold_meaning": "POLICY_LABEL_FOR_NO_NEW_EFFECTS_NOT_EMPIRICAL_PROOF_OF_PHYSICAL_SAFETY",
        "return_to_safe_state_meaning": "RECOVERY_INTENT_ONLY_REQUIRES_EXISTING_AUTHORITY_EFFECT_LIFECYCLE_AND_POSTCONDITION_VERIFICATION",
        "emergency_meaning": "EMERGENCY_RESPONSE_INTENT_ONLY_NEVER_CREATES_OR_EXPANDS_AUTHORITY",
        "local_only": "REMOTE_DEPENDENCIES_FORBIDDEN_BY_MODE_ENVELOPE_NO_LOCAL_AUTHORITY_CREATION",
        "mode_selection_grants_effect_authority": False,
        "mode_existence_grants_effect_authority": False,
        "assessment_is_authorization": False,
        "assessment_is_reusable_authorization_token": False,
        "assessment_activates_mode": False,
        "assessment_proves_safety": False,
        "hidden_current_mode": "NONE",
        "parallel_mode_store": "NONE",
        "parallel_authority_evaluator": "NONE",
        "parallel_effect_lifecycle": "NONE",
        "parallel_dispatcher": "NONE",
        "runtime_admission": "PRE_ADMISSION_ONLY",
        "public_admission": "PRE_ADMISSION_ONLY",
    }


__all__ = [
    "DEGRADED_OPERATION_CONTRACT_ID",
    "DEGRADED_OPERATION_CONTRACT_VERSION",
    "DEGRADED_OPERATION_ASSESSMENT_CONTRACT_ID",
    "DEGRADED_OPERATION_ASSESSMENT_CONTRACT_VERSION",
    "DEGRADED_OPERATION_STABILITY",
    "DEGRADED_OPERATION_MODES",
    "DEPENDENCY_STATUSES",
    "EFFECT_POLICIES",
    "REMOTE_DEPENDENCY_POLICIES",
    "PREEMPTION_REQUIREMENTS",
    "RECOVERY_INTENTS",
    "DEGRADED_ASSESSMENT_STATUSES",
    "DependencyState",
    "DependencyRequirement",
    "DegradedModeEnvelope",
    "ModeSelectionRule",
    "DegradedOperationPolicy",
    "DegradedOperationContext",
    "DegradedOperationAssessment",
    "evaluate_degraded_operation",
    "degraded_operation_contract",
]
