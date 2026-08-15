from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Protocol

from .model import new_id, now
from .semantic_result import semantic_fingerprint


EFFECT_INTENT_CONTRACT_ID = "aasm.effect.intent.v1"
EFFECT_DISPATCH_REQUEST_CONTRACT_ID = "aasm.effect.dispatch-request.v1"
EFFECT_OWNERSHIP_CONTRACT_ID = "aasm.effect.ownership.v1"
EFFECT_RECONCILIATION_CONTRACT_ID = "aasm.effect.reconciliation.v1"
EFFECT_GOVERNANCE_CONTRACT_VERSION = "0.1.0"
EFFECT_GOVERNANCE_STABILITY = "FOUNDATION_EXPERIMENTAL"


class EffectStatus(str, Enum):
    PROPOSED = "PROPOSED"
    AUTHORIZED = "AUTHORIZED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"
    CANCELLED = "CANCELLED"


class EffectOutcome(str, Enum):
    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"


@dataclass
class RetryPolicy:
    max_attempts: int = 1
    retry_on_failure: bool = False
    retry_on_unknown: bool = False


@dataclass
class EffectSpec:
    effect_type: str
    payload: dict[str, Any] = field(default_factory=dict)
    idempotency_key: str = ""
    preconditions: list[dict[str, Any]] = field(default_factory=list)
    postconditions: list[dict[str, Any]] = field(default_factory=list)
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    reversible: bool = False
    compensation: dict[str, Any] | None = None
    effect_id: str = field(default_factory=lambda: new_id("effect"))

    def __post_init__(self):
        if not self.idempotency_key:
            self.idempotency_key = self.effect_id


