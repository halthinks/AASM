from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from .semantic_result import semantic_fingerprint


MACHINE_TRANSITION_CONTRACT_ID = "aasm.machine.transition.v1"
MACHINE_TRANSITION_CONTRACT_VERSION = "0.1.0"
MACHINE_TRANSITION_STABILITY = "FOUNDATION_EXPERIMENTAL"


def _require(value: str, name: str) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError(f"{name} is required")
    return text


def _uniq(values: Sequence[str], name: str) -> tuple[str, ...]:
    result = tuple(sorted({str(value).strip() for value in values if str(value).strip()}))
    if not result:
        raise ValueError(f"{name} requires at least one value")
    return result


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
    raise TypeError(f"machine-transition value is not JSON serializable: {type(value)!r}")


@dataclass(frozen=True)
class MachineTransitionIntent:
    workspace_id: str
    scope_id: str
    binding_id: str
    operation: str
    expected_state_claim_ids: tuple[str, ...]
    target_state_claim_ids: tuple[str, ...]
    external_revision_id: str
    effect_id: str
    effect_intent_id: str
    effect_intent_fingerprint: str
    proposer_principal_id: str
    resource_reservation_ids: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)
    transition_id: str = ""
    contract_id: str = MACHINE_TRANSITION_CONTRACT_ID
    contract_version: str = MACHINE_TRANSITION_CONTRACT_VERSION

    def __post_init__(self) -> None:
        for name in (
            "workspace_id",
            "scope_id",
            "binding_id",
            "operation",
            "external_revision_id",
            "effect_id",
            "effect_intent_id",
            "effect_intent_fingerprint",
            "proposer_principal_id",
        ):
            object.__setattr__(self, name, _require(getattr(self, name), name))
        if self.contract_id != MACHINE_TRANSITION_CONTRACT_ID or self.contract_version != MACHINE_TRANSITION_CONTRACT_VERSION:
            raise ValueError("unsupported machine transition contract")
        object.__setattr__(
            self,
            "expected_state_claim_ids",
            _uniq(self.expected_state_claim_ids, "expected_state_claim_ids"),
        )
        object.__setattr__(
            self,
            "target_state_claim_ids",
            _uniq(self.target_state_claim_ids, "target_state_claim_ids"),
        )
        object.__setattr__(
            self,
            "resource_reservation_ids",
            tuple(sorted({str(value).strip() for value in self.resource_reservation_ids if str(value).strip()})),
        )
        object.__setattr__(self, "metadata", _jsonable(dict(self.metadata)))
        if not self.transition_id:
            object.__setattr__(
                self,
                "transition_id",
                f"machine-transition-{semantic_fingerprint(self.identity_payload())[:24]}",
            )
        else:
            object.__setattr__(self, "transition_id", _require(self.transition_id, "transition_id"))

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "workspace_id": self.workspace_id,
            "scope_id": self.scope_id,
            "binding_id": self.binding_id,
            "operation": self.operation,
            "expected_state_claim_ids": list(self.expected_state_claim_ids),
            "target_state_claim_ids": list(self.target_state_claim_ids),
            "external_revision_id": self.external_revision_id,
            "effect_id": self.effect_id,
            "effect_intent_id": self.effect_intent_id,
            "effect_intent_fingerprint": self.effect_intent_fingerprint,
            "proposer_principal_id": self.proposer_principal_id,
            "resource_reservation_ids": list(self.resource_reservation_ids),
            "metadata": _jsonable(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"transition_id": self.transition_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {
            "transition_id": self.transition_id,
            **self.identity_payload(),
            "fingerprint": self.fingerprint,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "MachineTransitionIntent":
        payload = deepcopy(dict(value))
        payload.pop("fingerprint", None)
        payload["expected_state_claim_ids"] = tuple(payload.get("expected_state_claim_ids") or ())
        payload["target_state_claim_ids"] = tuple(payload.get("target_state_claim_ids") or ())
        payload["resource_reservation_ids"] = tuple(payload.get("resource_reservation_ids") or ())
        return cls(**payload)


def machine_transition_contract() -> dict[str, Any]:
    return {
        "contract_id": MACHINE_TRANSITION_CONTRACT_ID,
        "contract_version": MACHINE_TRANSITION_CONTRACT_VERSION,
        "stability": MACHINE_TRANSITION_STABILITY,
        "binding_requirement": "EXISTING_DURABLE_MACHINE_BINDING_REQUIRED",
        "expected_prestate": "EXACT_DURABLE_AUTHORITATIVE_STATE_CLAIMS_REQUIRED",
        "target_state": "EXACT_DURABLE_DESIRED_STATE_CLAIMS_REQUIRED",
        "external_revision": "EXACT_MACHINE_BINDING_REVISION_REQUIRED",
        "effect_proposal": "EXISTING_AASM_PROPOSE_EFFECT_AND_EFFECT_INTENT_ONLY",
        "effect_authorization": "EXISTING_AASM_AUTHORIZE_EFFECT_ONLY_NOT_PERFORMED_BY_THIS_CONTRACT",
        "effect_dispatch": "EXISTING_AASM_EXECUTE_EFFECT_ONLY_NOT_PERFORMED_BY_THIS_CONTRACT",
        "effect_ownership": "EXISTING_AASM_EFFECT_OWNERSHIP_ONLY_NOT_CREATED_BY_THIS_CONTRACT",
        "effect_reconciliation": "EXISTING_AASM_EFFECT_RECONCILIATION_ONLY",
        "transition_lifecycle": "DERIVED_FROM_EXISTING_EFFECT_RECORD_NO_PARALLEL_STATUS_MACHINE",
        "command_success_is_achievement": False,
        "postcondition_verification": "NOT_IMPLEMENTED_PR2B_RESERVED_FOR_PR2C",
        "binding_executor_capability_grants_effect_authority": False,
        "transition_proposal_grants_effect_authority": False,
        "machine_state_mutation": "NONE_BY_TRANSITION_PROPOSAL",
        "parallel_dispatcher": "NONE",
        "parallel_effect_store": "NONE",
    }


__all__ = [
    "MACHINE_TRANSITION_CONTRACT_ID",
    "MACHINE_TRANSITION_CONTRACT_VERSION",
    "MACHINE_TRANSITION_STABILITY",
    "MachineTransitionIntent",
    "machine_transition_contract",
]
