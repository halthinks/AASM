from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from .semantic_result import semantic_fingerprint
from .solver_outcome_v2 import NORMALIZED_STATUSES, ProviderTermination, TERMINATION_REASONS


PROVIDER_STATUS_MAP_CONTRACT_ID = "aasm.solver.provider-status-map.v1"
PROVIDER_STATUS_MAP_CONTRACT_VERSION = "0.2.0"
PROVIDER_STATUS_MAP_STABILITY = "QUALIFICATION_CANDIDATE"

STATUS_RULES = (
    *NORMALIZED_STATUSES,
    "OPTIMAL_OR_SAT",
    "INFEASIBLE_OR_UNSAT",
    "TIME_LIMIT_DYNAMIC",
    "NODE_LIMIT_DYNAMIC",
    "ITERATION_LIMIT_DYNAMIC",
    "SOLUTION_LIMIT_DYNAMIC",
    "MEMORY_LIMIT_DYNAMIC",
    "OBJECTIVE_BOUND_DYNAMIC",
    "OBJECTIVE_TARGET_DYNAMIC",
    "USER_INTERRUPT_DYNAMIC",
    "UNKNOWN_DYNAMIC",
)
INCUMBENT_ELIGIBILITY = ("NEVER", "VALIDATED_IF_PRESENT", "REQUIRED")
BOUND_ELIGIBILITY = ("NEVER", "IF_PROVIDER_SUPPLIED", "EXPECTED_IF_OBJECTIVE")
CERTIFICATE_ELIGIBILITY = ("NONE", "OPTIONAL", "PROVIDER_SPECIFIC")


def _required(value: str, name: str) -> str:
    normalized = str(value).strip()
    if not normalized:
        raise ValueError(f"{name} is required")
    return normalized


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
    normalized_status: str
    raw_status: str = ""
    raw_status_code: str = ""
    incumbent_eligibility: str = "NEVER"
    bound_eligibility: str = "NEVER"
    certificate_eligibility: str = "NONE"
    provider_version_range: str = ""
    limit_unit: str = ""
    notes: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)
    rule_id: str = ""

    def __post_init__(self) -> None:
        if self.reason not in TERMINATION_REASONS:
            raise ValueError(f"invalid provider-status termination reason: {self.reason}")
        if self.normalized_status not in STATUS_RULES:
            raise ValueError(f"invalid provider-status normalized rule: {self.normalized_status}")
        if self.incumbent_eligibility not in INCUMBENT_ELIGIBILITY:
            raise ValueError(f"invalid incumbent eligibility: {self.incumbent_eligibility}")
        if self.bound_eligibility not in BOUND_ELIGIBILITY:
            raise ValueError(f"invalid bound eligibility: {self.bound_eligibility}")
        if self.certificate_eligibility not in CERTIFICATE_ELIGIBILITY:
            raise ValueError(f"invalid certificate eligibility: {self.certificate_eligibility}")
        raw_status = str(self.raw_status)
        raw_code = str(self.raw_status_code)
        if not raw_status and not raw_code:
            raise ValueError("provider status rule requires raw_status and/or raw_status_code")
        object.__setattr__(self, "raw_status", raw_status)
        object.__setattr__(self, "raw_status_code", raw_code)
        object.__setattr__(self, "provider_version_range", str(self.provider_version_range))
        object.__setattr__(self, "limit_unit", str(self.limit_unit))
        object.__setattr__(self, "notes", str(self.notes))
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
            "normalized_status": self.normalized_status,
            "raw_status": self.raw_status,
            "raw_status_code": self.raw_status_code,
            "incumbent_eligibility": self.incumbent_eligibility,
            "bound_eligibility": self.bound_eligibility,
            "certificate_eligibility": self.certificate_eligibility,
            "provider_version_range": self.provider_version_range,
            "limit_unit": self.limit_unit,
            "notes": self.notes,
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
        for rule in rules:
            if rule.provider_version_range and rule.provider_version_range != f"=={self.provider_version}":
                raise ValueError("v0.56 qualification maps support exact provider-version ranges only")
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