@dataclass(frozen=True)
class EffectIntent:
    effect_id: str
    effect_type: str
    idempotency_key: str
    workspace_id: str
    scope_id: str
    resource_reservation_ids: tuple[str, ...] = ()
    proposer_principal_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    contract_id: str = EFFECT_INTENT_CONTRACT_ID
    contract_version: str = EFFECT_GOVERNANCE_CONTRACT_VERSION

    def __post_init__(self) -> None:
        for name in ("effect_id", "effect_type", "idempotency_key", "workspace_id", "scope_id"):
            if not str(getattr(self, name)).strip():
                raise ValueError(f"effect intent {name} is required")
        if self.contract_id != EFFECT_INTENT_CONTRACT_ID or self.contract_version != EFFECT_GOVERNANCE_CONTRACT_VERSION:
            raise ValueError("unsupported effect intent contract")
        object.__setattr__(self, "resource_reservation_ids", tuple(sorted(set(map(str, self.resource_reservation_ids)))))
        object.__setattr__(self, "metadata", dict(self.metadata))

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "effect_id": self.effect_id,
            "effect_type": self.effect_type,
            "idempotency_key": self.idempotency_key,
            "workspace_id": self.workspace_id,
            "scope_id": self.scope_id,
            "resource_reservation_ids": list(self.resource_reservation_ids),
            "proposer_principal_id": self.proposer_principal_id,
            "metadata": self.metadata,
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(self.identity_payload())

    @property
    def intent_id(self) -> str:
        return f"effect-intent-{self.fingerprint[:24]}"

    def to_dict(self) -> dict[str, Any]:
        return {**self.identity_payload(), "intent_id": self.intent_id, "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "EffectIntent":
        payload = dict(data)
        payload.pop("intent_id", None)
        payload.pop("fingerprint", None)
        payload["resource_reservation_ids"] = tuple(payload.get("resource_reservation_ids") or ())
        return cls(**payload)

    @classmethod
    def from_spec(
        cls,
        spec: EffectSpec,
        *,
        workspace_id: str,
        scope_id: str,
        resource_reservation_ids=(),
        proposer_principal_id: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> "EffectIntent":
        return cls(
            spec.effect_id,
            spec.effect_type,
            spec.idempotency_key,
            workspace_id,
            scope_id,
            tuple(resource_reservation_ids),
            proposer_principal_id,
            dict(metadata or {}),
        )


@dataclass(frozen=True)
class EffectDispatchRequest:
    effect_id: str
    intent_id: str
    owner_worker_id: str
    task_lease_id: str
    workspace_id: str
    scope_id: str
    resource_reservation_ids: tuple[str, ...] = ()
    owner_principal_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    contract_id: str = EFFECT_DISPATCH_REQUEST_CONTRACT_ID
    contract_version: str = EFFECT_GOVERNANCE_CONTRACT_VERSION

    def __post_init__(self) -> None:
        for name in ("effect_id", "intent_id", "owner_worker_id", "task_lease_id", "workspace_id", "scope_id"):
            if not str(getattr(self, name)).strip():
                raise ValueError(f"effect dispatch request {name} is required")
        if self.contract_id != EFFECT_DISPATCH_REQUEST_CONTRACT_ID or self.contract_version != EFFECT_GOVERNANCE_CONTRACT_VERSION:
            raise ValueError("unsupported effect dispatch request contract")
        object.__setattr__(self, "resource_reservation_ids", tuple(sorted(set(map(str, self.resource_reservation_ids)))))
        object.__setattr__(self, "metadata", dict(self.metadata))

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "effect_id": self.effect_id,
            "intent_id": self.intent_id,
            "owner_worker_id": self.owner_worker_id,
            "task_lease_id": self.task_lease_id,
            "workspace_id": self.workspace_id,
            "scope_id": self.scope_id,
            "resource_reservation_ids": list(self.resource_reservation_ids),
            "owner_principal_id": self.owner_principal_id,
            "metadata": self.metadata,
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(self.identity_payload())

    @property
    def dispatch_request_id(self) -> str:
        return f"effect-dispatch-{self.fingerprint[:24]}"

    def to_dict(self) -> dict[str, Any]:
        return {
            **self.identity_payload(),
            "dispatch_request_id": self.dispatch_request_id,
            "fingerprint": self.fingerprint,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "EffectDispatchRequest":
        payload = dict(data)
        payload.pop("dispatch_request_id", None)
        payload.pop("fingerprint", None)
        payload["resource_reservation_ids"] = tuple(payload.get("resource_reservation_ids") or ())
        return cls(**payload)

    @classmethod
    def from_intent(
        cls,
        intent: EffectIntent,
        *,
        owner_worker_id: str,
        task_lease_id: str,
        owner_principal_id: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> "EffectDispatchRequest":
        return cls(
            effect_id=intent.effect_id,
            intent_id=intent.intent_id,
            owner_worker_id=owner_worker_id,
            task_lease_id=task_lease_id,
            workspace_id=intent.workspace_id,
            scope_id=intent.scope_id,
            resource_reservation_ids=intent.resource_reservation_ids,
            owner_principal_id=owner_principal_id,
            metadata=dict(metadata or {}),
        )


@dataclass(frozen=True)
class EffectOwnership:
    effect_id: str
    intent_id: str
    execution_id: str
    owner_worker_id: str
    workspace_id: str
    scope_id: str
    authority_decision_evidence_id: str
    resource_reservation_ids: tuple[str, ...] = ()
    task_lease_id: str | None = None
    owner_principal_id: str | None = None
    dispatch_request_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    contract_id: str = EFFECT_OWNERSHIP_CONTRACT_ID
    contract_version: str = EFFECT_GOVERNANCE_CONTRACT_VERSION

    def __post_init__(self) -> None:
        for name in (
            "effect_id",
            "intent_id",
            "execution_id",
            "owner_worker_id",
            "workspace_id",
            "scope_id",
            "authority_decision_evidence_id",
        ):
            if not str(getattr(self, name)).strip():
                raise ValueError(f"effect ownership {name} is required")
        if self.contract_id != EFFECT_OWNERSHIP_CONTRACT_ID or self.contract_version != EFFECT_GOVERNANCE_CONTRACT_VERSION:
            raise ValueError("unsupported effect ownership contract")
        object.__setattr__(self, "resource_reservation_ids", tuple(sorted(set(map(str, self.resource_reservation_ids)))))
        object.__setattr__(self, "metadata", dict(self.metadata))

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "effect_id": self.effect_id,
            "intent_id": self.intent_id,
            "execution_id": self.execution_id,
            "owner_worker_id": self.owner_worker_id,
            "workspace_id": self.workspace_id,
            "scope_id": self.scope_id,
            "authority_decision_evidence_id": self.authority_decision_evidence_id,
            "resource_reservation_ids": list(self.resource_reservation_ids),
            "task_lease_id": self.task_lease_id,
            "owner_principal_id": self.owner_principal_id,
            "dispatch_request_id": self.dispatch_request_id,
            "metadata": self.metadata,
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(self.identity_payload())

    @property
    def ownership_id(self) -> str:
        return f"effect-ownership-{self.fingerprint[:24]}"

    def to_dict(self) -> dict[str, Any]:
        return {**self.identity_payload(), "ownership_id": self.ownership_id, "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "EffectOwnership":
        payload = dict(data)
        payload.pop("ownership_id", None)
        payload.pop("fingerprint", None)
        payload["resource_reservation_ids"] = tuple(payload.get("resource_reservation_ids") or ())
        return cls(**payload)


@dataclass(frozen=True)
class EffectOwnershipRequest:
    effect_id: str
    intent_id: str
    dispatch_request_id: str
    authority_decision_evidence_id: str
    owner_worker_id: str
    task_lease_id: str
    workspace_id: str
    scope_id: str
    resource_reservation_ids: tuple[str, ...] = ()
    owner_principal_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in (
            "effect_id",
            "intent_id",
            "dispatch_request_id",
            "authority_decision_evidence_id",
            "owner_worker_id",
            "task_lease_id",
            "workspace_id",
            "scope_id",
        ):
            if not str(getattr(self, name)).strip():
                raise ValueError(f"effect ownership request {name} is required")
        object.__setattr__(self, "resource_reservation_ids", tuple(sorted(set(map(str, self.resource_reservation_ids)))))
        object.__setattr__(self, "metadata", dict(self.metadata))

    @classmethod
    def from_dispatch(
        cls,
        dispatch: EffectDispatchRequest,
        *,
        authority_decision_evidence_id: str,
        metadata: Mapping[str, Any] | None = None,
    ) -> "EffectOwnershipRequest":
        return cls(
            effect_id=dispatch.effect_id,
            intent_id=dispatch.intent_id,
            dispatch_request_id=dispatch.dispatch_request_id,
            authority_decision_evidence_id=authority_decision_evidence_id,
            owner_worker_id=dispatch.owner_worker_id,
            task_lease_id=dispatch.task_lease_id,
            workspace_id=dispatch.workspace_id,
            scope_id=dispatch.scope_id,
            resource_reservation_ids=dispatch.resource_reservation_ids,
            owner_principal_id=dispatch.owner_principal_id,
            metadata={**dispatch.metadata, **dict(metadata or {})},
        )

    def bind(self, execution_id: str) -> EffectOwnership:
        return EffectOwnership(
            effect_id=self.effect_id,
            intent_id=self.intent_id,
            execution_id=execution_id,
            owner_worker_id=self.owner_worker_id,
            workspace_id=self.workspace_id,
            scope_id=self.scope_id,
            authority_decision_evidence_id=self.authority_decision_evidence_id,
            resource_reservation_ids=self.resource_reservation_ids,
            task_lease_id=self.task_lease_id,
            owner_principal_id=self.owner_principal_id,
            dispatch_request_id=self.dispatch_request_id,
            metadata=self.metadata,
        )


@dataclass(frozen=True)
class EffectReconciliation:
    effect_id: str
    outcome: str
    evidence_ids: tuple[str, ...] = ()
    ownership_id: str | None = None
    reconciled_by_principal_id: str | None = None
    authority_decision_evidence_id: str | None = None
    result: dict[str, Any] | None = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    contract_id: str = EFFECT_RECONCILIATION_CONTRACT_ID
    contract_version: str = EFFECT_GOVERNANCE_CONTRACT_VERSION

    def __post_init__(self) -> None:
        if not self.effect_id.strip():
            raise ValueError("effect reconciliation effect_id is required")
        if self.outcome not in {row.value for row in EffectOutcome}:
            raise ValueError(f"invalid effect reconciliation outcome: {self.outcome}")
        if self.contract_id != EFFECT_RECONCILIATION_CONTRACT_ID or self.contract_version != EFFECT_GOVERNANCE_CONTRACT_VERSION:
            raise ValueError("unsupported effect reconciliation contract")
        object.__setattr__(self, "evidence_ids", tuple(sorted(set(map(str, self.evidence_ids)))))
        object.__setattr__(self, "metadata", dict(self.metadata))

    @property
    def retry_blocked(self) -> bool:
        return self.outcome == EffectOutcome.UNKNOWN.value

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "effect_id": self.effect_id,
            "outcome": self.outcome,
            "evidence_ids": list(self.evidence_ids),
            "ownership_id": self.ownership_id,
            "reconciled_by_principal_id": self.reconciled_by_principal_id,
            "authority_decision_evidence_id": self.authority_decision_evidence_id,
            "result": self.result,
            "error": self.error,
            "metadata": self.metadata,
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(self.identity_payload())

    @property
    def reconciliation_id(self) -> str:
        return f"effect-reconciliation-{self.fingerprint[:24]}"

    def to_dict(self) -> dict[str, Any]:
        return {
            **self.identity_payload(),
            "reconciliation_id": self.reconciliation_id,
            "fingerprint": self.fingerprint,
            "retry_blocked": self.retry_blocked,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "EffectReconciliation":
        payload = dict(data)
        payload.pop("reconciliation_id", None)
        payload.pop("fingerprint", None)
        payload.pop("retry_blocked", None)
        payload["evidence_ids"] = tuple(payload.get("evidence_ids") or ())
        return cls(**payload)


def effect_governance_contract() -> dict[str, Any]:
    return {
        "intent_contract_id": EFFECT_INTENT_CONTRACT_ID,
        "dispatch_request_contract_id": EFFECT_DISPATCH_REQUEST_CONTRACT_ID,
        "ownership_contract_id": EFFECT_OWNERSHIP_CONTRACT_ID,
        "reconciliation_contract_id": EFFECT_RECONCILIATION_CONTRACT_ID,
        "contract_version": EFFECT_GOVERNANCE_CONTRACT_VERSION,
        "stability": EFFECT_GOVERNANCE_STABILITY,
        "existing_effect_execution": "REUSED_NEVER_REPLACED",
        "authorization_before_ownership": True,
        "resource_reservations": "BOUND_TO_INTENT_DISPATCH_AND_OWNERSHIP_WHEN_DECLARED",
        "task_lease": "EXISTING_AASM_TASKLEASE_ONLY",
        "dispatch": "DURABLE_REQUEST_THEN_ATOMIC_EXECUTION_OWNERSHIP",
        "unknown_outcome": "REQUIRES_EXPLICIT_RECONCILIATION_BEFORE_NEW_OWNERSHIP",
        "history": "APPEND_ONLY_DISPATCH_OWNERSHIP_RECONCILIATION",
        "truth_authority": "EXISTING_AASM_POLICY_ONLY",
    }


def _append_unique(history: list[dict[str, Any]], document: dict[str, Any], id_key: str) -> list[dict[str, Any]]:
    identity = document[id_key]
    if not any(row.get(id_key) == identity for row in history):
        history.append(dict(document))
    return history


@dataclass
class EffectRecord:
    machine_id: str
    spec: EffectSpec
    status: str = EffectStatus.PROPOSED.value
    attempts: int = 0
    authorization_id: str | None = None
    authority: str | None = None
    execution_id: str | None = None
    result: dict[str, Any] | None = None
    error: str | None = None
    evidence: list[str] = field(default_factory=list)
    intent: dict[str, Any] | None = None
    dispatch_request: dict[str, Any] | None = None
    ownership: dict[str, Any] | None = None
    reconciliation: dict[str, Any] | None = None
    dispatch_history: list[dict[str, Any]] = field(default_factory=list)
    ownership_history: list[dict[str, Any]] = field(default_factory=list)
    reconciliation_history: list[dict[str, Any]] = field(default_factory=list)
    created_at: float = field(default_factory=now)
    updated_at: float = field(default_factory=now)

    def __post_init__(self) -> None:
        parsed_intent = None
        if self.intent is not None:
            parsed_intent = EffectIntent.from_dict(self.intent)
            if parsed_intent.effect_id != self.spec.effect_id:
                raise ValueError("effect intent does not match EffectSpec effect_id")
            if parsed_intent.effect_type != self.spec.effect_type or parsed_intent.idempotency_key != self.spec.idempotency_key:
                raise ValueError("effect intent does not match EffectSpec identity")
            self.intent = parsed_intent.to_dict()

        normalized_dispatch_history = []
        for raw in self.dispatch_history:
            item = EffectDispatchRequest.from_dict(raw)
            if item.effect_id != self.spec.effect_id:
                raise ValueError("dispatch history contains a different effect")
            normalized_dispatch_history.append(item.to_dict())
        self.dispatch_history = normalized_dispatch_history
        if self.dispatch_request is not None:
            dispatch = EffectDispatchRequest.from_dict(self.dispatch_request)
            if dispatch.effect_id != self.spec.effect_id:
                raise ValueError("effect dispatch request does not match EffectSpec effect_id")
            if parsed_intent is None or dispatch.intent_id != parsed_intent.intent_id:
                raise ValueError("effect dispatch request requires the bound EffectIntent")
            if dispatch.workspace_id != parsed_intent.workspace_id or dispatch.scope_id != parsed_intent.scope_id:
                raise ValueError("effect dispatch request crosses EffectIntent context")
            if dispatch.resource_reservation_ids != parsed_intent.resource_reservation_ids:
                raise ValueError("effect dispatch reservations do not match EffectIntent")
            self.dispatch_request = dispatch.to_dict()
            _append_unique(self.dispatch_history, self.dispatch_request, "dispatch_request_id")

        normalized_ownership_history = []
        for raw in self.ownership_history:
            item = EffectOwnership.from_dict(raw)
            if item.effect_id != self.spec.effect_id:
                raise ValueError("ownership history contains a different effect")
            normalized_ownership_history.append(item.to_dict())
        self.ownership_history = normalized_ownership_history
        if self.ownership is not None:
            ownership = EffectOwnership.from_dict(self.ownership)
            if ownership.effect_id != self.spec.effect_id:
                raise ValueError("effect ownership does not match EffectSpec effect_id")
            if parsed_intent is not None and ownership.intent_id != parsed_intent.intent_id:
                raise ValueError("effect ownership does not match bound EffectIntent")
            if self.dispatch_request is not None and ownership.dispatch_request_id not in {None, self.dispatch_request["dispatch_request_id"]}:
                raise ValueError("effect ownership does not match bound dispatch request")
            self.ownership = ownership.to_dict()
            _append_unique(self.ownership_history, self.ownership, "ownership_id")

        normalized_reconciliation_history = []
        for raw in self.reconciliation_history:
            item = EffectReconciliation.from_dict(raw)
            if item.effect_id != self.spec.effect_id:
                raise ValueError("reconciliation history contains a different effect")
            normalized_reconciliation_history.append(item.to_dict())
        self.reconciliation_history = normalized_reconciliation_history
        if self.reconciliation is not None:
            reconciliation = EffectReconciliation.from_dict(self.reconciliation)
            if reconciliation.effect_id != self.spec.effect_id:
                raise ValueError("effect reconciliation does not match EffectSpec effect_id")
            if self.ownership is not None and reconciliation.ownership_id not in {None, self.ownership["ownership_id"]}:
                raise ValueError("effect reconciliation does not match bound EffectOwnership")
            self.reconciliation = reconciliation.to_dict()
            _append_unique(self.reconciliation_history, self.reconciliation, "reconciliation_id")


def bind_effect_ownership(record: EffectRecord, request: EffectOwnershipRequest | Mapping[str, Any]) -> EffectOwnership:
    item = request if isinstance(request, EffectOwnershipRequest) else EffectOwnershipRequest(**dict(request))
    if not record.execution_id:
        raise ValueError("effect execution ownership requires an execution_id")
    if record.intent is None or record.dispatch_request is None:
        raise ValueError("effect execution ownership requires durable intent and dispatch request")
    intent = EffectIntent.from_dict(record.intent)
    dispatch = EffectDispatchRequest.from_dict(record.dispatch_request)
    if item.effect_id != record.spec.effect_id or item.effect_id != intent.effect_id:
        raise ValueError("effect ownership request effect_id mismatch")
    if item.intent_id != intent.intent_id or item.dispatch_request_id != dispatch.dispatch_request_id:
        raise ValueError("effect ownership request does not match durable intent/dispatch")
    if item.workspace_id != intent.workspace_id or item.scope_id != intent.scope_id:
        raise ValueError("effect ownership request crosses durable effect context")
    if item.owner_worker_id != dispatch.owner_worker_id or item.task_lease_id != dispatch.task_lease_id:
        raise ValueError("effect ownership request changes dispatch owner")
    if item.resource_reservation_ids != intent.resource_reservation_ids or item.resource_reservation_ids != dispatch.resource_reservation_ids:
        raise ValueError("effect ownership request changes governed reservations")
    ownership = item.bind(record.execution_id)
    record.ownership = ownership.to_dict()
    _append_unique(record.ownership_history, record.ownership, "ownership_id")
    record.reconciliation = None
    return ownership


def bind_effect_reconciliation(record: EffectRecord, reconciliation: EffectReconciliation | Mapping[str, Any]) -> EffectReconciliation:
    item = reconciliation if isinstance(reconciliation, EffectReconciliation) else EffectReconciliation.from_dict(reconciliation)
    if item.effect_id != record.spec.effect_id:
        raise ValueError("effect reconciliation effect_id mismatch")
    if record.ownership is not None:
        ownership = EffectOwnership.from_dict(record.ownership)
        if item.ownership_id not in {None, ownership.ownership_id}:
            raise ValueError("effect reconciliation ownership mismatch")
    record.reconciliation = item.to_dict()
    _append_unique(record.reconciliation_history, record.reconciliation, "reconciliation_id")
    return item


class EffectExecutor(Protocol):
    """Executor contract.

    The same idempotency_key is supplied on every retry. Executors that can
    provide strong exactly-once behavior should deduplicate by that key.
    """

    def __call__(self, spec: EffectSpec, idempotency_key: str) -> dict[str, Any]: ...


class EffectExecutionError(RuntimeError):
    pass


class EffectUnknownOutcome(RuntimeError):
    """Raised when a prior RUNNING attempt may have reached the external system.

    Retrying automatically could duplicate the side effect. Reconcile first or
    explicitly configure a retry-safe executor/policy.
    """
