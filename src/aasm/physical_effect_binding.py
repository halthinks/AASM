from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from math import isfinite
from typing import Any, Mapping

from .semantic_result import semantic_fingerprint


PHYSICAL_EFFECT_AUTHORITY_BINDING_CONTRACT_ID = "aasm.effect.physical-authority-binding.v1"
PHYSICAL_EFFECT_AUTHORITY_BINDING_CONTRACT_VERSION = "0.1.0"
PHYSICAL_EFFECT_AUTHORITY_BINDING_STABILITY = "FOUNDATION_EXPERIMENTAL"


def _required(value: str, name: str) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError(f"{name} is required")
    return text


def _optional(value: str | None) -> str:
    return "" if value is None else str(value).strip()


def _numeric_parameters(value: Mapping[str, Any]) -> dict[str, float]:
    result: dict[str, float] = {}
    for raw_name, raw_value in sorted(value.items(), key=lambda pair: str(pair[0])):
        name = _required(str(raw_name), "numeric parameter name")
        if isinstance(raw_value, bool) or not isinstance(raw_value, (int, float)):
            raise TypeError(f"physical effect numeric parameter must be int/float: {name}")
        number = float(raw_value)
        if not isfinite(number):
            raise ValueError(f"physical effect numeric parameter must be finite: {name}")
        result[name] = number
    return result


@dataclass(frozen=True)
class PhysicalEffectAuthorityBinding:
    effect_id: str
    effect_intent_id: str
    effect_intent_fingerprint: str
    workspace_id: str
    scope_id: str
    subject_id: str
    authority_domain_id: str
    authority_domain_fingerprint: str
    authority_lease_id: str
    authority_lease_fingerprint: str
    effect_capability_id: str
    effect_capability_fingerprint: str
    holder_principal_id: str
    authority_epoch: int
    effective_revocation_generation: int
    operation: str
    numeric_parameters: Mapping[str, Any]
    problem_revision_id: str = ""
    external_revision_id: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)
    binding_id: str = ""
    contract_id: str = PHYSICAL_EFFECT_AUTHORITY_BINDING_CONTRACT_ID
    contract_version: str = PHYSICAL_EFFECT_AUTHORITY_BINDING_CONTRACT_VERSION

    def __post_init__(self) -> None:
        for name in (
            "effect_id",
            "effect_intent_id",
            "effect_intent_fingerprint",
            "workspace_id",
            "scope_id",
            "subject_id",
            "authority_domain_id",
            "authority_domain_fingerprint",
            "authority_lease_id",
            "authority_lease_fingerprint",
            "effect_capability_id",
            "effect_capability_fingerprint",
            "holder_principal_id",
            "operation",
        ):
            object.__setattr__(self, name, _required(getattr(self, name), name))
        if (
            self.contract_id != PHYSICAL_EFFECT_AUTHORITY_BINDING_CONTRACT_ID
            or self.contract_version != PHYSICAL_EFFECT_AUTHORITY_BINDING_CONTRACT_VERSION
        ):
            raise ValueError("unsupported physical-effect authority-binding contract")
        if int(self.authority_epoch) < 1:
            raise ValueError("physical effect authority_epoch must be >= 1")
        if int(self.effective_revocation_generation) < 0:
            raise ValueError("physical effect effective_revocation_generation must be >= 0")
        object.__setattr__(self, "authority_epoch", int(self.authority_epoch))
        object.__setattr__(self, "effective_revocation_generation", int(self.effective_revocation_generation))
        object.__setattr__(self, "numeric_parameters", _numeric_parameters(self.numeric_parameters))
        object.__setattr__(self, "problem_revision_id", _optional(self.problem_revision_id))
        object.__setattr__(self, "external_revision_id", _optional(self.external_revision_id))
        object.__setattr__(self, "metadata", deepcopy(dict(self.metadata)))
        if not self.binding_id:
            object.__setattr__(
                self,
                "binding_id",
                f"physical-effect-binding-{semantic_fingerprint(self.identity_payload())[:24]}",
            )
        else:
            object.__setattr__(self, "binding_id", _required(self.binding_id, "binding_id"))

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "effect_id": self.effect_id,
            "effect_intent_id": self.effect_intent_id,
            "effect_intent_fingerprint": self.effect_intent_fingerprint,
            "workspace_id": self.workspace_id,
            "scope_id": self.scope_id,
            "subject_id": self.subject_id,
            "authority_domain_id": self.authority_domain_id,
            "authority_domain_fingerprint": self.authority_domain_fingerprint,
            "authority_lease_id": self.authority_lease_id,
            "authority_lease_fingerprint": self.authority_lease_fingerprint,
            "effect_capability_id": self.effect_capability_id,
            "effect_capability_fingerprint": self.effect_capability_fingerprint,
            "holder_principal_id": self.holder_principal_id,
            "authority_epoch": self.authority_epoch,
            "effective_revocation_generation": self.effective_revocation_generation,
            "operation": self.operation,
            "numeric_parameters": {
                name: self.numeric_parameters[name] for name in sorted(self.numeric_parameters)
            },
            "problem_revision_id": self.problem_revision_id,
            "external_revision_id": self.external_revision_id,
            "metadata": deepcopy(dict(self.metadata)),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"binding_id": self.binding_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"binding_id": self.binding_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "PhysicalEffectAuthorityBinding":
        payload = deepcopy(dict(value))
        payload.pop("fingerprint", None)
        payload["numeric_parameters"] = dict(payload.get("numeric_parameters") or {})
        return cls(**payload)


