from __future__ import annotations

import ast
from pathlib import Path
import re
import subprocess
import textwrap

ROOT = Path.cwd()


def write(path: str, content: str) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(textwrap.dedent(content).lstrip("\n"), encoding="utf-8")


def replace_once(path: str, old: str, new: str) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    if new in text:
        return
    if old not in text:
        raise SystemExit(f"required patch anchor not found in {path}: {old!r}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


def append_once(path: str, marker: str, content: str) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    if marker in text:
        return
    target.write_text(text.rstrip() + "\n\n" + textwrap.dedent(content).strip() + "\n", encoding="utf-8")


write(
    "src/aasm/_epistemic_debt.py",
    r'''
    from __future__ import annotations

    from copy import deepcopy
    from dataclasses import dataclass, field
    import re
    from typing import Any, Mapping

    from .calculus import OBLIGATION_STATUSES, content_hash, normalize_calculus_state
    from .obligation_phase import (
        OBLIGATION_PHASES,
        ObligationPhasePlan,
        obligation_semantic_fingerprint,
        validate_obligation_phase_plan,
    )
    from .scopes import scope_id_from
    from .semantic_result import semantic_fingerprint


    EPISTEMIC_DEBT_CONTRACT_ID = "aasm.epistemic.debt.v1"
    EPISTEMIC_DEBT_CONTRACT_VERSION = "0.1.0"
    EPISTEMIC_DEBT_STABILITY = "FOUNDATION_EXPERIMENTAL"
    EPISTEMIC_DEBT_CLASSES = ("OUTSTANDING", "TERMINAL_UNRESOLVED")
    SATISFIED_OBLIGATION_STATUSES = ("VERIFIED", "COMMITTED")
    TERMINAL_UNRESOLVED_STATUSES = ("REJECTED", "SUPERSEDED", "IMPOSSIBLE")

    _SHA256 = re.compile(r"^[0-9a-f]{64}$")


    def _required(name: str, value: Any) -> str:
        text = str(value).strip()
        if not text:
            raise ValueError(f"epistemic-debt {name} is required")
        return text


    def _optional(value: Any) -> str:
        return "" if value is None else str(value).strip()


    def _sha256(name: str, value: Any) -> str:
        text = _required(name, value).lower()
        if not _SHA256.fullmatch(text):
            raise ValueError(
                f"epistemic-debt {name} must be a lowercase 64-hex SHA-256 digest"
            )
        return text


    def _uniq(values: Any, *, name: str) -> tuple[str, ...]:
        return tuple(sorted({_required(name, value) for value in values}))


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
            raise TypeError(
                "binary floating-point values are forbidden in epistemic-debt portable identity"
            )
        if isinstance(value, (str, int, bool)) or value is None:
            return value
        raise TypeError(f"epistemic-debt value is not JSON serializable: {type(value)!r}")


    @dataclass(frozen=True)
    class EpistemicDebtItem:
        obligation_id: str
        obligation_semantic_fingerprint: str
        obligation_status: str
        classification: str
        statement: str
        dependency_obligation_ids: tuple[str, ...] = ()
        required_evidence_types: tuple[str, ...] = ()
        attached_evidence_ids: tuple[str, ...] = ()
        mandatory: bool = True
        persistent: bool = True
        scope_id: str = "root"
        phase: str = ""
        diagnostics: tuple[str, ...] = ()
        item_id: str = ""

        def __post_init__(self) -> None:
            obligation_id = _required("obligation_id", self.obligation_id)
            obligation_fingerprint = _sha256(
                "obligation_semantic_fingerprint",
                self.obligation_semantic_fingerprint,
            )
            status = _required("obligation_status", self.obligation_status).upper()
            if status not in OBLIGATION_STATUSES:
                raise ValueError(f"unsupported existing obligation status: {status}")
            if status in SATISFIED_OBLIGATION_STATUSES:
                raise ValueError("satisfied obligations cannot appear in epistemic debt")
            classification = _required("classification", self.classification).upper()
            if classification not in EPISTEMIC_DEBT_CLASSES:
                raise ValueError(f"unsupported epistemic debt classification: {classification}")
            expected = (
                "TERMINAL_UNRESOLVED"
                if status in TERMINAL_UNRESOLVED_STATUSES
                else "OUTSTANDING"
            )
            if classification != expected:
                raise ValueError(
                    "epistemic debt classification must be derived from the existing obligation status"
                )
            phase = _optional(self.phase).upper()
            if phase and phase not in OBLIGATION_PHASES:
                raise ValueError(f"unsupported obligation phase on epistemic debt item: {phase}")
            object.__setattr__(self, "obligation_id", obligation_id)
            object.__setattr__(
                self,
                "obligation_semantic_fingerprint",
                obligation_fingerprint,
            )
            object.__setattr__(self, "obligation_status", status)
            object.__setattr__(self, "classification", classification)
            object.__setattr__(self, "statement", _required("statement", self.statement))
            object.__setattr__(
                self,
                "dependency_obligation_ids",
                _uniq(
                    self.dependency_obligation_ids,
                    name="dependency obligation_id",
                ),
            )
            object.__setattr__(
                self,
                "required_evidence_types",
                _uniq(self.required_evidence_types, name="required evidence type"),
            )
            object.__setattr__(
                self,
                "attached_evidence_ids",
                _uniq(self.attached_evidence_ids, name="attached evidence_id"),
            )
            object.__setattr__(self, "mandatory", bool(self.mandatory))
            object.__setattr__(self, "persistent", bool(self.persistent))
            object.__setattr__(self, "scope_id", _required("scope_id", self.scope_id))
            object.__setattr__(self, "phase", phase)
            object.__setattr__(
                self,
                "diagnostics",
                _uniq(self.diagnostics, name="debt diagnostic"),
            )
            derived = f"epistemic-debt-item-{semantic_fingerprint(self.identity_payload())[:24]}"
            supplied = _optional(self.item_id)
            if supplied and supplied != derived:
                raise ValueError("epistemic debt item_id does not match canonical identity")
            object.__setattr__(self, "item_id", derived)

        def identity_payload(self) -> dict[str, Any]:
            return {
                "obligation_id": self.obligation_id,
                "obligation_semantic_fingerprint": self.obligation_semantic_fingerprint,
                "obligation_status": self.obligation_status,
                "classification": self.classification,
                "statement": self.statement,
                "dependency_obligation_ids": list(self.dependency_obligation_ids),
                "required_evidence_types": list(self.required_evidence_types),
                "attached_evidence_ids": list(self.attached_evidence_ids),
                "mandatory": self.mandatory,
                "persistent": self.persistent,
                "scope_id": self.scope_id,
                "phase": self.phase,
                "diagnostics": list(self.diagnostics),
            }

        @property
        def fingerprint(self) -> str:
            return semantic_fingerprint({"item_id": self.item_id, **self.identity_payload()})

        def to_dict(self) -> dict[str, Any]:
            return {
                "item_id": self.item_id,
                **self.identity_payload(),
                "fingerprint": self.fingerprint,
            }

        @classmethod
        def from_dict(cls, value: Mapping[str, Any]) -> "EpistemicDebtItem":
            payload = deepcopy(dict(value))
            supplied = str(payload.pop("fingerprint", "")).strip()
            for name in (
                "dependency_obligation_ids",
                "required_evidence_types",
                "attached_evidence_ids",
                "diagnostics",
            ):
                payload[name] = tuple(payload.get(name) or ())
            item = cls(**payload)
            if supplied and supplied != item.fingerprint:
                raise ValueError("epistemic debt item fingerprint mismatch")
            return item


    @dataclass(frozen=True)
    class EpistemicDebtProjection:
        problem_revision_id: str
        problem_revision_fingerprint: str
        calculus_state_fingerprint: str
        items: tuple[EpistemicDebtItem | Mapping[str, Any], ...]
        metadata: Mapping[str, Any] = field(default_factory=dict)
        projection_id: str = ""
        contract_id: str = EPISTEMIC_DEBT_CONTRACT_ID
        contract_version: str = EPISTEMIC_DEBT_CONTRACT_VERSION

        def __post_init__(self) -> None:
            if (
                self.contract_id != EPISTEMIC_DEBT_CONTRACT_ID
                or self.contract_version != EPISTEMIC_DEBT_CONTRACT_VERSION
            ):
                raise ValueError("unsupported epistemic-debt contract")
            revision_id = _required("problem_revision_id", self.problem_revision_id)
            revision_fingerprint = _sha256(
                "problem_revision_fingerprint",
                self.problem_revision_fingerprint,
            )
            state_fingerprint = _sha256(
                "calculus_state_fingerprint",
                self.calculus_state_fingerprint,
            )
            items = tuple(
                value
                if isinstance(value, EpistemicDebtItem)
                else EpistemicDebtItem.from_dict(value)
                for value in self.items
            )
            ids = [value.obligation_id for value in items]
            if len(ids) != len(set(ids)):
                raise ValueError(
                    "epistemic debt projection permits at most one item per existing obligation_id"
                )
            items = tuple(sorted(items, key=lambda value: value.obligation_id))
            object.__setattr__(self, "problem_revision_id", revision_id)
            object.__setattr__(
                self,
                "problem_revision_fingerprint",
                revision_fingerprint,
            )
            object.__setattr__(self, "calculus_state_fingerprint", state_fingerprint)
            object.__setattr__(self, "items", items)
            object.__setattr__(self, "metadata", _jsonable(dict(self.metadata)))
            derived = f"epistemic-debt-{semantic_fingerprint(self.identity_payload())[:24]}"
            supplied = _optional(self.projection_id)
            if supplied and supplied != derived:
                raise ValueError("epistemic debt projection_id does not match canonical identity")
            object.__setattr__(self, "projection_id", derived)

        @property
        def outstanding_count(self) -> int:
            return sum(value.classification == "OUTSTANDING" for value in self.items)

        @property
        def terminal_unresolved_count(self) -> int:
            return sum(
                value.classification == "TERMINAL_UNRESOLVED" for value in self.items
            )

        def identity_payload(self) -> dict[str, Any]:
            return {
                "contract_id": self.contract_id,
                "contract_version": self.contract_version,
                "problem_revision_id": self.problem_revision_id,
                "problem_revision_fingerprint": self.problem_revision_fingerprint,
                "calculus_state_fingerprint": self.calculus_state_fingerprint,
                "items": [value.identity_payload() for value in self.items],
                "metadata": _jsonable(self.metadata),
            }

        @property
        def fingerprint(self) -> str:
            return semantic_fingerprint(
                {"projection_id": self.projection_id, **self.identity_payload()}
            )

        def to_dict(self) -> dict[str, Any]:
            return {
                "projection_id": self.projection_id,
                "contract_id": self.contract_id,
                "contract_version": self.contract_version,
                "problem_revision_id": self.problem_revision_id,
                "problem_revision_fingerprint": self.problem_revision_fingerprint,
                "calculus_state_fingerprint": self.calculus_state_fingerprint,
                "items": [value.to_dict() for value in self.items],
                "total_debt_count": len(self.items),
                "outstanding_count": self.outstanding_count,
                "terminal_unresolved_count": self.terminal_unresolved_count,
                "metadata": _jsonable(self.metadata),
                "fingerprint": self.fingerprint,
            }

        @classmethod
        def from_dict(cls, value: Mapping[str, Any]) -> "EpistemicDebtProjection":
            payload = deepcopy(dict(value))
            supplied = str(payload.pop("fingerprint", "")).strip()
            payload.pop("total_debt_count", None)
            payload.pop("outstanding_count", None)
            payload.pop("terminal_unresolved_count", None)
            payload["items"] = tuple(payload.get("items") or ())
            item = cls(**payload)
            if supplied and supplied != item.fingerprint:
                raise ValueError("epistemic debt projection fingerprint mismatch")
            return item


    def _validate_canonical_edges(state: Mapping[str, Any]) -> None:
        obligations = dict(state.get("obligations") or {})
        expected = {
            (str(dependency), str(obligation_id), "REQUIRES")
            for obligation_id, obligation in obligations.items()
            for dependency in obligation.get("dependencies", [])
        }
        actual: set[tuple[str, str, str]] = set()
        for raw in state.get("obligation_edges", []):
            edge = dict(raw)
            src = _required("obligation edge src", edge.get("src"))
            dst = _required("obligation edge dst", edge.get("dst"))
            relation = _required("obligation edge relation", edge.get("relation"))
            if src not in obligations or dst not in obligations:
                raise ValueError(
                    "epistemic debt projection encountered an edge with unknown canonical obligation"
                )
            key = (src, dst, relation)
            if key in actual:
                raise ValueError(
                    "epistemic debt projection encountered duplicate canonical obligation edge"
                )
            actual.add(key)
        if actual != expected:
            raise ValueError(
                "canonical obligation_edges must exactly represent ObligationRecord.dependencies before epistemic debt projection"
            )


    def project_epistemic_debt(
        calculus_state: Mapping[str, Any],
        *,
        problem_revision_id: str,
        problem_revision_fingerprint: str,
        phase_plan: ObligationPhasePlan | Mapping[str, Any] | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> EpistemicDebtProjection:
        state = normalize_calculus_state(deepcopy(dict(calculus_state)))
        if int(state.get("schema_version", -1)) != 1:
            raise ValueError(
                "epistemic debt projection requires the existing calculus state schema_version 1"
            )
        _validate_canonical_edges(state)
        revision_id = _required("problem_revision_id", problem_revision_id)
        revision_fingerprint = _sha256(
            "problem_revision_fingerprint",
            problem_revision_fingerprint,
        )
        phases: dict[str, str] = {}
        if phase_plan is not None:
            plan = (
                phase_plan
                if isinstance(phase_plan, ObligationPhasePlan)
                else ObligationPhasePlan.from_dict(phase_plan)
            )
            if (
                plan.problem_revision_id != revision_id
                or plan.problem_revision_fingerprint != revision_fingerprint
            ):
                raise ValueError(
                    "epistemic debt projection requires the exact obligation-phase ProblemRevision"
                )
            validate_obligation_phase_plan(state, plan)
            phases = {binding.obligation_id: binding.phase for binding in plan.bindings}

        items: list[EpistemicDebtItem] = []
        for obligation_id, row in sorted((state.get("obligations") or {}).items()):
            status = str(row.get("status") or "AVAILABLE").upper()
            if status in SATISFIED_OBLIGATION_STATUSES:
                continue
            classification = (
                "TERMINAL_UNRESOLVED"
                if status in TERMINAL_UNRESOLVED_STATUSES
                else "OUTSTANDING"
            )
            diagnostic = (
                f"TERMINAL_UNRESOLVED:{status}"
                if classification == "TERMINAL_UNRESOLVED"
                else f"OUTSTANDING_STATUS:{status}"
            )
            items.append(
                EpistemicDebtItem(
                    obligation_id=obligation_id,
                    obligation_semantic_fingerprint=obligation_semantic_fingerprint(row),
                    obligation_status=status,
                    classification=classification,
                    statement=str(row.get("statement") or ""),
                    dependency_obligation_ids=tuple(row.get("dependencies") or ()),
                    required_evidence_types=tuple(
                        row.get("required_evidence_types") or ()
                    ),
                    attached_evidence_ids=tuple(row.get("evidence_ids") or ()),
                    mandatory=bool(row.get("mandatory", True)),
                    persistent=bool(row.get("persistent", True)),
                    scope_id=scope_id_from(row),
                    phase=phases.get(obligation_id, ""),
                    diagnostics=(diagnostic,),
                )
            )
        return EpistemicDebtProjection(
            problem_revision_id=revision_id,
            problem_revision_fingerprint=revision_fingerprint,
            calculus_state_fingerprint=content_hash(state),
            items=tuple(items),
            metadata=dict(metadata or {}),
        )


    def validate_epistemic_debt_projection(
        calculus_state: Mapping[str, Any],
        projection: EpistemicDebtProjection | Mapping[str, Any],
        *,
        phase_plan: ObligationPhasePlan | Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        item = (
            projection
            if isinstance(projection, EpistemicDebtProjection)
            else EpistemicDebtProjection.from_dict(projection)
        )
        expected = project_epistemic_debt(
            calculus_state,
            problem_revision_id=item.problem_revision_id,
            problem_revision_fingerprint=item.problem_revision_fingerprint,
            phase_plan=phase_plan,
            metadata=item.metadata,
        )
        if item != expected:
            raise ValueError(
                "epistemic debt projection is stale or mismatched for the exact existing obligation graph"
            )
        return {
            "valid": True,
            "projection_id": item.projection_id,
            "projection_fingerprint": item.fingerprint,
            "calculus_state_fingerprint": item.calculus_state_fingerprint,
            "total_debt_count": len(item.items),
            "outstanding_count": item.outstanding_count,
            "terminal_unresolved_count": item.terminal_unresolved_count,
            "obligation_store": "EXISTING_AASM_CALCULUS_V1_ONLY",
            "runtime_admission": "PRE_ADMISSION_ONLY",
        }


    __all__ = [
        "EPISTEMIC_DEBT_CONTRACT_ID",
        "EPISTEMIC_DEBT_CONTRACT_VERSION",
        "EPISTEMIC_DEBT_STABILITY",
        "EPISTEMIC_DEBT_CLASSES",
        "SATISFIED_OBLIGATION_STATUSES",
        "TERMINAL_UNRESOLVED_STATUSES",
        "EpistemicDebtItem",
        "EpistemicDebtProjection",
        "project_epistemic_debt",
        "validate_epistemic_debt_projection",
    ]
    ''',
)

write(
    "src/aasm/_manual_override.py",
    r'''
    from __future__ import annotations

    from copy import deepcopy
    from dataclasses import dataclass, field
    import re
    from typing import Any, Mapping, Sequence

    from .calculus import OBLIGATION_STATUSES, normalize_calculus_state
    from .obligation_phase import obligation_semantic_fingerprint
    from .risk_irreversibility import RiskAssessment
    from .rule import EngineeringRule, RuleSourceAuthorityRef
    from .semantic_result import semantic_fingerprint


    MANUAL_OVERRIDE_CONTRACT_ID = "aasm.manual.override.v1"
    MANUAL_OVERRIDE_CONTRACT_VERSION = "0.1.0"
    MANUAL_OVERRIDE_ASSESSMENT_CONTRACT_ID = "aasm.manual.override.assessment.v1"
    MANUAL_OVERRIDE_ASSESSMENT_CONTRACT_VERSION = "0.1.0"
    MANUAL_OVERRIDE_STABILITY = "FOUNDATION_EXPERIMENTAL"
    MANUAL_OVERRIDE_ASSESSMENT_STATUSES = (
        "ADMISSIBLE_FOR_AUTHORIZATION_REVIEW",
        "BLOCKED_HARD_FLOOR",
        "BLOCKED_RULE_POLICY",
        "BLOCKED_AUTHORITY_REFERENCE",
        "BLOCKED_ACCEPTED_RISK",
        "BLOCKED_RESULTING_OBLIGATIONS",
        "OUTSIDE_VALIDITY_WINDOW",
    )
    SATISFIED_OBLIGATION_STATUSES = ("VERIFIED", "COMMITTED")
    TERMINAL_OBLIGATION_STATUSES = ("REJECTED", "SUPERSEDED", "IMPOSSIBLE")

    _SHA256 = re.compile(r"^[0-9a-f]{64}$")


    def _required(name: str, value: Any) -> str:
        text = str(value).strip()
        if not text:
            raise ValueError(f"manual-override {name} is required")
        return text


    def _optional(value: Any) -> str:
        return "" if value is None else str(value).strip()


    def _sha256(name: str, value: Any) -> str:
        text = _required(name, value).lower()
        if not _SHA256.fullmatch(text):
            raise ValueError(
                f"manual-override {name} must be a lowercase 64-hex SHA-256 digest"
            )
        return text


    def _uniq(values: Sequence[Any], *, name: str) -> tuple[str, ...]:
        return tuple(sorted({_required(name, value) for value in values}))


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
            raise TypeError(
                "binary floating-point values are forbidden in manual-override portable identity"
            )
        if isinstance(value, (str, int, bool)) or value is None:
            return value
        raise TypeError(f"manual-override value is not JSON serializable: {type(value)!r}")


    @dataclass(frozen=True)
    class OverrideValidityWindow:
        clock_id: str
        not_before_sequence: int
        not_after_sequence: int

        def __post_init__(self) -> None:
            clock_id = _required("validity clock_id", self.clock_id)
            for name in ("not_before_sequence", "not_after_sequence"):
                value = getattr(self, name)
                if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                    raise ValueError(
                        f"manual override {name} must be an exact non-negative integer"
                    )
            if self.not_after_sequence <= self.not_before_sequence:
                raise ValueError(
                    "manual override not_after_sequence must be greater than not_before_sequence"
                )
            object.__setattr__(self, "clock_id", clock_id)

        def identity_payload(self) -> dict[str, Any]:
            return {
                "clock_id": self.clock_id,
                "not_before_sequence": self.not_before_sequence,
                "not_after_sequence": self.not_after_sequence,
            }

        @property
        def fingerprint(self) -> str:
            return semantic_fingerprint(self.identity_payload())

        def to_dict(self) -> dict[str, Any]:
            return {**self.identity_payload(), "fingerprint": self.fingerprint}

        @classmethod
        def from_dict(cls, value: Mapping[str, Any]) -> "OverrideValidityWindow":
            payload = dict(value)
            supplied = str(payload.pop("fingerprint", "")).strip()
            item = cls(**payload)
            if supplied and supplied != item.fingerprint:
                raise ValueError("manual override validity-window fingerprint mismatch")
            return item


    @dataclass(frozen=True)
    class ResultingObligationRef:
        obligation_id: str
        obligation_semantic_fingerprint: str

        def __post_init__(self) -> None:
            object.__setattr__(
                self,
                "obligation_id",
                _required("resulting obligation_id", self.obligation_id),
            )
            object.__setattr__(
                self,
                "obligation_semantic_fingerprint",
                _sha256(
                    "resulting obligation_semantic_fingerprint",
                    self.obligation_semantic_fingerprint,
                ),
            )

        def identity_payload(self) -> dict[str, str]:
            return {
                "obligation_id": self.obligation_id,
                "obligation_semantic_fingerprint": self.obligation_semantic_fingerprint,
            }

        @property
        def fingerprint(self) -> str:
            return semantic_fingerprint(self.identity_payload())

        def to_dict(self) -> dict[str, str]:
            return {**self.identity_payload(), "fingerprint": self.fingerprint}

        @classmethod
        def from_dict(cls, value: Mapping[str, Any]) -> "ResultingObligationRef":
            payload = dict(value)
            supplied = str(payload.pop("fingerprint", "")).strip()
            item = cls(**payload)
            if supplied and supplied != item.fingerprint:
                raise ValueError("resulting obligation reference fingerprint mismatch")
            return item


    @dataclass(frozen=True)
    class ManualOverride:
        principal_id: str
        rule_revision_id: str
        rule_fingerprint: str
        rule_id: str
        reason: str
        workspace_id: str
        scope_id: str
        scope_selector_fingerprint: str
        problem_revision_id: str
        problem_revision_fingerprint: str
        validity: OverrideValidityWindow | Mapping[str, Any]
        accepted_risk_assessment_id: str
        accepted_risk_assessment_fingerprint: str
        accepted_hazard_ids: tuple[str, ...]
        authority: RuleSourceAuthorityRef | Mapping[str, Any]
        authority_evidence_ids: tuple[str, ...]
        resulting_obligations: tuple[ResultingObligationRef | Mapping[str, Any], ...]
        evidence_ids: tuple[str, ...] = ()
        metadata: Mapping[str, Any] = field(default_factory=dict)
        override_id: str = ""
        contract_id: str = MANUAL_OVERRIDE_CONTRACT_ID
        contract_version: str = MANUAL_OVERRIDE_CONTRACT_VERSION

        def __post_init__(self) -> None:
            if (
                self.contract_id != MANUAL_OVERRIDE_CONTRACT_ID
                or self.contract_version != MANUAL_OVERRIDE_CONTRACT_VERSION
            ):
                raise ValueError("unsupported manual-override contract")
            principal_id = _required("principal_id", self.principal_id)
            rule_revision_id = _required("rule_revision_id", self.rule_revision_id)
            rule_fingerprint = _sha256("rule_fingerprint", self.rule_fingerprint)
            rule_id = _required("rule_id", self.rule_id)
            reason = _required("reason", self.reason)
            workspace_id = _required("workspace_id", self.workspace_id)
            scope_id = _optional(self.scope_id)
            selector_fingerprint = _sha256(
                "scope_selector_fingerprint",
                self.scope_selector_fingerprint,
            )
            revision_id = _required("problem_revision_id", self.problem_revision_id)
            revision_fingerprint = _sha256(
                "problem_revision_fingerprint",
                self.problem_revision_fingerprint,
            )
            validity = (
                self.validity
                if isinstance(self.validity, OverrideValidityWindow)
                else OverrideValidityWindow.from_dict(self.validity)
            )
            risk_id = _required(
                "accepted_risk_assessment_id",
                self.accepted_risk_assessment_id,
            )
            risk_fingerprint = _sha256(
                "accepted_risk_assessment_fingerprint",
                self.accepted_risk_assessment_fingerprint,
            )
            accepted_hazards = _uniq(
                self.accepted_hazard_ids,
                name="accepted hazard_id",
            )
            if not accepted_hazards:
                raise ValueError("manual override requires at least one explicitly accepted hazard")
            authority = (
                self.authority
                if isinstance(self.authority, RuleSourceAuthorityRef)
                else RuleSourceAuthorityRef.from_dict(self.authority)
            )
            if authority.principal_id != principal_id:
                raise ValueError(
                    "manual override principal_id must match its exact scoped-authority reference"
                )
            authority_evidence_ids = _uniq(
                self.authority_evidence_ids,
                name="authority evidence_id",
            )
            if not authority_evidence_ids:
                raise ValueError("manual override requires explicit authority evidence IDs")
            resulting = tuple(
                value
                if isinstance(value, ResultingObligationRef)
                else ResultingObligationRef.from_dict(value)
                for value in self.resulting_obligations
            )
            if not resulting:
                raise ValueError(
                    "manual override requires at least one resulting existing obligation reference"
                )
            ids = [value.obligation_id for value in resulting]
            if len(ids) != len(set(ids)):
                raise ValueError(
                    "manual override resulting obligation references must be unique"
                )
            resulting = tuple(sorted(resulting, key=lambda value: value.obligation_id))
            object.__setattr__(self, "principal_id", principal_id)
            object.__setattr__(self, "rule_revision_id", rule_revision_id)
            object.__setattr__(self, "rule_fingerprint", rule_fingerprint)
            object.__setattr__(self, "rule_id", rule_id)
            object.__setattr__(self, "reason", reason)
            object.__setattr__(self, "workspace_id", workspace_id)
            object.__setattr__(self, "scope_id", scope_id)
            object.__setattr__(
                self,
                "scope_selector_fingerprint",
                selector_fingerprint,
            )
            object.__setattr__(self, "problem_revision_id", revision_id)
            object.__setattr__(
                self,
                "problem_revision_fingerprint",
                revision_fingerprint,
            )
            object.__setattr__(self, "validity", validity)
            object.__setattr__(self, "accepted_risk_assessment_id", risk_id)
            object.__setattr__(
                self,
                "accepted_risk_assessment_fingerprint",
                risk_fingerprint,
            )
            object.__setattr__(self, "accepted_hazard_ids", accepted_hazards)
            object.__setattr__(self, "authority", authority)
            object.__setattr__(
                self,
                "authority_evidence_ids",
                authority_evidence_ids,
            )
            object.__setattr__(self, "resulting_obligations", resulting)
            object.__setattr__(
                self,
                "evidence_ids",
                _uniq(self.evidence_ids, name="override evidence_id"),
            )
            object.__setattr__(self, "metadata", _jsonable(dict(self.metadata)))
            derived = f"manual-override-{semantic_fingerprint(self.identity_payload())[:24]}"
            supplied = _optional(self.override_id)
            if supplied and supplied != derived:
                raise ValueError("manual override_id does not match canonical identity")
            object.__setattr__(self, "override_id", derived)

        def identity_payload(self) -> dict[str, Any]:
            return {
                "contract_id": self.contract_id,
                "contract_version": self.contract_version,
                "principal_id": self.principal_id,
                "rule_revision_id": self.rule_revision_id,
                "rule_fingerprint": self.rule_fingerprint,
                "rule_id": self.rule_id,
                "reason": self.reason,
                "workspace_id": self.workspace_id,
                "scope_id": self.scope_id,
                "scope_selector_fingerprint": self.scope_selector_fingerprint,
                "problem_revision_id": self.problem_revision_id,
                "problem_revision_fingerprint": self.problem_revision_fingerprint,
                "validity": self.validity.identity_payload(),
                "accepted_risk_assessment_id": self.accepted_risk_assessment_id,
                "accepted_risk_assessment_fingerprint": self.accepted_risk_assessment_fingerprint,
                "accepted_hazard_ids": list(self.accepted_hazard_ids),
                "authority": self.authority.identity_payload(),
                "authority_evidence_ids": list(self.authority_evidence_ids),
                "resulting_obligations": [
                    value.identity_payload() for value in self.resulting_obligations
                ],
                "evidence_ids": list(self.evidence_ids),
                "metadata": _jsonable(self.metadata),
            }

        @property
        def fingerprint(self) -> str:
            return semantic_fingerprint(
                {"override_id": self.override_id, **self.identity_payload()}
            )

        def to_dict(self) -> dict[str, Any]:
            return {
                "override_id": self.override_id,
                "contract_id": self.contract_id,
                "contract_version": self.contract_version,
                "principal_id": self.principal_id,
                "rule_revision_id": self.rule_revision_id,
                "rule_fingerprint": self.rule_fingerprint,
                "rule_id": self.rule_id,
                "reason": self.reason,
                "workspace_id": self.workspace_id,
                "scope_id": self.scope_id,
                "scope_selector_fingerprint": self.scope_selector_fingerprint,
                "problem_revision_id": self.problem_revision_id,
                "problem_revision_fingerprint": self.problem_revision_fingerprint,
                "validity": self.validity.to_dict(),
                "accepted_risk_assessment_id": self.accepted_risk_assessment_id,
                "accepted_risk_assessment_fingerprint": self.accepted_risk_assessment_fingerprint,
                "accepted_hazard_ids": list(self.accepted_hazard_ids),
                "authority": self.authority.identity_payload(),
                "authority_evidence_ids": list(self.authority_evidence_ids),
                "resulting_obligations": [
                    value.to_dict() for value in self.resulting_obligations
                ],
                "evidence_ids": list(self.evidence_ids),
                "metadata": _jsonable(self.metadata),
                "fingerprint": self.fingerprint,
            }

        @classmethod
        def from_dict(cls, value: Mapping[str, Any]) -> "ManualOverride":
            payload = deepcopy(dict(value))
            supplied = str(payload.pop("fingerprint", "")).strip()
            payload["accepted_hazard_ids"] = tuple(
                payload.get("accepted_hazard_ids") or ()
            )
            payload["authority_evidence_ids"] = tuple(
                payload.get("authority_evidence_ids") or ()
            )
            payload["resulting_obligations"] = tuple(
                payload.get("resulting_obligations") or ()
            )
            payload["evidence_ids"] = tuple(payload.get("evidence_ids") or ())
            item = cls(**payload)
            if supplied and supplied != item.fingerprint:
                raise ValueError("manual override fingerprint mismatch")
            return item


    @dataclass(frozen=True)
    class ManualOverrideAssessment:
        override_id: str
        override_fingerprint: str
        rule_revision_id: str
        rule_fingerprint: str
        accepted_risk_assessment_id: str
        accepted_risk_assessment_fingerprint: str
        status: str
        diagnostics: tuple[str, ...] = ()
        waiver_performed: bool = False
        rule_mutated: bool = False
        authority_granted: bool = False
        effect_authority_granted: bool = False
        obligation_mutated: bool = False
        history_deleted: bool = False
        current_override_activated: bool = False
        assessment_id: str = ""
        contract_id: str = MANUAL_OVERRIDE_ASSESSMENT_CONTRACT_ID
        contract_version: str = MANUAL_OVERRIDE_ASSESSMENT_CONTRACT_VERSION

        def __post_init__(self) -> None:
            if (
                self.contract_id != MANUAL_OVERRIDE_ASSESSMENT_CONTRACT_ID
                or self.contract_version
                != MANUAL_OVERRIDE_ASSESSMENT_CONTRACT_VERSION
            ):
                raise ValueError("unsupported manual-override assessment contract")
            for name in (
                "override_id",
                "rule_revision_id",
                "accepted_risk_assessment_id",
            ):
                object.__setattr__(self, name, _required(name, getattr(self, name)))
            for name in (
                "override_fingerprint",
                "rule_fingerprint",
                "accepted_risk_assessment_fingerprint",
            ):
                object.__setattr__(self, name, _sha256(name, getattr(self, name)))
            status = _required("assessment status", self.status).upper()
            if status not in MANUAL_OVERRIDE_ASSESSMENT_STATUSES:
                raise ValueError(f"unsupported manual override assessment status: {status}")
            for name in (
                "waiver_performed",
                "rule_mutated",
                "authority_granted",
                "effect_authority_granted",
                "obligation_mutated",
                "history_deleted",
                "current_override_activated",
            ):
                if bool(getattr(self, name)):
                    raise ValueError(f"manual override assessment cannot set {name}=True")
            object.__setattr__(self, "status", status)
            object.__setattr__(
                self,
                "diagnostics",
                _uniq(self.diagnostics, name="assessment diagnostic"),
            )
            derived = f"manual-override-assessment-{semantic_fingerprint(self.identity_payload())[:24]}"
            supplied = _optional(self.assessment_id)
            if supplied and supplied != derived:
                raise ValueError(
                    "manual override assessment_id does not match canonical identity"
                )
            object.__setattr__(self, "assessment_id", derived)

        def identity_payload(self) -> dict[str, Any]:
            return {
                "contract_id": self.contract_id,
                "contract_version": self.contract_version,
                "override_id": self.override_id,
                "override_fingerprint": self.override_fingerprint,
                "rule_revision_id": self.rule_revision_id,
                "rule_fingerprint": self.rule_fingerprint,
                "accepted_risk_assessment_id": self.accepted_risk_assessment_id,
                "accepted_risk_assessment_fingerprint": self.accepted_risk_assessment_fingerprint,
                "status": self.status,
                "diagnostics": list(self.diagnostics),
                "waiver_performed": False,
                "rule_mutated": False,
                "authority_granted": False,
                "effect_authority_granted": False,
                "obligation_mutated": False,
                "history_deleted": False,
                "current_override_activated": False,
            }

        @property
        def fingerprint(self) -> str:
            return semantic_fingerprint(
                {"assessment_id": self.assessment_id, **self.identity_payload()}
            )

        def to_dict(self) -> dict[str, Any]:
            return {
                "assessment_id": self.assessment_id,
                **self.identity_payload(),
                "fingerprint": self.fingerprint,
            }

        @classmethod
        def from_dict(cls, value: Mapping[str, Any]) -> "ManualOverrideAssessment":
            payload = deepcopy(dict(value))
            supplied = str(payload.pop("fingerprint", "")).strip()
            payload["diagnostics"] = tuple(payload.get("diagnostics") or ())
            item = cls(**payload)
            if supplied and supplied != item.fingerprint:
                raise ValueError("manual override assessment fingerprint mismatch")
            return item


    def bind_manual_override(
        rule: EngineeringRule,
        risk_assessment: RiskAssessment,
        obligations: Sequence[Mapping[str, Any]],
        *,
        principal_id: str,
        authority: RuleSourceAuthorityRef,
        reason: str,
        validity: OverrideValidityWindow,
        problem_revision_id: str,
        problem_revision_fingerprint: str,
        authority_evidence_ids: Sequence[str],
        accepted_hazard_ids: Sequence[str] | None = None,
        evidence_ids: Sequence[str] = (),
        metadata: Mapping[str, Any] | None = None,
    ) -> ManualOverride:
        if not isinstance(rule, EngineeringRule):
            raise TypeError("bind_manual_override requires an exact EngineeringRule")
        if not isinstance(risk_assessment, RiskAssessment):
            raise TypeError("bind_manual_override requires an exact RiskAssessment")
        if not isinstance(authority, RuleSourceAuthorityRef):
            raise TypeError(
                "bind_manual_override requires an exact existing RuleSourceAuthorityRef"
            )
        if not isinstance(validity, OverrideValidityWindow):
            raise TypeError("bind_manual_override requires an explicit validity window")
        refs = tuple(
            ResultingObligationRef(
                obligation_id=str(row.get("obligation_id") or ""),
                obligation_semantic_fingerprint=obligation_semantic_fingerprint(row),
            )
            for row in obligations
        )
        return ManualOverride(
            principal_id=principal_id,
            rule_revision_id=rule.rule_revision_id,
            rule_fingerprint=rule.fingerprint,
            rule_id=rule.rule_id,
            reason=reason,
            workspace_id=rule.scope_selector.workspace_id,
            scope_id=rule.scope_selector.scope_id,
            scope_selector_fingerprint=rule.scope_selector.fingerprint,
            problem_revision_id=problem_revision_id,
            problem_revision_fingerprint=problem_revision_fingerprint,
            validity=validity,
            accepted_risk_assessment_id=risk_assessment.assessment_id,
            accepted_risk_assessment_fingerprint=risk_assessment.fingerprint,
            accepted_hazard_ids=tuple(
                risk_assessment.acceptance_hazard_ids
                if accepted_hazard_ids is None
                else accepted_hazard_ids
            ),
            authority=authority,
            authority_evidence_ids=tuple(authority_evidence_ids),
            resulting_obligations=refs,
            evidence_ids=tuple(evidence_ids),
            metadata=dict(metadata or {}),
        )


    def evaluate_manual_override(
        override: ManualOverride | Mapping[str, Any],
        rules: Sequence[EngineeringRule],
        risk_assessments: Sequence[RiskAssessment],
        calculus_state: Mapping[str, Any],
        *,
        clock_id: str,
        sequence: int,
    ) -> ManualOverrideAssessment:
        item = (
            override
            if isinstance(override, ManualOverride)
            else ManualOverride.from_dict(override)
        )
        if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 0:
            raise ValueError("manual override evaluation sequence must be non-negative")
        current_clock = _required("evaluation clock_id", clock_id)
        rule_rows = tuple(rules)
        if any(not isinstance(rule, EngineeringRule) for rule in rule_rows):
            raise TypeError("manual override evaluation requires exact EngineeringRule objects")
        rules_by_id = {rule.rule_revision_id: rule for rule in rule_rows}
        if len(rules_by_id) != len(rule_rows):
            raise ValueError("manual override evaluation rules must have unique identities")
        rule = rules_by_id.get(item.rule_revision_id)
        if rule is None or rule.fingerprint != item.rule_fingerprint:
            raise ValueError("manual override does not bind an exact supplied EngineeringRule")
        if rule.rule_id != item.rule_id:
            raise ValueError("manual override rule_id mismatch")
        if (
            rule.scope_selector.workspace_id != item.workspace_id
            or rule.scope_selector.scope_id != item.scope_id
            or rule.scope_selector.fingerprint != item.scope_selector_fingerprint
        ):
            raise ValueError("manual override scope does not match the exact Rule scope selector")
        if rule.problem_revision_id and (
            rule.problem_revision_id != item.problem_revision_id
            or rule.problem_revision_fingerprint
            != item.problem_revision_fingerprint
        ):
            raise ValueError("manual override EngineeringRule ProblemRevision mismatch")

        risk_rows = tuple(risk_assessments)
        if any(not isinstance(value, RiskAssessment) for value in risk_rows):
            raise TypeError("manual override evaluation requires exact RiskAssessment objects")
        risks_by_id = {value.assessment_id: value for value in risk_rows}
        if len(risks_by_id) != len(risk_rows):
            raise ValueError("manual override risk assessments must have unique identities")
        risk = risks_by_id.get(item.accepted_risk_assessment_id)
        if (
            risk is None
            or risk.fingerprint != item.accepted_risk_assessment_fingerprint
        ):
            raise ValueError("manual override does not bind an exact supplied RiskAssessment")

        state = normalize_calculus_state(deepcopy(dict(calculus_state)))
        obligations = dict(state.get("obligations") or {})
        obligation_statuses: list[str] = []
        for reference in item.resulting_obligations:
            row = obligations.get(reference.obligation_id)
            if row is None:
                raise ValueError(
                    "manual override resulting obligation reference is absent from the existing calculus store"
                )
            if (
                obligation_semantic_fingerprint(row)
                != reference.obligation_semantic_fingerprint
            ):
                raise ValueError(
                    "manual override resulting obligation reference is stale or mismatched"
                )
            status = str(row.get("status") or "AVAILABLE").upper()
            if status not in OBLIGATION_STATUSES:
                raise ValueError("manual override encountered unsupported obligation status")
            obligation_statuses.append(status)

        diagnostics: list[str] = []
        if rule.strength == "HARD_FLOOR":
            status = "BLOCKED_HARD_FLOOR"
            diagnostics.append("HARD_FLOOR_RULE_CANNOT_BE_WAIVED_OR_OVERRIDDEN")
        elif rule.control_policy.waiver_mode != "EXPLICIT_AUTHORIZED":
            status = "BLOCKED_RULE_POLICY"
            diagnostics.append("RULE_WAIVER_MODE_IS_NOT_EXPLICIT_AUTHORIZED")
        elif item.authority.capability != rule.control_policy.required_capability:
            status = "BLOCKED_AUTHORITY_REFERENCE"
            diagnostics.append("AUTHORITY_CAPABILITY_DOES_NOT_MATCH_RULE_POLICY")
        elif (
            risk.status != "REQUIRES_EXPLICIT_ACCEPTANCE"
            or tuple(item.accepted_hazard_ids) != tuple(risk.acceptance_hazard_ids)
            or bool(risk.blocking_hazard_ids)
            or bool(risk.mitigation_hazard_ids)
        ):
            status = "BLOCKED_ACCEPTED_RISK"
            diagnostics.append("RISK_ASSESSMENT_IS_NOT_EXACTLY_ACCEPTABLE_BY_MANUAL_OVERRIDE")
        elif any(
            value in SATISFIED_OBLIGATION_STATUSES + TERMINAL_OBLIGATION_STATUSES
            for value in obligation_statuses
        ):
            status = "BLOCKED_RESULTING_OBLIGATIONS"
            diagnostics.append(
                "RESULTING_OBLIGATIONS_MUST_BE_EXISTING_OUTSTANDING_NONTERMINAL_OBLIGATIONS"
            )
        elif (
            current_clock != item.validity.clock_id
            or sequence < item.validity.not_before_sequence
            or sequence > item.validity.not_after_sequence
        ):
            status = "OUTSIDE_VALIDITY_WINDOW"
            diagnostics.append("EXPLICIT_VALIDITY_WINDOW_NOT_SATISFIED")
        else:
            status = "ADMISSIBLE_FOR_AUTHORIZATION_REVIEW"
            diagnostics.extend(
                (
                    "AUTHORITY_REFERENCE_REQUIRES_POINT_OF_USE_REVALIDATION",
                    "NO_WAIVER_OR_AUTHORIZATION_PERFORMED_BY_FOUNDATION",
                    "RESULTING_OBLIGATIONS_REMAIN_OWNED_BY_EXISTING_CALCULUS",
                )
            )
        return ManualOverrideAssessment(
            override_id=item.override_id,
            override_fingerprint=item.fingerprint,
            rule_revision_id=item.rule_revision_id,
            rule_fingerprint=item.rule_fingerprint,
            accepted_risk_assessment_id=item.accepted_risk_assessment_id,
            accepted_risk_assessment_fingerprint=item.accepted_risk_assessment_fingerprint,
            status=status,
            diagnostics=tuple(diagnostics),
        )


    __all__ = [
        "MANUAL_OVERRIDE_CONTRACT_ID",
        "MANUAL_OVERRIDE_CONTRACT_VERSION",
        "MANUAL_OVERRIDE_ASSESSMENT_CONTRACT_ID",
        "MANUAL_OVERRIDE_ASSESSMENT_CONTRACT_VERSION",
        "MANUAL_OVERRIDE_STABILITY",
        "MANUAL_OVERRIDE_ASSESSMENT_STATUSES",
        "OverrideValidityWindow",
        "ResultingObligationRef",
        "ManualOverride",
        "ManualOverrideAssessment",
        "bind_manual_override",
        "evaluate_manual_override",
    ]
    ''',
)

write(
    "src/aasm/epistemic_debt_manual_override.py",
    r'''
    from __future__ import annotations

    from typing import Any

    from ._epistemic_debt import (
        EPISTEMIC_DEBT_CLASSES,
        EPISTEMIC_DEBT_CONTRACT_ID,
        EPISTEMIC_DEBT_CONTRACT_VERSION,
        EPISTEMIC_DEBT_STABILITY,
        EpistemicDebtItem,
        EpistemicDebtProjection,
        project_epistemic_debt,
        validate_epistemic_debt_projection,
    )
    from ._manual_override import (
        MANUAL_OVERRIDE_ASSESSMENT_CONTRACT_ID,
        MANUAL_OVERRIDE_ASSESSMENT_CONTRACT_VERSION,
        MANUAL_OVERRIDE_ASSESSMENT_STATUSES,
        MANUAL_OVERRIDE_CONTRACT_ID,
        MANUAL_OVERRIDE_CONTRACT_VERSION,
        MANUAL_OVERRIDE_STABILITY,
        ManualOverride,
        ManualOverrideAssessment,
        OverrideValidityWindow,
        ResultingObligationRef,
        bind_manual_override,
        evaluate_manual_override,
    )


    def epistemic_debt_manual_override_contract() -> dict[str, Any]:
        return {
            "epistemic_debt_contract_id": EPISTEMIC_DEBT_CONTRACT_ID,
            "epistemic_debt_contract_version": EPISTEMIC_DEBT_CONTRACT_VERSION,
            "manual_override_contract_id": MANUAL_OVERRIDE_CONTRACT_ID,
            "manual_override_contract_version": MANUAL_OVERRIDE_CONTRACT_VERSION,
            "manual_override_assessment_contract_id": MANUAL_OVERRIDE_ASSESSMENT_CONTRACT_ID,
            "manual_override_assessment_contract_version": MANUAL_OVERRIDE_ASSESSMENT_CONTRACT_VERSION,
            "stability": EPISTEMIC_DEBT_STABILITY,
            "debt_source": "EXACT_EXISTING_AASM_CALCULUS_V1_OBLIGATIONS_AND_REQUIRES_EDGES_ONLY",
            "debt_graph": "NONE_SECONDARY_OR_PARALLEL",
            "debt_store": "NONE_SECONDARY_OR_PARALLEL",
            "debt_identity": "PROJECTION_OF_EXISTING_OBLIGATION_ID_AND_S4_7_SEMANTIC_FINGERPRINT",
            "debt_classes": list(EPISTEMIC_DEBT_CLASSES),
            "debt_scalar_score": "NONE",
            "debt_forgiveness": "NONE",
            "resource_scarcity_relation": "CANNOT_ERASE_OR_DOWNGRADE_EPISTEMIC_DEBT",
            "objective_relation": "CANNOT_OVERRIDE_OUTSTANDING_OR_TERMINAL_UNRESOLVED_OBLIGATIONS",
            "manual_override_target": "EXACT_EXISTING_AASM_RULE_V1_REVISION_AND_FINGERPRINT",
            "hard_floor_override": "FORBIDDEN_UNCONDITIONALLY",
            "rule_waiver_policy": "EXACT_RULE_CONTROL_POLICY_EXPLICIT_AUTHORIZED_REQUIRED",
            "authority_reference": "EXACT_EXISTING_SCOPED_AUTHORITY_REFERENCE_AND_EVIDENCE_ONLY_NOT_AUTHORITY_PROOF",
            "authority_revalidation": "REQUIRED_AT_POINT_OF_USE_BY_EXISTING_AUTHORITY_PLANE",
            "accepted_risk": "EXACT_EXISTING_RISK_ASSESSMENT_REQUIRES_EXPLICIT_ACCEPTANCE_ONLY",
            "duration": "EXPLICIT_CLOCK_ID_AND_BOUNDED_INTEGER_SEQUENCE_WINDOW_NO_HIDDEN_WALL_CLOCK",
            "resulting_obligations": "EXACT_EXISTING_CALCULUS_OBLIGATION_REFERENCES_ONLY_NO_SECOND_OBLIGATION_STORE",
            "append_only_history": "OVERRIDE_RECORD_NEVER_DELETES_OR_REWRITES_PRIOR_HISTORY",
            "assessment_is_waiver": False,
            "assessment_is_authorization": False,
            "assessment_grants_effect_authority": False,
            "assessment_mutates_rule": False,
            "assessment_mutates_obligation": False,
            "assessment_activates_current_override": False,
            "parallel_override_registry": "NONE",
            "current_override_pointer": "NONE",
            "parallel_authority_evaluator": "NONE",
            "parallel_risk_plane": "NONE",
            "runtime_admission": "PRE_ADMISSION_ONLY",
            "public_admission": "PRE_ADMISSION_ONLY",
        }


    __all__ = [
        "EPISTEMIC_DEBT_CONTRACT_ID",
        "EPISTEMIC_DEBT_CONTRACT_VERSION",
        "EPISTEMIC_DEBT_STABILITY",
        "EPISTEMIC_DEBT_CLASSES",
        "MANUAL_OVERRIDE_CONTRACT_ID",
        "MANUAL_OVERRIDE_CONTRACT_VERSION",
        "MANUAL_OVERRIDE_ASSESSMENT_CONTRACT_ID",
        "MANUAL_OVERRIDE_ASSESSMENT_CONTRACT_VERSION",
        "MANUAL_OVERRIDE_STABILITY",
        "MANUAL_OVERRIDE_ASSESSMENT_STATUSES",
        "EpistemicDebtItem",
        "EpistemicDebtProjection",
        "OverrideValidityWindow",
        "ResultingObligationRef",
        "ManualOverride",
        "ManualOverrideAssessment",
        "project_epistemic_debt",
        "validate_epistemic_debt_projection",
        "bind_manual_override",
        "evaluate_manual_override",
        "epistemic_debt_manual_override_contract",
    ]
    ''',
)

write(
    "schemas/epistemic-debt.schema.json",
    r'''
    {
      "$schema": "https://json-schema.org/draft/2020-12/schema",
      "$id": "https://aasm.dev/schemas/epistemic-debt.schema.json",
      "title": "AASM Epistemic Debt Projection v1",
      "type": "object",
      "additionalProperties": false,
      "required": [
        "projection_id", "contract_id", "contract_version",
        "problem_revision_id", "problem_revision_fingerprint",
        "calculus_state_fingerprint", "items", "total_debt_count",
        "outstanding_count", "terminal_unresolved_count", "metadata", "fingerprint"
      ],
      "properties": {
        "projection_id": {"type": "string", "pattern": "^epistemic-debt-[0-9a-f]{24}$"},
        "contract_id": {"const": "aasm.epistemic.debt.v1"},
        "contract_version": {"const": "0.1.0"},
        "problem_revision_id": {"type": "string", "minLength": 1},
        "problem_revision_fingerprint": {"$ref": "#/$defs/sha256"},
        "calculus_state_fingerprint": {"$ref": "#/$defs/sha256"},
        "items": {"type": "array", "items": {"$ref": "#/$defs/debtItem"}},
        "total_debt_count": {"type": "integer", "minimum": 0},
        "outstanding_count": {"type": "integer", "minimum": 0},
        "terminal_unresolved_count": {"type": "integer", "minimum": 0},
        "metadata": {"$ref": "#/$defs/portableObject"},
        "fingerprint": {"$ref": "#/$defs/sha256"}
      },
      "$defs": {
        "sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
        "uniqueStrings": {"type": "array", "items": {"type": "string", "minLength": 1}, "uniqueItems": true},
        "portableValue": {"oneOf": [{"type": "null"}, {"type": "boolean"}, {"type": "string"}, {"type": "integer"}, {"type": "array", "items": {"$ref": "#/$defs/portableValue"}}, {"$ref": "#/$defs/portableObject"}]},
        "portableObject": {"type": "object", "additionalProperties": {"$ref": "#/$defs/portableValue"}},
        "debtItem": {
          "type": "object",
          "additionalProperties": false,
          "required": [
            "item_id", "obligation_id", "obligation_semantic_fingerprint",
            "obligation_status", "classification", "statement",
            "dependency_obligation_ids", "required_evidence_types",
            "attached_evidence_ids", "mandatory", "persistent", "scope_id",
            "phase", "diagnostics", "fingerprint"
          ],
          "properties": {
            "item_id": {"type": "string", "pattern": "^epistemic-debt-item-[0-9a-f]{24}$"},
            "obligation_id": {"type": "string", "minLength": 1},
            "obligation_semantic_fingerprint": {"$ref": "#/$defs/sha256"},
            "obligation_status": {"enum": ["AVAILABLE", "ENABLED", "IN_PROGRESS", "VERIFYING", "BLOCKED", "LOCKED", "NEEDS_REVALIDATION", "REJECTED", "SUPERSEDED", "IMPOSSIBLE"]},
            "classification": {"enum": ["OUTSTANDING", "TERMINAL_UNRESOLVED"]},
            "statement": {"type": "string", "minLength": 1},
            "dependency_obligation_ids": {"$ref": "#/$defs/uniqueStrings"},
            "required_evidence_types": {"$ref": "#/$defs/uniqueStrings"},
            "attached_evidence_ids": {"$ref": "#/$defs/uniqueStrings"},
            "mandatory": {"type": "boolean"},
            "persistent": {"type": "boolean"},
            "scope_id": {"type": "string", "minLength": 1},
            "phase": {"enum": ["", "PRE_AUTHORIZE", "PRE_DISPATCH", "POST_DISPATCH", "POST_OBSERVE", "POST_VERIFY", "RECOVERY"]},
            "diagnostics": {"$ref": "#/$defs/uniqueStrings"},
            "fingerprint": {"$ref": "#/$defs/sha256"}
          }
        }
      }
    }
    ''',
)

write(
    "schemas/manual-override.schema.json",
    r'''
    {
      "$schema": "https://json-schema.org/draft/2020-12/schema",
      "$id": "https://aasm.dev/schemas/manual-override.schema.json",
      "title": "AASM Manual Override v1",
      "type": "object",
      "additionalProperties": false,
      "required": [
        "override_id", "contract_id", "contract_version", "principal_id",
        "rule_revision_id", "rule_fingerprint", "rule_id", "reason",
        "workspace_id", "scope_id", "scope_selector_fingerprint",
        "problem_revision_id", "problem_revision_fingerprint", "validity",
        "accepted_risk_assessment_id", "accepted_risk_assessment_fingerprint",
        "accepted_hazard_ids", "authority", "authority_evidence_ids",
        "resulting_obligations", "evidence_ids", "metadata", "fingerprint"
      ],
      "properties": {
        "override_id": {"type": "string", "pattern": "^manual-override-[0-9a-f]{24}$"},
        "contract_id": {"const": "aasm.manual.override.v1"},
        "contract_version": {"const": "0.1.0"},
        "principal_id": {"type": "string", "minLength": 1},
        "rule_revision_id": {"type": "string", "minLength": 1},
        "rule_fingerprint": {"$ref": "#/$defs/sha256"},
        "rule_id": {"type": "string", "minLength": 1},
        "reason": {"type": "string", "minLength": 1},
        "workspace_id": {"type": "string", "minLength": 1},
        "scope_id": {"type": "string"},
        "scope_selector_fingerprint": {"$ref": "#/$defs/sha256"},
        "problem_revision_id": {"type": "string", "minLength": 1},
        "problem_revision_fingerprint": {"$ref": "#/$defs/sha256"},
        "validity": {"$ref": "#/$defs/validityWindow"},
        "accepted_risk_assessment_id": {"type": "string", "minLength": 1},
        "accepted_risk_assessment_fingerprint": {"$ref": "#/$defs/sha256"},
        "accepted_hazard_ids": {"type": "array", "minItems": 1, "items": {"type": "string", "minLength": 1}, "uniqueItems": true},
        "authority": {"$ref": "#/$defs/authorityRef"},
        "authority_evidence_ids": {"type": "array", "minItems": 1, "items": {"type": "string", "minLength": 1}, "uniqueItems": true},
        "resulting_obligations": {"type": "array", "minItems": 1, "items": {"$ref": "#/$defs/obligationRef"}},
        "evidence_ids": {"$ref": "#/$defs/uniqueStrings"},
        "metadata": {"$ref": "#/$defs/portableObject"},
        "fingerprint": {"$ref": "#/$defs/sha256"}
      },
      "$defs": {
        "sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
        "uniqueStrings": {"type": "array", "items": {"type": "string", "minLength": 1}, "uniqueItems": true},
        "portableValue": {"oneOf": [{"type": "null"}, {"type": "boolean"}, {"type": "string"}, {"type": "integer"}, {"type": "array", "items": {"$ref": "#/$defs/portableValue"}}, {"$ref": "#/$defs/portableObject"}]},
        "portableObject": {"type": "object", "additionalProperties": {"$ref": "#/$defs/portableValue"}},
        "validityWindow": {
          "type": "object", "additionalProperties": false,
          "required": ["clock_id", "not_before_sequence", "not_after_sequence", "fingerprint"],
          "properties": {
            "clock_id": {"type": "string", "minLength": 1},
            "not_before_sequence": {"type": "integer", "minimum": 0},
            "not_after_sequence": {"type": "integer", "minimum": 1},
            "fingerprint": {"$ref": "#/$defs/sha256"}
          }
        },
        "authorityRef": {
          "type": "object", "additionalProperties": false,
          "required": ["principal_id", "authority_grant_id", "authority_grant_fingerprint", "capability"],
          "properties": {
            "principal_id": {"type": "string", "minLength": 1},
            "authority_grant_id": {"type": "string", "minLength": 1},
            "authority_grant_fingerprint": {"$ref": "#/$defs/sha256"},
            "capability": {"type": "string", "minLength": 1}
          }
        },
        "obligationRef": {
          "type": "object", "additionalProperties": false,
          "required": ["obligation_id", "obligation_semantic_fingerprint", "fingerprint"],
          "properties": {
            "obligation_id": {"type": "string", "minLength": 1},
            "obligation_semantic_fingerprint": {"$ref": "#/$defs/sha256"},
            "fingerprint": {"$ref": "#/$defs/sha256"}
          }
        }
      }
    }
    ''',
)

write(
    "schemas/manual-override-assessment.schema.json",
    r'''
    {
      "$schema": "https://json-schema.org/draft/2020-12/schema",
      "$id": "https://aasm.dev/schemas/manual-override-assessment.schema.json",
      "title": "AASM Manual Override Assessment v1",
      "type": "object",
      "additionalProperties": false,
      "required": [
        "assessment_id", "contract_id", "contract_version", "override_id",
        "override_fingerprint", "rule_revision_id", "rule_fingerprint",
        "accepted_risk_assessment_id", "accepted_risk_assessment_fingerprint",
        "status", "diagnostics", "waiver_performed", "rule_mutated",
        "authority_granted", "effect_authority_granted", "obligation_mutated",
        "history_deleted", "current_override_activated", "fingerprint"
      ],
      "properties": {
        "assessment_id": {"type": "string", "pattern": "^manual-override-assessment-[0-9a-f]{24}$"},
        "contract_id": {"const": "aasm.manual.override.assessment.v1"},
        "contract_version": {"const": "0.1.0"},
        "override_id": {"type": "string", "pattern": "^manual-override-[0-9a-f]{24}$"},
        "override_fingerprint": {"$ref": "#/$defs/sha256"},
        "rule_revision_id": {"type": "string", "minLength": 1},
        "rule_fingerprint": {"$ref": "#/$defs/sha256"},
        "accepted_risk_assessment_id": {"type": "string", "minLength": 1},
        "accepted_risk_assessment_fingerprint": {"$ref": "#/$defs/sha256"},
        "status": {"enum": ["ADMISSIBLE_FOR_AUTHORIZATION_REVIEW", "BLOCKED_HARD_FLOOR", "BLOCKED_RULE_POLICY", "BLOCKED_AUTHORITY_REFERENCE", "BLOCKED_ACCEPTED_RISK", "BLOCKED_RESULTING_OBLIGATIONS", "OUTSIDE_VALIDITY_WINDOW"]},
        "diagnostics": {"$ref": "#/$defs/uniqueStrings"},
        "waiver_performed": {"const": false},
        "rule_mutated": {"const": false},
        "authority_granted": {"const": false},
        "effect_authority_granted": {"const": false},
        "obligation_mutated": {"const": false},
        "history_deleted": {"const": false},
        "current_override_activated": {"const": false},
        "fingerprint": {"$ref": "#/$defs/sha256"}
      },
      "$defs": {
        "sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
        "uniqueStrings": {"type": "array", "items": {"type": "string", "minLength": 1}, "uniqueItems": true}
      }
    }
    ''',
)

write(
    "docs/implementation/EPISTEMIC_DEBT_MANUAL_OVERRIDE_FOUNDATION.md",
    r'''
    # S4.9 Epistemic Debt and Manual Override Foundation

    **Status:** implemented as a pre-admission semantic foundation  
    **Contracts:** `aasm.epistemic.debt.v1`, `aasm.manual.override.v1`, `aasm.manual.override.assessment.v1`  
    **Runtime/public admission:** `PRE_ADMISSION_ONLY`

    ## Purpose

    S4.9 makes unresolved engineering knowledge and exceptional human intervention explicit without creating a second truth, obligation, authority, risk, or waiver plane.

    Epistemic debt is a deterministic projection of the existing AASM calculus obligation graph. A manual override is an immutable, scope-bound, duration-bound record that references an exact existing Rule, RiskAssessment, scoped-authority reference, evidence, and resulting existing obligations. Neither object performs an override.

    ## Epistemic debt

    `EpistemicDebtProjection` is regenerated from the exact existing `aasm.calculus.v1` state. It preserves:

    - existing `obligation_id` identity;
    - the S4.7 obligation semantic fingerprint;
    - the existing status machine;
    - exact `REQUIRES` dependencies;
    - required and attached evidence references;
    - mandatory/persistent flags and scope;
    - optional S4.7 phase bindings;
    - exact ProblemRevision and calculus-state fingerprints.

    `VERIFIED` and `COMMITTED` obligations are absent from debt. Other live states are `OUTSTANDING`; `REJECTED`, `SUPERSEDED`, and `IMPOSSIBLE` are retained as `TERMINAL_UNRESOLVED` rather than disappearing from the knowledge record.

    Debt has no scalar score, forgiveness switch, resource-cost collapse, hidden registry, or independent lifecycle. Resource scarcity and objective improvement cannot erase it.

    ## Manual override

    A `ManualOverride` records:

    - principal identity;
    - exact Rule revision, fingerprint, and scope selector;
    - explicit reason;
    - exact ProblemRevision;
    - explicit logical clock and bounded integer sequence window;
    - exact accepted RiskAssessment and hazard IDs;
    - exact existing scoped-authority reference and evidence IDs;
    - exact resulting existing obligation IDs and S4.7 semantic fingerprints;
    - additional Evidence references and portable metadata.

    `HARD_FLOOR` rules are unconditionally non-overridable. Other rules require their existing `RuleControlPolicy.waiver_mode` to be `EXPLICIT_AUTHORIZED`, and the supplied authority capability must exactly match the Rule policy. Accepted risk must be an exact `REQUIRES_EXPLICIT_ACCEPTANCE` assessment with no hard blocker or unresolved mitigation. Resulting obligations must already exist in the canonical calculus store and remain outstanding and nonterminal.

    The assessment result `ADMISSIBLE_FOR_AUTHORIZATION_REVIEW` is deliberately not authorization. The existing authority plane must revalidate the grant at point of use, and any later effect must still traverse the existing Effect lifecycle and point-of-use authority checks.

    ## Claim ceiling

    S4.9 performs none of the following:

    - creates a second debt or obligation graph;
    - mutates obligation status or evidence;
    - waives, edits, deletes, or supersedes a Rule;
    - grants scoped or effect authority;
    - activates a current override;
    - dispatches an Effect;
    - deletes or rewrites history;
    - treats an authority reference as authority proof;
    - weakens a hard floor, evidence floor, or assurance requirement;
    - hides wall-clock semantics in durable identity.

    All records are immutable, revision-bound, deterministic, closed-schema, and binary-float-free. Later runtime admission must compose through the existing Rule, RiskAssessment, authority, calculus, Evidence, and Effect systems rather than bypassing them.
    ''',
)

write(
    "tests/test_epistemic_debt_manual_override_foundation.py",
    r'''
    from __future__ import annotations

    from copy import deepcopy
    import hashlib
    import json
    from pathlib import Path

    import pytest
    from jsonschema import Draft202012Validator, ValidationError, validate

    import aasm
    from aasm.calculus import ObligationRecord, default_calculus_state, normalize_calculus_state
    from aasm.epistemic_debt_manual_override import (
        EPISTEMIC_DEBT_CLASSES,
        MANUAL_OVERRIDE_ASSESSMENT_STATUSES,
        EpistemicDebtProjection,
        ManualOverride,
        ManualOverrideAssessment,
        OverrideValidityWindow,
        bind_manual_override,
        epistemic_debt_manual_override_contract,
        evaluate_manual_override,
        project_epistemic_debt,
        validate_epistemic_debt_projection,
    )
    from aasm.obligation_phase import ObligationPhasePlan, bind_obligation_phase
    from aasm.risk_irreversibility import RiskAssessment
    from aasm.rule import (
        EngineeringRule,
        RuleApplicabilityPredicate,
        RuleClauseRef,
        RuleControlPolicy,
        RuleScopeSelector,
        RuleSourceAuthorityRef,
    )


    ROOT = Path(__file__).resolve().parents[1]
    REVISION_ID = "problem-revision-s4-9"
    REVISION_FINGERPRINT = "9" * 64


    def obligation(
        obligation_id: str,
        *,
        status: str = "AVAILABLE",
        dependencies: tuple[str, ...] = (),
        required_evidence_types: tuple[str, ...] = (),
    ) -> ObligationRecord:
        return ObligationRecord(
            obligation_id,
            f"Obligation {obligation_id}",
            status=status,
            dependencies=list(dependencies),
            required_evidence_types=list(required_evidence_types),
            scope={"scope_id": "control"},
        )


    def state_with(*records: ObligationRecord) -> dict:
        state = default_calculus_state()
        for record in records:
            state["obligations"][record.obligation_id] = record.to_dict()
            for dependency in record.dependencies:
                state["obligation_edges"].append(
                    {"src": dependency, "dst": record.obligation_id, "relation": "REQUIRES"}
                )
        return normalize_calculus_state(state)


    def plan_for(state: dict, phases: dict[str, str]) -> ObligationPhasePlan:
        return ObligationPhasePlan(
            REVISION_ID,
            REVISION_FINGERPRINT,
            tuple(
                bind_obligation_phase(
                    state["obligations"][obligation_id],
                    phase,
                    problem_revision_id=REVISION_ID,
                    problem_revision_fingerprint=REVISION_FINGERPRINT,
                )
                for obligation_id, phase in sorted(phases.items())
            ),
        )


    def rule(*, strength: str = "POLICY", waivable: bool = True) -> EngineeringRule:
        clause_id = f"override-{strength}-{waivable}"
        control = (
            RuleControlPolicy("EXPLICIT_AUTHORIZED", "FORBIDDEN", "rule.waive")
            if waivable
            else RuleControlPolicy()
        )
        return EngineeringRule(
            "operator-policy",
            RuleClauseRef(
                "aasm.semantic.constraint.v1",
                clause_id,
                hashlib.sha256(clause_id.encode()).hexdigest(),
                "POLICY",
            ),
            strength,
            RuleScopeSelector("workspace-1", "control", "EXACT", ("actuator-1",)),
            RuleApplicabilityPredicate("ALWAYS"),
            "operator-policy",
            control_policy=control,
            severity="HIGH",
            problem_revision_id=REVISION_ID,
            problem_revision_fingerprint=REVISION_FINGERPRINT,
        )


    def risk(status: str = "REQUIRES_EXPLICIT_ACCEPTANCE") -> RiskAssessment:
        return RiskAssessment(
            envelope_id="risk-envelope-1",
            envelope_fingerprint="a" * 64,
            irreversibility_profile_id="irreversibility-profile-1",
            irreversibility_fingerprint="b" * 64,
            status=status,
            required_assurance_level="BASELINE",
            available_assurance_level="MAXIMUM",
            mitigation_hazard_ids=("guard",) if status == "REQUIRES_MITIGATION" else (),
            acceptance_hazard_ids=("operator-risk",)
            if status == "REQUIRES_EXPLICIT_ACCEPTANCE"
            else (),
        )


    def authority(capability: str = "rule.waive") -> RuleSourceAuthorityRef:
        return RuleSourceAuthorityRef(
            "principal-1",
            "authority-grant-1",
            "c" * 64,
            capability,
        )


    def override_for(
        state: dict,
        *,
        rule_obj: EngineeringRule | None = None,
        risk_obj: RiskAssessment | None = None,
        authority_obj: RuleSourceAuthorityRef | None = None,
        accepted_hazard_ids: tuple[str, ...] | None = None,
    ) -> tuple[ManualOverride, EngineeringRule, RiskAssessment]:
        rule_obj = rule_obj or rule()
        risk_obj = risk_obj or risk()
        authority_obj = authority_obj or authority()
        item = bind_manual_override(
            rule_obj,
            risk_obj,
            (state["obligations"]["O-review"],),
            principal_id="principal-1",
            authority=authority_obj,
            reason="Operator accepts the bounded policy exception for this revision",
            validity=OverrideValidityWindow("control-sequence", 10, 20),
            problem_revision_id=REVISION_ID,
            problem_revision_fingerprint=REVISION_FINGERPRINT,
            authority_evidence_ids=("evidence-authority",),
            accepted_hazard_ids=accepted_hazard_ids,
            evidence_ids=("evidence-override-request",),
        )
        return item, rule_obj, risk_obj


    def test_vocabularies_and_contract_claim_ceiling_are_exact():
        assert EPISTEMIC_DEBT_CLASSES == ("OUTSTANDING", "TERMINAL_UNRESOLVED")
        assert MANUAL_OVERRIDE_ASSESSMENT_STATUSES == (
            "ADMISSIBLE_FOR_AUTHORIZATION_REVIEW",
            "BLOCKED_HARD_FLOOR",
            "BLOCKED_RULE_POLICY",
            "BLOCKED_AUTHORITY_REFERENCE",
            "BLOCKED_ACCEPTED_RISK",
            "BLOCKED_RESULTING_OBLIGATIONS",
            "OUTSIDE_VALIDITY_WINDOW",
        )
        contract = epistemic_debt_manual_override_contract()
        assert contract["debt_graph"] == "NONE_SECONDARY_OR_PARALLEL"
        assert contract["debt_store"] == "NONE_SECONDARY_OR_PARALLEL"
        assert contract["debt_scalar_score"] == "NONE"
        assert contract["hard_floor_override"] == "FORBIDDEN_UNCONDITIONALLY"
        assert contract["assessment_is_waiver"] is False
        assert contract["assessment_is_authorization"] is False
        assert contract["assessment_mutates_rule"] is False
        assert contract["assessment_mutates_obligation"] is False
        assert contract["parallel_override_registry"] == "NONE"
        assert contract["current_override_pointer"] == "NONE"
        assert contract["runtime_admission"] == "PRE_ADMISSION_ONLY"
        assert contract["public_admission"] == "PRE_ADMISSION_ONLY"


    def test_debt_projection_uses_existing_obligations_edges_and_status_machine():
        state = state_with(
            obligation("O-evidence", required_evidence_types=("hardware-test",)),
            obligation("O-review", dependencies=("O-evidence",), status="BLOCKED"),
            obligation("O-done", status="VERIFIED"),
        )
        projection = project_epistemic_debt(
            state,
            problem_revision_id=REVISION_ID,
            problem_revision_fingerprint=REVISION_FINGERPRINT,
        )
        assert tuple(value.obligation_id for value in projection.items) == (
            "O-evidence",
            "O-review",
        )
        assert projection.outstanding_count == 2
        assert projection.terminal_unresolved_count == 0
        assert projection.items[1].dependency_obligation_ids == ("O-evidence",)
        assert validate_epistemic_debt_projection(state, projection)["valid"] is True
        assert EpistemicDebtProjection.from_dict(projection.to_dict()) == projection


    def test_debt_projection_preserves_optional_s4_7_phase_bindings():
        state = state_with(
            obligation("O-auth"),
            obligation("O-review", dependencies=("O-auth",)),
        )
        plan = plan_for(state, {"O-auth": "PRE_AUTHORIZE", "O-review": "POST_VERIFY"})
        projection = project_epistemic_debt(
            state,
            problem_revision_id=REVISION_ID,
            problem_revision_fingerprint=REVISION_FINGERPRINT,
            phase_plan=plan,
        )
        phases = {value.obligation_id: value.phase for value in projection.items}
        assert phases == {"O-auth": "PRE_AUTHORIZE", "O-review": "POST_VERIFY"}
        assert validate_epistemic_debt_projection(
            state,
            projection,
            phase_plan=plan,
        )["valid"] is True


    def test_terminal_obligations_remain_visible_as_unresolved_debt():
        for status in ("REJECTED", "SUPERSEDED", "IMPOSSIBLE"):
            state = state_with(obligation("O-terminal", status=status))
            projection = project_epistemic_debt(
                state,
                problem_revision_id=REVISION_ID,
                problem_revision_fingerprint=REVISION_FINGERPRINT,
            )
            assert projection.items[0].classification == "TERMINAL_UNRESOLVED"
            assert projection.terminal_unresolved_count == 1


    def test_verified_and_committed_obligations_clear_projection_without_mutation():
        for status in ("VERIFIED", "COMMITTED"):
            state = state_with(obligation("O-done", status=status))
            before = deepcopy(state)
            projection = project_epistemic_debt(
                state,
                problem_revision_id=REVISION_ID,
                problem_revision_fingerprint=REVISION_FINGERPRINT,
            )
            assert projection.items == ()
            assert projection.to_dict()["total_debt_count"] == 0
            assert state == before


    def test_stale_debt_projection_and_malformed_edge_projection_fail_closed():
        state = state_with(obligation("O-review"))
        projection = project_epistemic_debt(
            state,
            problem_revision_id=REVISION_ID,
            problem_revision_fingerprint=REVISION_FINGERPRINT,
        )
        changed = deepcopy(state)
        changed["obligations"]["O-review"]["statement"] = "Changed requirement"
        with pytest.raises(ValueError, match="stale or mismatched"):
            validate_epistemic_debt_projection(changed, projection)
        malformed = deepcopy(state)
        malformed["obligation_edges"] = [
            {"src": "O-review", "dst": "O-review", "relation": "REQUIRES"}
        ]
        with pytest.raises(ValueError, match="exactly represent"):
            project_epistemic_debt(
                malformed,
                problem_revision_id=REVISION_ID,
                problem_revision_fingerprint=REVISION_FINGERPRINT,
            )


    def test_manual_override_records_exact_required_bindings_and_round_trips():
        state = state_with(obligation("O-review"))
        item, _, _ = override_for(state)
        restored = ManualOverride.from_dict(item.to_dict())
        assert restored == item
        assert restored.principal_id == "principal-1"
        assert restored.workspace_id == "workspace-1"
        assert restored.scope_id == "control"
        assert restored.validity.clock_id == "control-sequence"
        assert restored.accepted_hazard_ids == ("operator-risk",)
        assert restored.authority_evidence_ids == ("evidence-authority",)
        assert restored.resulting_obligations[0].obligation_id == "O-review"


    def test_hard_floor_and_nonwaivable_rules_fail_closed():
        state = state_with(obligation("O-review"))
        hard = rule(strength="HARD_FLOOR", waivable=False)
        hard_override, _, risk_obj = override_for(state, rule_obj=hard)
        hard_result = evaluate_manual_override(
            hard_override,
            (hard,),
            (risk_obj,),
            state,
            clock_id="control-sequence",
            sequence=15,
        )
        assert hard_result.status == "BLOCKED_HARD_FLOOR"
        policy = rule(strength="POLICY", waivable=False)
        policy_override, _, risk_obj = override_for(state, rule_obj=policy)
        policy_result = evaluate_manual_override(
            policy_override,
            (policy,),
            (risk_obj,),
            state,
            clock_id="control-sequence",
            sequence=15,
        )
        assert policy_result.status == "BLOCKED_RULE_POLICY"


    def test_authority_capability_is_reference_only_and_must_match_rule_policy():
        state = state_with(obligation("O-review"))
        item, rule_obj, risk_obj = override_for(
            state,
            authority_obj=authority("different.capability"),
        )
        result = evaluate_manual_override(
            item,
            (rule_obj,),
            (risk_obj,),
            state,
            clock_id="control-sequence",
            sequence=15,
        )
        assert result.status == "BLOCKED_AUTHORITY_REFERENCE"
        assert result.authority_granted is False
        assert result.effect_authority_granted is False


    def test_only_exact_explicit_acceptance_risk_is_eligible():
        state = state_with(obligation("O-review"))
        mitigation = risk("REQUIRES_MITIGATION")
        item, rule_obj, _ = override_for(
            state,
            risk_obj=mitigation,
            accepted_hazard_ids=("operator-risk",),
        )
        result = evaluate_manual_override(
            item,
            (rule_obj,),
            (mitigation,),
            state,
            clock_id="control-sequence",
            sequence=15,
        )
        assert result.status == "BLOCKED_ACCEPTED_RISK"
        accepted = risk()
        changed = deepcopy(item.to_dict())
        changed["accepted_risk_assessment_id"] = accepted.assessment_id
        changed["accepted_risk_assessment_fingerprint"] = accepted.fingerprint
        changed["accepted_hazard_ids"] = ["wrong-hazard"]
        changed.pop("fingerprint")
        mismatch = ManualOverride.from_dict(changed)
        result = evaluate_manual_override(
            mismatch,
            (rule_obj,),
            (accepted,),
            state,
            clock_id="control-sequence",
            sequence=15,
        )
        assert result.status == "BLOCKED_ACCEPTED_RISK"


    def test_resulting_obligations_reuse_exact_existing_store_and_must_remain_open():
        state = state_with(obligation("O-review"))
        item, rule_obj, risk_obj = override_for(state)
        stale = deepcopy(state)
        stale["obligations"]["O-review"]["statement"] = "Different obligation"
        with pytest.raises(ValueError, match="stale or mismatched"):
            evaluate_manual_override(
                item,
                (rule_obj,),
                (risk_obj,),
                stale,
                clock_id="control-sequence",
                sequence=15,
            )
        verified = deepcopy(state)
        verified["obligations"]["O-review"]["status"] = "VERIFIED"
        result = evaluate_manual_override(
            item,
            (rule_obj,),
            (risk_obj,),
            verified,
            clock_id="control-sequence",
            sequence=15,
        )
        assert result.status == "BLOCKED_RESULTING_OBLIGATIONS"


    def test_validity_uses_explicit_clock_and_sequence_without_hidden_wall_clock():
        state = state_with(obligation("O-review"))
        item, rule_obj, risk_obj = override_for(state)
        for clock_id, sequence in (
            ("other-clock", 15),
            ("control-sequence", 9),
            ("control-sequence", 21),
        ):
            result = evaluate_manual_override(
                item,
                (rule_obj,),
                (risk_obj,),
                state,
                clock_id=clock_id,
                sequence=sequence,
            )
            assert result.status == "OUTSIDE_VALIDITY_WINDOW"
        assert OverrideValidityWindow("control-sequence", 10, 20).to_dict()[
            "not_after_sequence"
        ] == 20


    def test_admissible_assessment_remains_review_only_and_pure():
        state = state_with(obligation("O-review"))
        item, rule_obj, risk_obj = override_for(state)
        before = deepcopy(state)
        result = evaluate_manual_override(
            item,
            (rule_obj,),
            (risk_obj,),
            state,
            clock_id="control-sequence",
            sequence=15,
        )
        assert result.status == "ADMISSIBLE_FOR_AUTHORIZATION_REVIEW"
        assert state == before
        for name in (
            "waiver_performed",
            "rule_mutated",
            "authority_granted",
            "effect_authority_granted",
            "obligation_mutated",
            "history_deleted",
            "current_override_activated",
        ):
            assert getattr(result, name) is False
        assert ManualOverrideAssessment.from_dict(result.to_dict()) == result


    def test_override_resulting_obligation_remains_epistemic_debt_until_verified():
        state = state_with(obligation("O-review"))
        item, rule_obj, risk_obj = override_for(state)
        assert evaluate_manual_override(
            item,
            (rule_obj,),
            (risk_obj,),
            state,
            clock_id="control-sequence",
            sequence=15,
        ).status == "ADMISSIBLE_FOR_AUTHORIZATION_REVIEW"
        debt = project_epistemic_debt(
            state,
            problem_revision_id=REVISION_ID,
            problem_revision_fingerprint=REVISION_FINGERPRINT,
        )
        assert tuple(value.obligation_id for value in debt.items) == ("O-review",)
        verified = deepcopy(state)
        verified["obligations"]["O-review"]["status"] = "VERIFIED"
        assert project_epistemic_debt(
            verified,
            problem_revision_id=REVISION_ID,
            problem_revision_fingerprint=REVISION_FINGERPRINT,
        ).items == ()


    def test_binary_float_metadata_and_identity_tampering_fail_closed():
        state = state_with(obligation("O-review"))
        with pytest.raises(TypeError, match="binary floating-point"):
            project_epistemic_debt(
                state,
                problem_revision_id=REVISION_ID,
                problem_revision_fingerprint=REVISION_FINGERPRINT,
                metadata={"confidence": 0.9},
            )
        item, _, _ = override_for(state)
        changed = deepcopy(item.to_dict())
        changed["fingerprint"] = "0" * 64
        with pytest.raises(ValueError, match="fingerprint mismatch"):
            ManualOverride.from_dict(changed)


    def test_foundation_is_not_public_root_or_runtime_composition():
        assert not hasattr(aasm, "EpistemicDebtProjection")
        assert not hasattr(aasm, "ManualOverride")
        runtime_source = (ROOT / "src/aasm/runtime_v56_foundation.py").read_text(
            encoding="utf-8"
        )
        assert "from .epistemic_debt_manual_override" not in runtime_source
        assert "EpistemicDebtProjection" not in runtime_source
        assert "ManualOverride" not in runtime_source


    def test_schemas_are_closed_and_accept_canonical_documents():
        state = state_with(obligation("O-review"))
        debt = project_epistemic_debt(
            state,
            problem_revision_id=REVISION_ID,
            problem_revision_fingerprint=REVISION_FINGERPRINT,
        )
        item, rule_obj, risk_obj = override_for(state)
        assessment = evaluate_manual_override(
            item,
            (rule_obj,),
            (risk_obj,),
            state,
            clock_id="control-sequence",
            sequence=15,
        )
        docs = (
            ("epistemic-debt.schema.json", debt.to_dict()),
            ("manual-override.schema.json", item.to_dict()),
            ("manual-override-assessment.schema.json", assessment.to_dict()),
        )
        for filename, document in docs:
            schema = json.loads((ROOT / "schemas" / filename).read_text(encoding="utf-8"))
            Draft202012Validator.check_schema(schema)
            assert schema["additionalProperties"] is False
            validate(document, schema)
            changed = deepcopy(document)
            changed["unknown_field"] = True
            with pytest.raises(ValidationError):
                validate(changed, schema)
    ''',
)

write(
    "scripts/check_epistemic_debt_manual_override_contracts.py",
    r'''
    from __future__ import annotations

    import json
    from pathlib import Path

    from aasm.calculus import OBLIGATION_STATUSES


    ROOT = Path(__file__).resolve().parents[1]


    def fail(message: str) -> None:
        raise SystemExit(message)


    def text(path: str) -> str:
        target = ROOT / path
        if not target.exists():
            fail(f"missing epistemic-debt/manual-override contract file: {path}")
        return target.read_text(encoding="utf-8")


    def require(source: str, tokens: tuple[str, ...], label: str) -> None:
        missing = [token for token in tokens if token not in source]
        if missing:
            fail(f"{label} missing required tokens: {missing}")


    def forbid(source: str, tokens: tuple[str, ...], label: str) -> None:
        present = [token for token in tokens if token in source]
        if present:
            fail(f"{label} contains forbidden tokens: {present}")


    def main() -> None:
        model_paths = (
            "src/aasm/epistemic_debt_manual_override.py",
            "src/aasm/_epistemic_debt.py",
            "src/aasm/_manual_override.py",
        )
        model = "\n".join(text(path) for path in model_paths)
        calculus = text("src/aasm/_calculus_model.py")
        obligation_phase = text("src/aasm/obligation_phase.py")
        rule = text("src/aasm/rule.py")
        risk = text("src/aasm/risk_irreversibility.py")
        runtime = text("src/aasm/runtime_v56_foundation.py")
        package_root = text("src/aasm/__init__.py")
        tests = text("tests/test_epistemic_debt_manual_override_foundation.py")
        workflow = text(".github/workflows/engineering-epistemic-debt-manual-override.yml")

        require(
            model,
            (
                'EPISTEMIC_DEBT_CONTRACT_ID = "aasm.epistemic.debt.v1"',
                'MANUAL_OVERRIDE_CONTRACT_ID = "aasm.manual.override.v1"',
                'MANUAL_OVERRIDE_ASSESSMENT_CONTRACT_ID = "aasm.manual.override.assessment.v1"',
                "from .calculus import OBLIGATION_STATUSES, content_hash, normalize_calculus_state",
                "from .obligation_phase import",
                "obligation_semantic_fingerprint",
                "validate_obligation_phase_plan",
                "from .risk_irreversibility import RiskAssessment",
                "from .rule import EngineeringRule, RuleSourceAuthorityRef",
                "class EpistemicDebtItem:",
                "class EpistemicDebtProjection:",
                "class OverrideValidityWindow:",
                "class ResultingObligationRef:",
                "class ManualOverride:",
                "class ManualOverrideAssessment:",
                "def project_epistemic_debt(",
                "def validate_epistemic_debt_projection(",
                "def bind_manual_override(",
                "def evaluate_manual_override(",
                'rule.strength == "HARD_FLOOR"',
                'rule.control_policy.waiver_mode != "EXPLICIT_AUTHORIZED"',
                'risk.status != "REQUIRES_EXPLICIT_ACCEPTANCE"',
                '"debt_graph": "NONE_SECONDARY_OR_PARALLEL"',
                '"debt_store": "NONE_SECONDARY_OR_PARALLEL"',
                '"debt_scalar_score": "NONE"',
                '"hard_floor_override": "FORBIDDEN_UNCONDITIONALLY"',
                '"assessment_is_waiver": False',
                '"assessment_is_authorization": False',
                '"assessment_mutates_rule": False',
                '"assessment_mutates_obligation": False',
                '"parallel_override_registry": "NONE"',
                '"current_override_pointer": "NONE"',
                '"runtime_admission": "PRE_ADMISSION_ONLY"',
                '"public_admission": "PRE_ADMISSION_ONLY"',
            ),
            "epistemic-debt/manual-override model",
        )
        forbid(
            model,
            (
                "class ObligationRecord:",
                "\nOBLIGATION_STATUSES =",
                "\nOBLIGATION_TRANSITIONS =",
                "CURRENT_OVERRIDE",
                "OVERRIDE_REGISTRY",
                "EPISTEMIC_DEBT_STORE",
                "EPISTEMIC_DEBT_GRAPH",
                "FactAuthority(",
                ".authorize_effect(",
                ".execute_effect(",
                "dispatch_effect(",
                "set_obligation_status(",
                "register_obligation(",
                "datetime.now(",
                "time.time(",
            ),
            "epistemic-debt/manual-override model",
        )
        require(
            calculus,
            (
                "class ObligationRecord:",
                '"obligations": {},',
                '"obligation_edges": [],',
            ),
            "existing calculus",
        )
        require(
            obligation_phase,
            (
                'OBLIGATION_PHASE_CONTRACT_ID = "aasm.obligation.phase.v1"',
                "def obligation_semantic_fingerprint(",
            ),
            "existing obligation-phase foundation",
        )
        require(
            rule,
            (
                'RULE_CONTRACT_ID = "aasm.rule.v1"',
                '"HARD_FLOOR"',
                '"EXPLICIT_AUTHORIZED"',
                "class RuleSourceAuthorityRef:",
            ),
            "existing Rule foundation",
        )
        require(
            risk,
            (
                'RISK_ASSESSMENT_CONTRACT_ID = "aasm.risk.assessment.v1"',
                '"REQUIRES_EXPLICIT_ACCEPTANCE"',
            ),
            "existing RiskAssessment foundation",
        )
        if not {
            "VERIFIED",
            "COMMITTED",
            "REJECTED",
            "SUPERSEDED",
            "IMPOSSIBLE",
        }.issubset(OBLIGATION_STATUSES):
            fail("live obligation status vocabulary no longer supports S4.9 semantics")
        forbid(
            runtime,
            (
                "from .epistemic_debt_manual_override",
                "EpistemicDebtProjection",
                "ManualOverride",
                "ManualOverrideAssessment",
            ),
            "runtime_v56 foundation",
        )
        forbid(
            package_root,
            (
                "from .epistemic_debt_manual_override import",
                "EpistemicDebtProjection",
                "ManualOverride",
                "ManualOverrideAssessment",
            ),
            "active package root",
        )
        for filename, contract_id in (
            ("schemas/epistemic-debt.schema.json", "aasm.epistemic.debt.v1"),
            ("schemas/manual-override.schema.json", "aasm.manual.override.v1"),
            (
                "schemas/manual-override-assessment.schema.json",
                "aasm.manual.override.assessment.v1",
            ),
        ):
            schema = json.loads(text(filename))
            if schema.get("additionalProperties") is not False:
                fail(f"{filename} must be closed")
            serialized = json.dumps(schema, sort_keys=True)
            if contract_id not in serialized:
                fail(f"{filename} missing contract ID {contract_id}")
            if '"type": "number"' in serialized:
                fail(f"{filename} admits binary floating-point identity")
        for token in (
            "test_vocabularies_and_contract_claim_ceiling_are_exact",
            "test_debt_projection_uses_existing_obligations_edges_and_status_machine",
            "test_debt_projection_preserves_optional_s4_7_phase_bindings",
            "test_terminal_obligations_remain_visible_as_unresolved_debt",
            "test_stale_debt_projection_and_malformed_edge_projection_fail_closed",
            "test_manual_override_records_exact_required_bindings_and_round_trips",
            "test_hard_floor_and_nonwaivable_rules_fail_closed",
            "test_authority_capability_is_reference_only_and_must_match_rule_policy",
            "test_only_exact_explicit_acceptance_risk_is_eligible",
            "test_resulting_obligations_reuse_exact_existing_store_and_must_remain_open",
            "test_validity_uses_explicit_clock_and_sequence_without_hidden_wall_clock",
            "test_admissible_assessment_remains_review_only_and_pure",
            "test_override_resulting_obligation_remains_epistemic_debt_until_verified",
            "test_foundation_is_not_public_root_or_runtime_composition",
            "test_schemas_are_closed_and_accept_canonical_documents",
        ):
            if token not in tests:
                fail(f"S4.9 adversarial corpus missing test: {token}")
        require(
            workflow,
            (
                "python scripts/check_epistemic_debt_manual_override_contracts.py",
                "pytest -q tests/test_epistemic_debt_manual_override_foundation.py",
                "aasm/engineering-epistemic-debt-manual-override",
                "schemas/epistemic-debt.schema.json",
                "schemas/manual-override.schema.json",
                "schemas/manual-override-assessment.schema.json",
            ),
            "S4.9 workflow",
        )
        print("S4.9 epistemic-debt/manual-override pre-admission source contracts: PASS")


    if __name__ == "__main__":
        main()
    ''',
)

write(
    "scripts/check_s49_release_contracts.py",
    r'''
    from __future__ import annotations

    from pathlib import Path
    import sys


    def fail(message: str) -> None:
        raise SystemExit(message)


    def text(root: Path, path: str) -> str:
        target = root / path
        if not target.exists():
            fail(f"missing S4.9 release-contract file: {path}")
        return target.read_text(encoding="utf-8")


    def require(root: Path, path: str, tokens: tuple[str, ...]) -> None:
        source = text(root, path)
        missing = [token for token in tokens if token not in source]
        if missing:
            fail(f"{path} missing S4.9 release-contract tokens: {missing}")


    def forbid(root: Path, path: str, tokens: tuple[str, ...]) -> None:
        source = text(root, path)
        present = [token for token in tokens if token in source]
        if present:
            fail(f"{path} leaks pre-admission S4.9 contracts: {present}")


    def main() -> int:
        root = Path(__file__).resolve().parents[1]
        model = "\n".join(
            text(root, path)
            for path in (
                "src/aasm/epistemic_debt_manual_override.py",
                "src/aasm/_epistemic_debt.py",
                "src/aasm/_manual_override.py",
            )
        )
        tokens = (
            'EPISTEMIC_DEBT_CONTRACT_ID = "aasm.epistemic.debt.v1"',
            'MANUAL_OVERRIDE_CONTRACT_ID = "aasm.manual.override.v1"',
            'MANUAL_OVERRIDE_ASSESSMENT_CONTRACT_ID = "aasm.manual.override.assessment.v1"',
            '"debt_graph": "NONE_SECONDARY_OR_PARALLEL"',
            '"hard_floor_override": "FORBIDDEN_UNCONDITIONALLY"',
            '"assessment_is_authorization": False',
            '"runtime_admission": "PRE_ADMISSION_ONLY"',
            '"public_admission": "PRE_ADMISSION_ONLY"',
        )
        missing = [token for token in tokens if token not in model]
        if missing:
            fail(f"S4.9 model missing release-contract tokens: {missing}")
        for path in (
            "schemas/epistemic-debt.schema.json",
            "schemas/manual-override.schema.json",
            "schemas/manual-override-assessment.schema.json",
            "tests/test_epistemic_debt_manual_override_foundation.py",
            "scripts/check_epistemic_debt_manual_override_contracts.py",
            "docs/implementation/EPISTEMIC_DEBT_MANUAL_OVERRIDE_FOUNDATION.md",
        ):
            text(root, path)
        require(
            root,
            ".github/workflows/engineering-epistemic-debt-manual-override.yml",
            (
                "check_epistemic_debt_manual_override_contracts.py",
                "tests/test_epistemic_debt_manual_override_foundation.py",
                "context='aasm/engineering-epistemic-debt-manual-override'",
            ),
        )
        require(
            root,
            ".github/workflows/engineering-s4.yml",
            (
                "src/aasm/epistemic_debt_manual_override.py",
                "check_epistemic_debt_manual_override_contracts.py",
                "tests/test_epistemic_debt_manual_override_foundation.py",
                "context='aasm/engineering-s4'",
            ),
        )
        require(
            root,
            ".github/workflows/v56.yml",
            (
                "Check S4.9 Epistemic Debt and Manual Override pre-admission foundation",
                "check_epistemic_debt_manual_override_contracts.py",
                "tests/test_epistemic_debt_manual_override_foundation.py",
                "check_s49_release_contracts.py",
                "context='aasm/v56'",
            ),
        )
        require(
            root,
            ".github/workflows/release.yml",
            (
                "aasm/engineering-epistemic-debt-manual-override",
                "python scripts/check_s49_release_contracts.py",
            ),
        )
        forbid(
            root,
            "src/aasm/runtime_v56_foundation.py",
            (
                "from .epistemic_debt_manual_override",
                "EpistemicDebtProjection",
                "ManualOverride",
                "ManualOverrideAssessment",
            ),
        )
        forbid(
            root,
            "src/aasm/__init__.py",
            (
                "from .epistemic_debt_manual_override import",
                "EpistemicDebtProjection",
                "ManualOverride",
                "ManualOverrideAssessment",
            ),
        )
        sys.path.insert(0, str(root / "src"))
        import aasm

        contract = aasm.public_api_contract()
        for key in (
            "epistemic_debt",
            "manual_override",
            "manual_override_assessment",
        ):
            if key in contract:
                fail(f"pre-admission S4.9 surface leaked into active contract: {key}")
        for name in (
            "EpistemicDebtProjection",
            "ManualOverride",
            "ManualOverrideAssessment",
        ):
            if hasattr(aasm, name):
                fail(f"pre-admission S4.9 import leaked into package root: {name}")
        prefixes = ("epistemic_debt_", "manual_override_")
        if any(name.startswith(prefixes) for name in aasm.SUPPORTED_ENGINE_METHODS):
            fail("pre-admission S4.9 semantic IR leaked into engine methods")
        print("S4.9 epistemic-debt/manual-override release contracts: PASS")
        return 0


    if __name__ == "__main__":
        raise SystemExit(main())
    ''',
)

write(
    ".github/workflows/engineering-epistemic-debt-manual-override.yml",
    r'''
    name: AASM Engineering Epistemic Debt Manual Override Qualification

    on:
      push:
        branches: [main]
      pull_request:
        branches: [main]

    concurrency:
      group: aasm-engineering-epistemic-debt-manual-override-${{ github.ref }}
      cancel-in-progress: true

    permissions:
      contents: read
      statuses: write

    jobs:
      engineering-epistemic-debt-manual-override:
        runs-on: ubuntu-24.04
        steps:
          - uses: actions/checkout@v7
          - uses: actions/setup-python@v7
            with:
              python-version: "3.13"
              cache: pip
          - name: Install AASM development dependencies
            run: python -m pip install -e '.[dev]'
          - name: Compile S4.9 foundation and source firewall
            run: |
              python -m compileall -q \
                src/aasm/epistemic_debt_manual_override.py \
                src/aasm/_epistemic_debt.py \
                src/aasm/_manual_override.py \
                scripts/check_epistemic_debt_manual_override_contracts.py \
                tests/test_epistemic_debt_manual_override_foundation.py
              python -m json.tool schemas/epistemic-debt.schema.json >/dev/null
              python -m json.tool schemas/manual-override.schema.json >/dev/null
              python -m json.tool schemas/manual-override-assessment.schema.json >/dev/null
          - name: Check S4.9 source contracts
            run: python scripts/check_epistemic_debt_manual_override_contracts.py
          - name: Run S4.9 adversarial corpus
            run: pytest -q tests/test_epistemic_debt_manual_override_foundation.py
          - name: Publish S4.9 qualification
            if: always()
            env:
              GH_TOKEN: ${{ github.token }}
              JOB_STATUS: ${{ job.status }}
            shell: bash
            run: |
              set -euo pipefail
              if [ "$JOB_STATUS" = success ]; then
                state=success
                description='S4.9 epistemic-debt/manual-override pre-admission foundation passed'
              else
                state=failure
                description='S4.9 epistemic-debt/manual-override pre-admission foundation failed'
              fi
              for attempt in 1 2 3 4 5; do
                if gh api "repos/$GITHUB_REPOSITORY/statuses/$GITHUB_SHA" \
                  -f state="$state" \
                  -f context='aasm/engineering-epistemic-debt-manual-override' \
                  -f description="$description" \
                  -f target_url="https://github.com/$GITHUB_REPOSITORY/actions/runs/$GITHUB_RUN_ID"; then
                  exit 0
                fi
                if [ "$attempt" -lt 5 ]; then sleep $((attempt * 2)); fi
              done
              exit 1
    ''',
)

# Cumulative workflow integration.
replace_once(
    ".github/workflows/engineering-s4.yml",
    "            src/aasm/_safety_envelope_evaluation.py \\\n            scripts/check_quantity_contracts.py",
    "            src/aasm/_safety_envelope_evaluation.py \\\n            src/aasm/epistemic_debt_manual_override.py \\\n            src/aasm/_epistemic_debt.py \\\n            src/aasm/_manual_override.py \\\n            scripts/check_quantity_contracts.py",
)
replace_once(
    ".github/workflows/engineering-s4.yml",
    "            scripts/check_safety_envelope_hybrid_state_contracts.py\n          python -m json.tool schemas/quantity.schema.json",
    "            scripts/check_safety_envelope_hybrid_state_contracts.py \\\n            scripts/check_epistemic_debt_manual_override_contracts.py\n          python -m json.tool schemas/quantity.schema.json",
)
replace_once(
    ".github/workflows/engineering-s4.yml",
    "          python -m json.tool schemas/safety-envelope-assessment.schema.json >/dev/null\n",
    "          python -m json.tool schemas/safety-envelope-assessment.schema.json >/dev/null\n          python -m json.tool schemas/epistemic-debt.schema.json >/dev/null\n          python -m json.tool schemas/manual-override.schema.json >/dev/null\n          python -m json.tool schemas/manual-override-assessment.schema.json >/dev/null\n",
)
replace_once(
    ".github/workflows/engineering-s4.yml",
    "      - name: Run cumulative S4 semantic corpus\n",
    "      - name: Check Epistemic Debt and Manual Override pre-admission contracts\n        run: python scripts/check_epistemic_debt_manual_override_contracts.py\n      - name: Run cumulative S4 semantic corpus\n",
)
replace_once(
    ".github/workflows/engineering-s4.yml",
    "            tests/test_safety_envelope_hybrid_state_foundation.py\n",
    "            tests/test_safety_envelope_hybrid_state_foundation.py \\\n            tests/test_epistemic_debt_manual_override_foundation.py\n",
)
replace_once(
    ".github/workflows/engineering-s4.yml",
    "description='S4 through active degraded 0.32.20 + risk + obligation phases + safety envelope passed'",
    "description='S4 through active degraded 0.32.20 + risk + obligation phases + safety envelope + epistemic governance passed'",
)

# v0.56 cumulative integration.
replace_once(
    ".github/workflows/v56.yml",
    "      - name: Validate cumulative development source contract\n",
    "      - name: Check S4.9 Epistemic Debt and Manual Override pre-admission foundation\n        run: |\n          python scripts/check_epistemic_debt_manual_override_contracts.py\n          pytest -q tests/test_epistemic_debt_manual_override_foundation.py\n\n      - name: Validate cumulative development source contract\n",
)
replace_once(
    ".github/workflows/v56.yml",
    "          python scripts/check_s48_release_contracts.py\n",
    "          python scripts/check_s48_release_contracts.py\n          python scripts/check_s49_release_contracts.py\n",
)
replace_once(
    ".github/workflows/v56.yml",
    "          for key in ('obligation_phase','safety_envelope','hybrid_state','safety_envelope_assessment'):\n",
    "          for key in ('obligation_phase','safety_envelope','hybrid_state','safety_envelope_assessment','epistemic_debt','manual_override','manual_override_assessment'):\n",
)
replace_once(
    ".github/workflows/v56.yml",
    "          for name in ('ObligationPhasePlan','SafetyEnvelope','HybridState','SafetyEnvelopeAssessment'):\n",
    "          for name in ('ObligationPhasePlan','SafetyEnvelope','HybridState','SafetyEnvelopeAssessment','EpistemicDebtProjection','ManualOverride','ManualOverrideAssessment'):\n",
)
replace_once(
    ".github/workflows/v56.yml",
    "'safety_envelope_','hybrid_state_'))",
    "'safety_envelope_','hybrid_state_','epistemic_debt_','manual_override_'))",
)
replace_once(
    ".github/workflows/v56.yml",
    "through Safety Envelope/Hybrid State pre-admission: PASS",
    "through Epistemic Debt/Manual Override pre-admission: PASS",
)
replace_once(
    ".github/workflows/v56.yml",
    "and S4.8 pre-admission passed'",
    "and S4.9 pre-admission passed'",
)

# Release gate integration.
replace_once(
    ".github/workflows/release.yml",
    "            aasm/engineering-safety-envelope-hybrid-state \\\n            aasm/engineering-s4",
    "            aasm/engineering-safety-envelope-hybrid-state \\\n            aasm/engineering-epistemic-debt-manual-override \\\n            aasm/engineering-s4",
)
replace_once(
    ".github/workflows/release.yml",
    "          python scripts/check_s48_release_contracts.py\n",
    "          python scripts/check_s48_release_contracts.py\n          python scripts/check_s49_release_contracts.py\n",
)

# Roadmap and release-facing status corrections.
replace_once(
    "docs/roadmaps/GOVERNED_SEMANTIC_EVOLUTION_ROADMAP.md",
    "    4.7 Obligation phases                       NEXT\n    4.8 Safety envelope / hybrid state\n    4.9 Epistemic debt / manual override",
    "    4.7 Obligation phases                       FOUNDATION GATED; PRE-ADMISSION\n    4.8 Safety envelope / hybrid state             FOUNDATION GATED; PRE-ADMISSION\n    4.9 Epistemic debt / manual override            FOUNDATION IMPLEMENTED; QUALIFICATION ACTIVE",
)
replace_once(
    "docs/roadmaps/GOVERNED_SEMANTIC_EVOLUTION_ROADMAP.md",
    "**Status: NEXT after S4.6 foundation qualification/public admission review.**",
    "**Status: FOUNDATION GATED under `aasm/engineering-obligation-phase`; public/runtime admission remains `PRE_ADMISSION_ONLY`.**",
)
replace_once(
    "docs/roadmaps/GOVERNED_SEMANTIC_EVOLUTION_ROADMAP.md",
    "## 4.8 Safety envelope/hybrid state\n\nTargets:",
    "## 4.8 Safety envelope/hybrid state\n\n**Status: FOUNDATION GATED under `aasm/engineering-safety-envelope-hybrid-state`; public/runtime admission remains `PRE_ADMISSION_ONLY`.**\n\nTargets:",
)
replace_once(
    "docs/roadmaps/GOVERNED_SEMANTIC_EVOLUTION_ROADMAP.md",
    "## 4.9 Epistemic debt and manual override\n\nTargets:",
    "## 4.9 Epistemic debt and manual override\n\n**Status: FOUNDATION IMPLEMENTED; dedicated qualification active. Public/runtime admission remains `PRE_ADMISSION_ONLY`.**\n\nTargets:",
)
replace_once(
    "docs/roadmaps/GOVERNED_SEMANTIC_EVOLUTION_ROADMAP.md",
    "Debt uses existing semantic dependencies/obligations; no second debt graph.\n\nOverride records principal, exact waived rule, reason, scope, duration, accepted risk, authority evidence and resulting obligations. It never deletes history.",
    "Debt is a deterministic, revision-bound projection of the exact existing calculus obligations and `REQUIRES` edges; there is no second debt graph, store, lifecycle, scalar score, or forgiveness switch. Verified/committed obligations leave the projection, while terminal unresolved obligations remain visible.\n\nOverride records principal, exact Rule revision/fingerprint and scope, explicit logical-clock duration, exact accepted RiskAssessment, exact scoped-authority reference and evidence, and exact resulting existing obligations. `HARD_FLOOR` remains unconditionally non-overridable. An assessment is review eligibility only: it performs no waiver, authorization, Rule/obligation mutation, current-override activation, Effect dispatch, or history deletion.",
)
replace_once(
    "docs/roadmaps/GOVERNED_SEMANTIC_EVOLUTION_ROADMAP.md",
    "**Next seam:** finish S4.6 qualification, then S4.7 Obligation Phases.",
    "**Next seam:** S4.10 permanent TextPCB fixtures and aggregate safety-governance qualification, then S5 governed refinement.",
)
append_once(
    "docs/implementation/GOVERNED_SEMANTIC_EVOLUTION_EXECUTION_LEDGER.md",
    "## S4.9 — Epistemic Debt and Manual Override",
    r'''
    ## S4.8 — Safety Envelope and Hybrid State

    - Foundation implemented and gated under `aasm/engineering-safety-envelope-hybrid-state`.
    - Reuses exact Quantity, HARD_FLOOR/SAFETY_INVARIANT Rule, ProblemRevision, Evidence/external references, and existing authority/effect boundaries.
    - Performs conservative exact support containment only; no ODE/physics solving, controller synthesis, mode activation, authority grant, dispatch, or empirical safety proof.
    - Runtime/public admission remains `PRE_ADMISSION_ONLY`.

    ## S4.9 — Epistemic Debt and Manual Override

    - Foundation implemented; dedicated qualification active under `aasm/engineering-epistemic-debt-manual-override`.
    - `aasm.epistemic.debt.v1` projects unresolved knowledge from the existing calculus obligation graph; no second graph/store/lifecycle or scalar debt score.
    - `aasm.manual.override.v1` records exact Rule, scope, reason, explicit sequence window, accepted RiskAssessment, scoped-authority reference/evidence, and resulting existing obligations.
    - HARD_FLOOR is never overridable. Review eligibility performs no waiver, authorization, mutation, dispatch, current-override activation, or history deletion.
    - Runtime/public admission remains `PRE_ADMISSION_ONLY`.
    - Next dependency seam: S4.10 permanent TextPCB fixtures and aggregate safety-governance qualification.
    ''',
)
append_once(
    "ROADMAP.md",
    "## Governed Semantic Evolution live status — S4.9",
    r'''
    ## Governed Semantic Evolution live status — S4.9

    S4.8 Safety Envelope/Hybrid State is implemented as a gated pre-admission semantic foundation. S4.9 Epistemic Debt/Manual Override is implemented with a dedicated qualification gate and remains pre-admission. The next dependency-ordered seam is the permanent S4.10 TextPCB fixture corpus and aggregate `aasm/safety-governance` qualification before S5 refinement admission.
    ''',
)

# Correct stale README development status without changing published SemVer.
replace_once(
    "README.md",
    "**Current active adoption contract on `main`:** `aasm.adoption.v1 / 0.32.17`",
    "**Current active adoption contract on `main`:** `aasm.adoption.v1 / 0.32.20`",
)
replace_once(
    "README.md",
    "**Qualified development boundary:** PR-1 + PR-2 + complete PR-3 / PHY-01 + complete S3 + S4 `aasm.quantity.v1` + `aasm.rule.v1` public semantic foundations",
    "**Qualified development boundary:** PR-1 + PR-2 + complete PR-3 / PHY-01 + complete S3 + active S4 public lineage through Degraded Operation 0.32.20, with Risk/Irreversibility, Obligation Phases, Safety Envelope/Hybrid State, and Epistemic Debt/Manual Override gated pre-admission foundations",
)
replace_once(
    "README.md",
    "**Next unfinished boundary:** S4.3 — semantic projection/equivalence; one explicit “same/equivalent” contract with no implicit “same enough”",
    "**Next unfinished boundary:** S4.10 — permanent TextPCB safety/engineering fixtures and aggregate safety-governance qualification",
)
replace_once(
    "README.md",
    "active development adoption contract:       aasm.adoption.v1 / 0.32.17",
    "active development adoption contract:       aasm.adoption.v1 / 0.32.20",
)

# Update the canonical tracked-file inventory using its literal Python collection.
permanent_paths = [
    ".github/workflows/engineering-epistemic-debt-manual-override.yml",
    "schemas/epistemic-debt.schema.json",
    "schemas/manual-override.schema.json",
    "schemas/manual-override-assessment.schema.json",
    "scripts/check_epistemic_debt_manual_override_contracts.py",
    "scripts/check_s49_release_contracts.py",
    "docs/implementation/EPISTEMIC_DEBT_MANUAL_OVERRIDE_FOUNDATION.md",
    "tests/test_epistemic_debt_manual_override_foundation.py",
    "src/aasm/epistemic_debt_manual_override.py",
    "src/aasm/_epistemic_debt.py",
    "src/aasm/_manual_override.py",
]
anchors = {
    "src/aasm/obligation_phase.py",
    "scripts/check_obligation_phase_contracts.py",
    "tests/test_obligation_phase_foundation.py",
    "schemas/obligation-phase-assessment.schema.json",
    ".github/workflows/engineering-obligation-phase.yml",
}
check = subprocess.run(
    ["python", "scripts/release_manifest.py", "--check-file-list"],
    text=True,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
)
if check.returncode:
    candidates: list[tuple[int, Path, str]] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        if not any(word in path.name.lower() for word in ("release", "manifest", "inventory")):
            continue
        try:
            source = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        score = sum(anchor in source for anchor in anchors)
        if score >= 3:
            candidates.append((score, path, source))
    if not candidates:
        raise SystemExit("canonical tracked-file inventory source not found")
    _, inventory_path, source = max(candidates, key=lambda item: (item[0], len(item[2])))
    tree = ast.parse(source)
    matches: list[tuple[ast.List | ast.Tuple | ast.Set, list[str]]] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.List, ast.Tuple, ast.Set)):
            continue
        values: list[str] = []
        for element in node.elts:
            if not isinstance(element, ast.Constant) or not isinstance(element.value, str):
                break
            values.append(element.value)
        else:
            if len(anchors.intersection(values)) >= 3:
                matches.append((node, values))
    if not matches:
        raise SystemExit(f"canonical literal tracked-file inventory not found in {inventory_path}")
    node, values = max(matches, key=lambda item: len(item[1]))
    additions = [value for value in permanent_paths if value not in values]
    lines = source.splitlines()
    close_index = node.end_lineno - 1
    sample = next(
        (
            line
            for line in reversed(lines[node.lineno - 1 : node.end_lineno - 1])
            if '"' in line or "'" in line
        ),
        lines[close_index],
    )
    indentation = re.match(r"\s*", sample).group(0)
    quote = '"' if '"' in sample else "'"
    comma = "," if sample.rstrip().endswith(",") else ""
    lines[close_index:close_index] = [
        f"{indentation}{quote}{value}{quote}{comma}" for value in additions
    ]
    inventory_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

print("S4.9 payload materialized")
