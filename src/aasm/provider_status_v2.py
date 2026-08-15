from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from .semantic_result import semantic_fingerprint
from .solver_outcome_v2 import ProviderTermination, TERMINATION_REASONS


PROVIDER_STATUS_MAP_CONTRACT_ID = "aasm.solver.provider-status-map.v1"
PROVIDER_STATUS_MAP_CONTRACT_VERSION = "0.1.0"
PROVIDER_STATUS_MAP_STABILITY = "FOUNDATION_EXPERIMENTAL"


def _required(value: str, name: str) -> str:
    normalized = str(value).strip()
    if not normalized:
        raise ValueError(f"{name} is required")
    return normalized


def _uniq(values: Sequence[str]) -> tuple[str, ...]:
    return tuple(sorted(set(map(str, values))))


def _jsonable(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))}
    if isinstance(value, (tuple, list, set)):
        return [_jsonable(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    raise TypeError(f"provider status map value is not JSON serializable: {type(value)!r}")


@dataclass(frozen=True)
class ProviderStatusRule:
    reason: str
    raw_status: str = ""
    raw_status_code: str = ""
    limit_unit: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)
    rule_id: str = ""

    def __post_init__(self) -> None:
        if self.reason not in TERMINATION_REASONS:
            raise ValueError(f"invalid provider-status termination reason: {self.reason}")
        raw_status = str(self.raw_status)
        raw_code = str(self.raw_status_code)
        if not raw_status and not raw_code:
            raise ValueError("provider status rule requires raw_status and/or raw_status_code")
        object.__setattr__(self, "raw_status", raw_status)
        object.__setattr__(self, "raw_status_code", raw_code)
        object.__setattr__(self, "limit_unit", str(self.limit_unit))
        object.__setattr__(self, "metadata", _jsonable(dict(self.metadata)))
        if not self.rule_id:
            object.__setattr__(self, "rule_id", f"provider-status-rule-{semantic_fingerprint(self.identity_payload())[:20]}")

    @property
    def match_key(self) -> tuple[str, str]:
        return self.raw_status, self.raw_status_code

    def matches(self, raw_status: str, raw_status_code: str) -> bool:
        status_ok = not self.raw_status or self.raw_status == raw_status
        code_ok = not self.raw_status_code or self.raw_status_code == raw_status_code
        return status_ok and code_ok

    def identity_payload(self) -> dict[str, Any]:
        return {
            "reason": self.reason,
            "raw_status": self.raw_status,
            "raw_status_code": self.raw_status_code,
            "limit_unit": self.limit_unit,
            "metadata": _jsonable(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"rule_id": self.rule_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"rule_id": self.rule_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ProviderStatusRule":
        payload = deepcopy(dict(value)); payload.pop("fingerprint", None); return cls(**payload)


@dataclass(frozen=True)
class ProviderStatusMap:
    provider_id: str
    provider_version: str
    adapter_id: str
    adapter_version: str
    rules: tuple[ProviderStatusRule | Mapping[str, Any], ...]
    metadata: Mapping[str, Any] = field(default_factory=dict)
    map_id: str = ""
    contract_id: str = PROVIDER_STATUS_MAP_CONTRACT_ID
    contract_version: str = PROVIDER_STATUS_MAP_CONTRACT_VERSION

    def __post_init__(self) -> None:
        for name in ("provider_id", "provider_version", "adapter_id", "adapter_version"):
            object.__setattr__(self, name, _required(getattr(self, name), name))
        if self.contract_id != PROVIDER_STATUS_MAP_CONTRACT_ID or self.contract_version != PROVIDER_STATUS_MAP_CONTRACT_VERSION:
            raise ValueError("unsupported provider status map contract")
        rules = tuple(row if isinstance(row, ProviderStatusRule) else ProviderStatusRule.from_dict(row) for row in self.rules)
        if not rules:
            raise ValueError("provider status map requires at least one rule")
        exact_keys = [row.match_key for row in rules]
        if len(exact_keys) != len(set(exact_keys)):
            raise ValueError("provider status map contains duplicate exact rule keys")
        object.__setattr__(self, "rules", tuple(sorted(rules, key=lambda row: (row.raw_status, row.raw_status_code, row.rule_id))))
        object.__setattr__(self, "metadata", _jsonable(dict(self.metadata)))
        if not self.map_id:
            object.__setattr__(self, "map_id", f"provider-status-map-{semantic_fingerprint(self.identity_payload())[:20]}")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "provider_id": self.provider_id,
            "provider_version": self.provider_version,
            "adapter_id": self.adapter_id,
            "adapter_version": self.adapter_version,
            "rules": [row.to_dict() for row in self.rules],
            "metadata": _jsonable(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"map_id": self.map_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"map_id": self.map_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ProviderStatusMap":
        payload = deepcopy(dict(value)); payload.pop("fingerprint", None); payload["rules"] = tuple(payload.get("rules") or ()); return cls(**payload)


def map_provider_termination(
    status_map: ProviderStatusMap | Mapping[str, Any],
    *,
    raw_status: str = "",
    raw_status_code: str = "",
    raw_message: str = "",
    limit_value: float | int | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> ProviderTermination:
    mapping = status_map if isinstance(status_map, ProviderStatusMap) else ProviderStatusMap.from_dict(status_map)
    raw_status = str(raw_status)
    raw_status_code = str(raw_status_code)
    matches = [row for row in mapping.rules if row.matches(raw_status, raw_status_code)]
    if len(matches) > 1:
        raise ValueError(f"ambiguous provider status mapping for {raw_status!r}/{raw_status_code!r}")
    if not matches:
        return ProviderTermination(
            "UNKNOWN",
            raw_status=raw_status,
            raw_status_code=raw_status_code,
            raw_message=raw_message,
            limit_value=limit_value,
            metadata={
                "provider_status_map_id": mapping.map_id,
                "provider_status_map_fingerprint": mapping.fingerprint,
                "mapping_status": "NO_EXACT_RULE",
                **dict(metadata or {}),
            },
        )
    rule = matches[0]
    return ProviderTermination(
        rule.reason,
        raw_status=raw_status,
        raw_status_code=raw_status_code,
        raw_message=raw_message,
        limit_value=limit_value,
        limit_unit=rule.limit_unit,
        metadata={
            "provider_status_map_id": mapping.map_id,
            "provider_status_map_fingerprint": mapping.fingerprint,
            "provider_status_rule_id": rule.rule_id,
            "provider_status_rule_fingerprint": rule.fingerprint,
            "mapping_status": "EXACT_RULE",
            "rule_metadata": _jsonable(rule.metadata),
            **dict(metadata or {}),
        },
    )


def provider_status_map_contract() -> dict[str, Any]:
    return {
        "contract_id": PROVIDER_STATUS_MAP_CONTRACT_ID,
        "contract_version": PROVIDER_STATUS_MAP_CONTRACT_VERSION,
        "stability": PROVIDER_STATUS_MAP_STABILITY,
        "mapping": "EXACT_RAW_STATUS_AND_OR_CODE_RULES_ONLY",
        "fuzzy_matching": "FORBIDDEN",
        "unknown_raw_status": "PRESERVE_RAW_PAYLOAD_AND_NORMALIZE_TERMINATION_UNKNOWN",
        "ambiguous_mapping": "FAIL_CLOSED",
        "provider_and_adapter_identity": "FINGERPRINT_BOUND",
        "truth_authority": "NONE",
    }


__all__ = [
    "PROVIDER_STATUS_MAP_CONTRACT_ID",
    "PROVIDER_STATUS_MAP_CONTRACT_VERSION",
    "ProviderStatusRule",
    "ProviderStatusMap",
    "map_provider_termination",
    "provider_status_map_contract",
]
