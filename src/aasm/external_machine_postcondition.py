from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from .semantic_result import semantic_fingerprint


MACHINE_POSTCONDITION_VERIFICATION_CONTRACT_ID = "aasm.machine.postcondition-verification.v1"
MACHINE_POSTCONDITION_VERIFICATION_CONTRACT_VERSION = "0.1.0"
MACHINE_POSTCONDITION_VERIFICATION_STABILITY = "FOUNDATION_EXPERIMENTAL"

POSTCONDITION_VERDICTS = ("VERIFIED", "MISMATCH")


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
    raise TypeError(f"postcondition value is not JSON serializable: {type(value)!r}")


@dataclass(frozen=True)
class MachinePostconditionVerification:
    transition_id: str
    effect_id: str
    binding_id: str
    verifier_principal_id: str
    verdict: str
    target_state_claim_ids: tuple[str, ...]
    achieved_state_claim_ids: tuple[str, ...]
    machine_observation_ids: tuple[str, ...]
    comparison: Mapping[str, Any]
    metadata: Mapping[str, Any] = field(default_factory=dict)
    verification_id: str = ""
    contract_id: str = MACHINE_POSTCONDITION_VERIFICATION_CONTRACT_ID
    contract_version: str = MACHINE_POSTCONDITION_VERIFICATION_CONTRACT_VERSION

    def __post_init__(self) -> None:
        for name in (
            "transition_id",
            "effect_id",
            "binding_id",
            "verifier_principal_id",
            "verdict",
        ):
            object.__setattr__(self, name, _require(getattr(self, name), name))
        if self.contract_id != MACHINE_POSTCONDITION_VERIFICATION_CONTRACT_ID or self.contract_version != MACHINE_POSTCONDITION_VERIFICATION_CONTRACT_VERSION:
            raise ValueError("unsupported machine postcondition verification contract")
        verdict = str(self.verdict).upper()
        if verdict not in POSTCONDITION_VERDICTS:
            raise ValueError(f"unsupported postcondition verdict: {self.verdict}")
        object.__setattr__(self, "verdict", verdict)
        object.__setattr__(self, "target_state_claim_ids", _uniq(self.target_state_claim_ids, "target_state_claim_ids"))
        object.__setattr__(self, "achieved_state_claim_ids", _uniq(self.achieved_state_claim_ids, "achieved_state_claim_ids"))
        object.__setattr__(self, "machine_observation_ids", _uniq(self.machine_observation_ids, "machine_observation_ids"))
        object.__setattr__(self, "comparison", _jsonable(dict(self.comparison)))
        object.__setattr__(self, "metadata", _jsonable(dict(self.metadata)))
        if not self.verification_id:
            object.__setattr__(
                self,
                "verification_id",
                f"machine-postcondition-{semantic_fingerprint(self.identity_payload())[:24]}",
            )
        else:
            object.__setattr__(self, "verification_id", _require(self.verification_id, "verification_id"))

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "transition_id": self.transition_id,
            "effect_id": self.effect_id,
            "binding_id": self.binding_id,
            "verifier_principal_id": self.verifier_principal_id,
            "verdict": self.verdict,
            "target_state_claim_ids": list(self.target_state_claim_ids),
            "achieved_state_claim_ids": list(self.achieved_state_claim_ids),
            "machine_observation_ids": list(self.machine_observation_ids),
            "comparison": _jsonable(self.comparison),
            "metadata": _jsonable(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"verification_id": self.verification_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"verification_id": self.verification_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "MachinePostconditionVerification":
        payload = deepcopy(dict(value))
        payload.pop("fingerprint", None)
        payload["target_state_claim_ids"] = tuple(payload.get("target_state_claim_ids") or ())
        payload["achieved_state_claim_ids"] = tuple(payload.get("achieved_state_claim_ids") or ())
        payload["machine_observation_ids"] = tuple(payload.get("machine_observation_ids") or ())
        return cls(**payload)


def machine_postcondition_verification_contract() -> dict[str, Any]:
    return {
        "contract_id": MACHINE_POSTCONDITION_VERIFICATION_CONTRACT_ID,
        "contract_version": MACHINE_POSTCONDITION_VERIFICATION_CONTRACT_VERSION,
        "stability": MACHINE_POSTCONDITION_VERIFICATION_STABILITY,
        "effect_status_requirement": "EXISTING_AASM_EFFECT_MUST_BE_SUCCEEDED",
        "unknown_effect": "BLOCKED_USE_EXISTING_EFFECT_RECONCILIATION",
        "failed_or_cancelled_effect": "BLOCKED_NO_ACHIEVEMENT_CLAIM",
        "target_source": "PR2B_DURABLE_DESIRED_STATE_CLAIMS",
        "achieved_source": "PR1_DURABLE_AUTHORITATIVE_STATE_CLAIMS_ONLY",
        "observation_correlation": "PR2A_MACHINE_STATE_OBSERVATION_MUST_REFERENCE_AUTHORITATIVE_SOURCE_OBSERVED_CLAIM",
        "comparison": "EXACT_CANONICAL_VALUE_EQUALITY_ONLY_NO_TOLERANCE_IN_THIS_FOUNDATION",
        "verdicts": list(POSTCONDITION_VERDICTS),
        "effect_success_is_achievement": False,
        "verification_mints_fact_authority": False,
        "verification_mints_state_claim": False,
        "verification_mutates_effect_outcome": False,
        "verification_mutates_machine_state": False,
        "verification_grants_effect_authority": False,
        "parallel_truth_table": "NONE",
        "parallel_effect_lifecycle": "NONE",
        "freshness_semantics": "NOT_YET_CLAIMED_PR4",
        "calibration_semantics": "NOT_YET_CLAIMED_PR4",
    }


__all__ = [
    "MACHINE_POSTCONDITION_VERIFICATION_CONTRACT_ID",
    "MACHINE_POSTCONDITION_VERIFICATION_CONTRACT_VERSION",
    "MACHINE_POSTCONDITION_VERIFICATION_STABILITY",
    "POSTCONDITION_VERDICTS",
    "MachinePostconditionVerification",
    "machine_postcondition_verification_contract",
]
