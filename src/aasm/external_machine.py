from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from .semantic_result import semantic_fingerprint


MACHINE_BINDING_CONTRACT_ID = "aasm.machine.binding.v1"
MACHINE_BINDING_CONTRACT_VERSION = "0.1.0"
MACHINE_STATE_OBSERVATION_CONTRACT_ID = "aasm.machine.state-observation.v1"
MACHINE_STATE_OBSERVATION_CONTRACT_VERSION = "0.1.0"
EXTERNAL_MACHINE_STABILITY = "FOUNDATION_EXPERIMENTAL"


def _require(value: str, name: str) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError(f"{name} is required")
    return text


def _uniq(values: Sequence[str]) -> tuple[str, ...]:
    return tuple(sorted({str(value).strip() for value in values if str(value).strip()}))


def _jsonable(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        return _jsonable(value.to_dict())
    if isinstance(value, Mapping):
        return {
            str(key): _jsonable(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (tuple, list, set)):
        return [_jsonable(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    raise TypeError(f"external-machine value is not JSON serializable: {type(value)!r}")


@dataclass(frozen=True)
class MachineBinding:
    workspace_id: str
    scope_id: str
    external_machine_id: str
    subject_id: str
    state_namespaces: tuple[str, ...]
    observer_capability_id: str
    executor_capability_id: str
    external_revision_id: str
    problem_revision_id: str = ""
    fact_authority_ids: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)
    binding_id: str = ""
    contract_id: str = MACHINE_BINDING_CONTRACT_ID
    contract_version: str = MACHINE_BINDING_CONTRACT_VERSION

    def __post_init__(self) -> None:
        for name in (
            "workspace_id",
            "scope_id",
            "external_machine_id",
            "subject_id",
            "observer_capability_id",
            "executor_capability_id",
            "external_revision_id",
        ):
            object.__setattr__(self, name, _require(getattr(self, name), name))
        if self.contract_id != MACHINE_BINDING_CONTRACT_ID or self.contract_version != MACHINE_BINDING_CONTRACT_VERSION:
            raise ValueError("unsupported machine binding contract")
        namespaces = _uniq(self.state_namespaces)
        if not namespaces:
            raise ValueError("machine binding requires at least one state namespace")
        object.__setattr__(self, "state_namespaces", namespaces)
        object.__setattr__(self, "fact_authority_ids", _uniq(self.fact_authority_ids))
        object.__setattr__(self, "problem_revision_id", str(self.problem_revision_id).strip())
        object.__setattr__(self, "metadata", _jsonable(dict(self.metadata)))
        if not self.binding_id:
            object.__setattr__(
                self,
                "binding_id",
                f"machine-binding-{semantic_fingerprint(self.identity_payload())[:24]}",
            )
        else:
            object.__setattr__(self, "binding_id", _require(self.binding_id, "binding_id"))

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "workspace_id": self.workspace_id,
            "scope_id": self.scope_id,
            "external_machine_id": self.external_machine_id,
            "subject_id": self.subject_id,
            "state_namespaces": list(self.state_namespaces),
            "observer_capability_id": self.observer_capability_id,
            "executor_capability_id": self.executor_capability_id,
            "external_revision_id": self.external_revision_id,
            "problem_revision_id": self.problem_revision_id,
            "fact_authority_ids": list(self.fact_authority_ids),
            "metadata": _jsonable(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"binding_id": self.binding_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"binding_id": self.binding_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "MachineBinding":
        payload = deepcopy(dict(value))
        payload.pop("fingerprint", None)
        payload["state_namespaces"] = tuple(payload.get("state_namespaces") or ())
        payload["fact_authority_ids"] = tuple(payload.get("fact_authority_ids") or ())
        return cls(**payload)


@dataclass(frozen=True)
class MachineStateObservation:
    binding_id: str
    state_claim_id: str
    observer_principal_id: str
    observer_capability_id: str
    external_revision_id: str
    receipt_id: str = ""
    correlation_id: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)
    observation_id: str = ""
    contract_id: str = MACHINE_STATE_OBSERVATION_CONTRACT_ID
    contract_version: str = MACHINE_STATE_OBSERVATION_CONTRACT_VERSION

    def __post_init__(self) -> None:
        for name in (
            "binding_id",
            "state_claim_id",
            "observer_principal_id",
            "observer_capability_id",
            "external_revision_id",
        ):
            object.__setattr__(self, name, _require(getattr(self, name), name))
        if self.contract_id != MACHINE_STATE_OBSERVATION_CONTRACT_ID or self.contract_version != MACHINE_STATE_OBSERVATION_CONTRACT_VERSION:
            raise ValueError("unsupported machine state observation contract")
        object.__setattr__(self, "receipt_id", str(self.receipt_id).strip())
        object.__setattr__(self, "correlation_id", str(self.correlation_id).strip())
        object.__setattr__(self, "metadata", _jsonable(dict(self.metadata)))
        if not self.observation_id:
            object.__setattr__(
                self,
                "observation_id",
                f"machine-observation-{semantic_fingerprint(self.identity_payload())[:24]}",
            )
        else:
            object.__setattr__(self, "observation_id", _require(self.observation_id, "observation_id"))

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "binding_id": self.binding_id,
            "state_claim_id": self.state_claim_id,
            "observer_principal_id": self.observer_principal_id,
            "observer_capability_id": self.observer_capability_id,
            "external_revision_id": self.external_revision_id,
            "receipt_id": self.receipt_id,
            "correlation_id": self.correlation_id,
            "metadata": _jsonable(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"observation_id": self.observation_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"observation_id": self.observation_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "MachineStateObservation":
        payload = deepcopy(dict(value))
        payload.pop("fingerprint", None)
        return cls(**payload)


def external_machine_contract() -> dict[str, Any]:
    return {
        "binding_contract_id": MACHINE_BINDING_CONTRACT_ID,
        "binding_contract_version": MACHINE_BINDING_CONTRACT_VERSION,
        "state_observation_contract_id": MACHINE_STATE_OBSERVATION_CONTRACT_ID,
        "state_observation_contract_version": MACHINE_STATE_OBSERVATION_CONTRACT_VERSION,
        "stability": EXTERNAL_MACHINE_STABILITY,
        "binding_role": "REFERENCE_AND_CORRELATION_ONLY_NOT_EXTERNAL_STATE_COPY",
        "state_truth_source": "PR1_STATE_CLAIM_EVIDENCE_ONLY",
        "observation_requirement": "DURABLE_OBSERVED_STATE_CLAIM_EXACT_CONTEXT_AND_REVISION",
        "observer_capability_requirement": "ADMITTED_OBSERVER_CAPABILITY_REFERENCE",
        "executor_capability_requirement": "ADMITTED_OPERATOR_CAPABILITY_REFERENCE",
        "binding_grants_fact_authority": False,
        "binding_grants_effect_authority": False,
        "capability_reference_grants_authority": False,
        "observation_grants_fact_authority": False,
        "external_state_table": "NONE",
        "executor_invocation": "NONE_BY_THIS_FOUNDATION",
        "machine_state_mutation": "NONE_BY_THIS_FOUNDATION",
        "temporal_freshness_claim": "NOT_YET_CLAIMED_PR4",
        "postcondition_achievement_claim": "NOT_YET_CLAIMED_PR2C",
    }


__all__ = [
    "MACHINE_BINDING_CONTRACT_ID",
    "MACHINE_BINDING_CONTRACT_VERSION",
    "MACHINE_STATE_OBSERVATION_CONTRACT_ID",
    "MACHINE_STATE_OBSERVATION_CONTRACT_VERSION",
    "EXTERNAL_MACHINE_STABILITY",
    "MachineBinding",
    "MachineStateObservation",
    "external_machine_contract",
]