def physical_effect_authority_binding_contract() -> dict[str, Any]:
    return {
        "contract_id": PHYSICAL_EFFECT_AUTHORITY_BINDING_CONTRACT_ID,
        "contract_version": PHYSICAL_EFFECT_AUTHORITY_BINDING_CONTRACT_VERSION,
        "stability": PHYSICAL_EFFECT_AUTHORITY_BINDING_STABILITY,
        "role": "DURABLE_EFFECT_TO_CURRENT_PHYSICAL_AUTHORITY_IDENTITY_BINDING",
        "effect_source": "EXISTING_V54_EFFECT_INTENT_ONLY",
        "authority_source": "EXISTING_PR3_AUTHORITY_DOMAIN_LEASE_AND_EFFECT_CAPABILITY_ONLY",
        "operation_source": "DERIVED_FROM_DURABLE_EFFECT_SPEC_NOT_CALLER_ASSERTION",
        "numeric_parameter_source": "DERIVED_FROM_DURABLE_EFFECT_COMMAND_PAYLOAD_NOT_CALLER_ASSERTION",
        "numeric_parameter_semantics": "FINITE_NUMERIC_LEAVES_ONLY_UNITS_DEFERRED_TO_QUANTITY_CONTRACT",
        "authorization_recheck": "MANDATORY_AT_EXISTING_AUTHORIZE_EFFECT_BOUNDARY",
        "execution_recheck": "MANDATORY_AT_EXISTING_EXECUTE_EFFECT_BOUNDARY",
        "binding_existence_grants_effect_authority": False,
        "prior_use_validation_is_authorization": False,
        "resource_state_grants_authority": False,
        "fact_authority_grants_effect_authority": False,
        "parallel_authority_evaluator": "NONE",
        "parallel_effect_lifecycle": "NONE",
        "parallel_dispatcher": "NONE",
    }


__all__ = [
    "PHYSICAL_EFFECT_AUTHORITY_BINDING_CONTRACT_ID",
    "PHYSICAL_EFFECT_AUTHORITY_BINDING_CONTRACT_VERSION",
    "PHYSICAL_EFFECT_AUTHORITY_BINDING_STABILITY",
    "PhysicalEffectAuthorityBinding",
    "physical_effect_authority_binding_contract",
]