@dataclass(frozen=True)
class ProviderStatusMapping:
    normalized_status: str
    termination: ProviderTermination
    rule_id: str
    map_id: str
    map_version: str
    incumbent_eligibility: str
    bound_eligibility: str
    certificate_eligibility: str
    mapping_status: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "normalized_status": self.normalized_status,
            "termination": self.termination.to_dict(),
            "rule_id": self.rule_id,
            "map_id": self.map_id,
            "map_version": self.map_version,
            "incumbent_eligibility": self.incumbent_eligibility,
            "bound_eligibility": self.bound_eligibility,
            "certificate_eligibility": self.certificate_eligibility,
            "mapping_status": self.mapping_status,
        }


def _resolve_status(rule: str, *, has_incumbent: bool, objective_present: bool) -> str:
    direct = set(NORMALIZED_STATUSES)
    if rule in direct:
        return rule
    if rule == "OPTIMAL_OR_SAT":
        return "OPTIMAL" if objective_present else "SAT"
    if rule == "INFEASIBLE_OR_UNSAT":
        return "INFEASIBLE" if objective_present else "UNSAT"
    dynamic = {
        "TIME_LIMIT_DYNAMIC": "TIME_LIMIT",
        "NODE_LIMIT_DYNAMIC": "NODE_LIMIT",
        "ITERATION_LIMIT_DYNAMIC": "ITERATION_LIMIT",
        "SOLUTION_LIMIT_DYNAMIC": "SOLUTION_LIMIT",
        "MEMORY_LIMIT_DYNAMIC": "MEMORY_LIMIT",
        "OBJECTIVE_BOUND_DYNAMIC": "OBJECTIVE_BOUND",
        "OBJECTIVE_TARGET_DYNAMIC": "OBJECTIVE_TARGET",
        "USER_INTERRUPT_DYNAMIC": "USER_INTERRUPT",
    }
    if rule in dynamic:
        return f"{dynamic[rule]}_{'WITH_INCUMBENT' if has_incumbent else 'NO_SOLUTION'}"
    if rule == "UNKNOWN_DYNAMIC":
        return "UNKNOWN_WITH_INCUMBENT" if has_incumbent else "UNKNOWN_NO_SOLUTION"
    raise ValueError(f"unsupported provider status rule: {rule}")


def map_provider_status(
    status_map: ProviderStatusMap | Mapping[str, Any],
    *,
    raw_status: str = "",
    raw_status_code: str = "",
    raw_message: str = "",
    has_incumbent: bool = False,
    objective_present: bool = False,
    limit_value: float | int | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> ProviderStatusMapping:
    mapping = status_map if isinstance(status_map, ProviderStatusMap) else ProviderStatusMap.from_dict(status_map)
    raw_status = str(raw_status)
    raw_status_code = str(raw_status_code)
    matches = [row for row in mapping.rules if row.matches(raw_status, raw_status_code)]
    if len(matches) > 1:
        raise ValueError(f"ambiguous provider status mapping for {raw_status!r}/{raw_status_code!r}")
    if not matches:
        termination = ProviderTermination(
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
        return ProviderStatusMapping(
            "UNKNOWN_WITH_INCUMBENT" if has_incumbent else "UNKNOWN_NO_SOLUTION",
            termination,
            "",
            mapping.map_id,
            mapping.contract_version,
            "VALIDATED_IF_PRESENT",
            "IF_PROVIDER_SUPPLIED",
            "NONE",
            "NO_EXACT_RULE",
        )
    rule = matches[0]
    if has_incumbent and rule.incumbent_eligibility == "NEVER":
        raise ValueError(f"provider status rule {rule.rule_id} forbids an incumbent")
    if not has_incumbent and rule.incumbent_eligibility == "REQUIRED":
        raise ValueError(f"provider status rule {rule.rule_id} requires an incumbent")
    termination = ProviderTermination(
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
            "provider_version_range": rule.provider_version_range,
            "rule_notes": rule.notes,
            "rule_metadata": _jsonable(rule.metadata),
            **dict(metadata or {}),
        },
    )
    return ProviderStatusMapping(
        _resolve_status(rule.normalized_status, has_incumbent=has_incumbent, objective_present=objective_present),
        termination,
        rule.rule_id,
        mapping.map_id,
        mapping.contract_version,
        rule.incumbent_eligibility,
        rule.bound_eligibility,
        rule.certificate_eligibility,
        "EXACT_RULE",
    )


def map_provider_termination(status_map: ProviderStatusMap | Mapping[str, Any], **kwargs: Any) -> ProviderTermination:
    """Backward-compatible termination-only projection of the richer v0.56 status mapping."""
    return map_provider_status(status_map, **kwargs).termination


def _rule(version: str, reason: str, normalized_status: str, raw_status: str, code: int | str, *, incumbent: str = "NEVER", bound: str = "NEVER", certificate: str = "NONE", limit_unit: str = "", notes: str = "") -> ProviderStatusRule:
    return ProviderStatusRule(
        reason,
        normalized_status,
        raw_status,
        str(code),
        incumbent,
        bound,
        certificate,
        f"=={version}",
        limit_unit,
        notes,
    )


def ortools_cp_sat_status_map(version: str) -> ProviderStatusMap:
    version = _required(version, "OR-Tools version")
    return ProviderStatusMap(
        "ortools-cp-sat", version, "aasm.optimization.ortools-cp-sat", "0.1.0",
        (
            _rule(version, "UNKNOWN", "UNKNOWN_DYNAMIC", "UNKNOWN", 0, incumbent="VALIDATED_IF_PRESENT", bound="IF_PROVIDER_SUPPLIED", notes="OR-Tools UNKNOWN does not identify whether time, memory, or another custom limit stopped the search."),
            _rule(version, "MODEL_INVALID", "MODEL_INVALID", "MODEL_INVALID", 1, notes="CpModelProto validation failed; never map to infeasible."),
            _rule(version, "COMPLETED", "FEASIBLE_NOT_PROVEN_OPTIMAL", "FEASIBLE", 2, incumbent="REQUIRED", bound="IF_PROVIDER_SUPPLIED"),
            _rule(version, "COMPLETED", "INFEASIBLE_OR_UNSAT", "INFEASIBLE", 3, certificate="PROVIDER_SPECIFIC"),
            _rule(version, "COMPLETED", "OPTIMAL_OR_SAT", "OPTIMAL", 4, incumbent="REQUIRED", bound="EXPECTED_IF_OBJECTIVE", certificate="PROVIDER_SPECIFIC"),
        ),
        metadata={"source": "ortools CpSolverStatus enum", "raw_code_type": "CpSolverStatus numeric value"},
    )


def highs_status_map(version: str) -> ProviderStatusMap:
    version = _required(version, "HiGHS version")
    rows = (
        _rule(version, "UNKNOWN", "UNKNOWN_DYNAMIC", "kNotset", 0, incumbent="VALIDATED_IF_PRESENT"),
        _rule(version, "INTERNAL_ERROR", "INTERNAL_ERROR", "kLoadError", 1),
        _rule(version, "MODEL_INVALID", "MODEL_INVALID", "kModelError", 2),
        _rule(version, "INTERNAL_ERROR", "INTERNAL_ERROR", "kPresolveError", 3),
        _rule(version, "INTERNAL_ERROR", "INTERNAL_ERROR", "kSolveError", 4),
        _rule(version, "INTERNAL_ERROR", "INTERNAL_ERROR", "kPostsolveError", 5),
        _rule(version, "COMPLETED", "UNKNOWN_DYNAMIC", "kModelEmpty", 6),
        _rule(version, "COMPLETED", "OPTIMAL_OR_SAT", "kOptimal", 7, incumbent="REQUIRED", bound="EXPECTED_IF_OBJECTIVE", certificate="PROVIDER_SPECIFIC"),
        _rule(version, "COMPLETED", "INFEASIBLE_OR_UNSAT", "kInfeasible", 8, certificate="PROVIDER_SPECIFIC"),
        _rule(version, "COMPLETED", "INFEASIBLE_OR_UNBOUNDED", "kUnboundedOrInfeasible", 9),
        _rule(version, "COMPLETED", "UNBOUNDED", "kUnbounded", 10, certificate="PROVIDER_SPECIFIC"),
        _rule(version, "OBJECTIVE_BOUND", "OBJECTIVE_BOUND_DYNAMIC", "kObjectiveBound", 11, incumbent="VALIDATED_IF_PRESENT", bound="IF_PROVIDER_SUPPLIED"),
        _rule(version, "OBJECTIVE_TARGET", "OBJECTIVE_TARGET_DYNAMIC", "kObjectiveTarget", 12, incumbent="VALIDATED_IF_PRESENT", bound="IF_PROVIDER_SUPPLIED"),
        _rule(version, "TIME_LIMIT", "TIME_LIMIT_DYNAMIC", "kTimeLimit", 13, incumbent="VALIDATED_IF_PRESENT", bound="IF_PROVIDER_SUPPLIED", limit_unit="seconds"),
        _rule(version, "ITERATION_LIMIT", "ITERATION_LIMIT_DYNAMIC", "kIterationLimit", 14, incumbent="VALIDATED_IF_PRESENT", bound="IF_PROVIDER_SUPPLIED", limit_unit="iterations"),
        _rule(version, "UNKNOWN", "UNKNOWN_DYNAMIC", "kUnknown", 15, incumbent="VALIDATED_IF_PRESENT", bound="IF_PROVIDER_SUPPLIED"),
        _rule(version, "SOLUTION_LIMIT", "SOLUTION_LIMIT_DYNAMIC", "kSolutionLimit", 16, incumbent="VALIDATED_IF_PRESENT", bound="IF_PROVIDER_SUPPLIED", limit_unit="solutions"),
        _rule(version, "USER_INTERRUPT", "USER_INTERRUPT_DYNAMIC", "kInterrupt", 17, incumbent="VALIDATED_IF_PRESENT", bound="IF_PROVIDER_SUPPLIED"),
    )
    return ProviderStatusMap(
        "highs", version, "aasm.optimization.highs", "0.1.0", rows,
        metadata={"source": "HiGHS HighsModelStatus enum", "raw_code_type": "HighsModelStatus integer value"},
    )


def pysat_cadical_status_map(version: str) -> ProviderStatusMap:
    version = _required(version, "python-sat version")
    return ProviderStatusMap(
        "cadical", version, "aasm.optimization.pysat-cadical", "0.1.0",
        (
            ProviderStatusRule("COMPLETED", "SAT", "SAT", "1", "REQUIRED", "NEVER", "PROVIDER_SPECIFIC", f"=={version}", notes="PySAT solve() returned True and the assignment must still pass AASM validation."),
            ProviderStatusRule("COMPLETED", "UNSAT", "UNSAT", "0", "NEVER", "NEVER", "PROVIDER_SPECIFIC", f"=={version}", notes="PySAT solve() returned False."),
        ),
        metadata={"source": "PySAT Solver.solve boolean result", "limit_specific_statuses": "UNSUPPORTED_BY_CURRENT_AASM_CADICAL_ADAPTER"},
    )


def default_provider_status_map(provider_id: str, provider_version: str) -> ProviderStatusMap:
    if provider_id == "ortools-cp-sat":
        return ortools_cp_sat_status_map(provider_version)
    if provider_id == "highs":
        return highs_status_map(provider_version)
    if provider_id == "cadical":
        return pysat_cadical_status_map(provider_version)
    raise KeyError(f"no qualified v0.56 provider status map for {provider_id}")


def provider_status_map_contract() -> dict[str, Any]:
    return {
        "contract_id": PROVIDER_STATUS_MAP_CONTRACT_ID,
        "contract_version": PROVIDER_STATUS_MAP_CONTRACT_VERSION,
        "stability": PROVIDER_STATUS_MAP_STABILITY,
        "mapping": "EXACT_NATIVE_ENUM_NAME_AND_OR_CODE_RULES_ONLY",
        "fuzzy_matching": "FORBIDDEN",
        "substring_inference": "FORBIDDEN",
        "unknown_raw_status": "PRESERVE_RAW_PAYLOAD_AND_NORMALIZE_CONSERVATIVELY",
        "ambiguous_mapping": "FAIL_CLOSED",
        "provider_version_qualification": "EXACT_VERSION_RANGE_IN_V056_FOUNDATION",
        "rule_fields": ["normalized_status", "termination_reason", "incumbent_eligibility", "bound_eligibility", "certificate_eligibility", "notes"],
        "qualified_provider_families": ["cadical/PySAT", "OR-Tools CP-SAT", "HiGHS"],
        "truth_authority": "NONE",
    }


__all__ = [
    "PROVIDER_STATUS_MAP_CONTRACT_ID", "PROVIDER_STATUS_MAP_CONTRACT_VERSION",
    "ProviderStatusRule", "ProviderStatusMap", "ProviderStatusMapping", "map_provider_status",
    "map_provider_termination", "ortools_cp_sat_status_map", "highs_status_map",
    "pysat_cadical_status_map", "default_provider_status_map", "provider_status_map_contract",
]
