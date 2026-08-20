from __future__ import annotations

"""S5.7 language-neutral reference boundary for governed refinement history.

The portable boundary carries identifiers, semantic fingerprints, Evidence
references, obligation/conflict/core references, and ProblemRevision transition
references only. It deliberately excludes solver/tool/model payloads and grants
no authority. Full portable machine semantics begin in S6.
"""

from copy import deepcopy
from dataclasses import dataclass, field
import re
from typing import Any, Iterable, Mapping, Sequence

from .semantic_result import semantic_fingerprint


REFINEMENT_PORTABLE_BOUNDARY_CONTRACT_ID = "aasm.refinement.portable-boundary.v1"
REFINEMENT_PORTABLE_BOUNDARY_CONTRACT_VERSION = "0.1.0"
REFINEMENT_PORTABLE_BOUNDARY_STABILITY = "FOUNDATION_EXPERIMENTAL"
REFINEMENT_PORTABLE_BOUNDARY_GATE = "aasm/refinement"

PORTABLE_REFINEMENT_EXCLUDED_ENGINES = (
    "LLM",
    "SOLVER",
    "CAD",
    "SPICE",
    "EM",
    "PHYSICS",
)

REFINEMENT_PORTABLE_AUTHORITY_CEILING = {
    "fact_authority": "NONE",
    "effect_authority": "NONE",
    "refinement_application_authority": "NONE",
    "problem_mutation": "NONE",
    "artifact_acceptance": "NONE",
    "solver_execution": "NONE",
    "runtime_admission": "PRE_ADMISSION_ONLY",
    "public_admission": "PRE_ADMISSION_ONLY",
}

_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _required(name: str, value: Any) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError(f"portable refinement {name} is required")
    return text


def _optional(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _sha256(name: str, value: Any) -> str:
    text = _required(name, value).lower()
    if not _SHA256.fullmatch(text):
        raise ValueError(f"portable refinement {name} must be a lowercase 64-hex SHA-256 digest")
    return text


def _uniq(values: Sequence[Any] | Iterable[Any], *, name: str) -> tuple[str, ...]:
    return tuple(sorted({_required(name, value) for value in values}))


def _round_trip(item: Any, supplied: str, *, label: str) -> None:
    if supplied and supplied != item.fingerprint:
        raise ValueError(f"{label} fingerprint mismatch")


@dataclass(frozen=True)
class PortableRevisionRef:
    revision_id: str
    revision_fingerprint: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "revision_id", _required("revision_id", self.revision_id))
        object.__setattr__(self, "revision_fingerprint", _sha256("revision_fingerprint", self.revision_fingerprint))

    def identity_payload(self) -> dict[str, Any]:
        return {
            "revision_id": self.revision_id,
            "revision_fingerprint": self.revision_fingerprint,
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(self.identity_payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "PortableRevisionRef":
        payload = deepcopy(dict(value))
        supplied = _optional(payload.pop("fingerprint", ""))
        item = cls(**payload)
        _round_trip(item, supplied, label="portable revision reference")
        return item


@dataclass(frozen=True)
class PortableProblemTransitionRef:
    delta_id: str
    delta_fingerprint: str
    base_revision_id: str
    target_revision_id: str
    transition_evidence_id: str

    def __post_init__(self) -> None:
        for name in ("delta_id", "base_revision_id", "target_revision_id", "transition_evidence_id"):
            object.__setattr__(self, name, _required(name, getattr(self, name)))
        object.__setattr__(self, "delta_fingerprint", _sha256("delta_fingerprint", self.delta_fingerprint))
        if self.base_revision_id == self.target_revision_id:
            raise ValueError("portable refinement transition must change revision identity")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "delta_id": self.delta_id,
            "delta_fingerprint": self.delta_fingerprint,
            "base_revision_id": self.base_revision_id,
            "target_revision_id": self.target_revision_id,
            "transition_evidence_id": self.transition_evidence_id,
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(self.identity_payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "PortableProblemTransitionRef":
        payload = deepcopy(dict(value))
        supplied = _optional(payload.pop("fingerprint", ""))
        item = cls(**payload)
        _round_trip(item, supplied, label="portable problem transition reference")
        return item


@dataclass(frozen=True)
class PortableRefinementBoundary:
    workspace_id: str
    scope_id: str
    problem_id: str
    revision_refs: tuple[PortableRevisionRef | Mapping[str, Any], ...]
    proposal_ids: tuple[str, ...] = ()
    validation_ids: tuple[str, ...] = ()
    application_ids: tuple[str, ...] = ()
    termination_ids: tuple[str, ...] = ()
    evidence_ids: tuple[str, ...] = ()
    obligation_ids: tuple[str, ...] = ()
    conflict_ids: tuple[str, ...] = ()
    core_ids: tuple[str, ...] = ()
    transition_refs: tuple[PortableProblemTransitionRef | Mapping[str, Any], ...] = ()
    boundary_id: str = ""
    contract_id: str = REFINEMENT_PORTABLE_BOUNDARY_CONTRACT_ID
    contract_version: str = REFINEMENT_PORTABLE_BOUNDARY_CONTRACT_VERSION

    def __post_init__(self) -> None:
        if self.contract_id != REFINEMENT_PORTABLE_BOUNDARY_CONTRACT_ID:
            raise ValueError("unsupported portable refinement boundary contract_id")
        if self.contract_version != REFINEMENT_PORTABLE_BOUNDARY_CONTRACT_VERSION:
            raise ValueError("unsupported portable refinement boundary contract_version")
        for name in ("workspace_id", "scope_id", "problem_id"):
            object.__setattr__(self, name, _required(name, getattr(self, name)))

        revisions = tuple(
            item if isinstance(item, PortableRevisionRef) else PortableRevisionRef.from_dict(item)
            for item in self.revision_refs
        )
        by_id = {item.revision_id: item for item in revisions}
        if not by_id:
            raise ValueError("portable refinement boundary requires at least one revision reference")
        if len(by_id) != len(revisions):
            raise ValueError("portable refinement revision IDs must be unique")
        object.__setattr__(self, "revision_refs", tuple(sorted(revisions, key=lambda item: item.revision_id)))

        for name in (
            "proposal_ids",
            "validation_ids",
            "application_ids",
            "termination_ids",
            "evidence_ids",
            "obligation_ids",
            "conflict_ids",
            "core_ids",
        ):
            object.__setattr__(self, name, _uniq(getattr(self, name), name=name))

        transitions = tuple(
            item if isinstance(item, PortableProblemTransitionRef) else PortableProblemTransitionRef.from_dict(item)
            for item in self.transition_refs
        )
        transition_keys = {(item.delta_id, item.delta_fingerprint): item for item in transitions}
        if len(transition_keys) != len(transitions):
            raise ValueError("portable refinement transition references must be unique")
        known_revisions = set(by_id)
        for transition in transitions:
            if transition.base_revision_id not in known_revisions or transition.target_revision_id not in known_revisions:
                raise ValueError("portable refinement transition references unknown revision")
            if transition.transition_evidence_id not in set(self.evidence_ids):
                raise ValueError("portable refinement transition Evidence must be present in boundary evidence_ids")
        object.__setattr__(
            self,
            "transition_refs",
            tuple(sorted(transitions, key=lambda item: (item.base_revision_id, item.target_revision_id, item.delta_id))),
        )

        supplied = _optional(self.boundary_id)
        derived = f"portable-refinement-{semantic_fingerprint(self.identity_payload())[:24]}"
        if supplied and supplied != derived:
            raise ValueError("portable refinement boundary_id does not match canonical identity")
        object.__setattr__(self, "boundary_id", derived)

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "workspace_id": self.workspace_id,
            "scope_id": self.scope_id,
            "problem_id": self.problem_id,
            "revision_refs": [item.to_dict() for item in self.revision_refs],
            "proposal_ids": list(self.proposal_ids),
            "validation_ids": list(self.validation_ids),
            "application_ids": list(self.application_ids),
            "termination_ids": list(self.termination_ids),
            "evidence_ids": list(self.evidence_ids),
            "obligation_ids": list(self.obligation_ids),
            "conflict_ids": list(self.conflict_ids),
            "core_ids": list(self.core_ids),
            "transition_refs": [item.to_dict() for item in self.transition_refs],
            "embedded_engines": [],
            "authority_claim": "NONE",
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"boundary_id": self.boundary_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"boundary_id": self.boundary_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "PortableRefinementBoundary":
        payload = deepcopy(dict(value))
        supplied = _optional(payload.pop("fingerprint", ""))
        embedded = payload.pop("embedded_engines", [])
        authority = payload.pop("authority_claim", "NONE")
        if embedded:
            raise ValueError("portable refinement boundary cannot embed execution engines")
        if authority != "NONE":
            raise ValueError("portable refinement boundary cannot carry authority")
        for name in (
            "revision_refs",
            "proposal_ids",
            "validation_ids",
            "application_ids",
            "termination_ids",
            "evidence_ids",
            "obligation_ids",
            "conflict_ids",
            "core_ids",
            "transition_refs",
        ):
            payload[name] = tuple(payload.get(name) or ())
        item = cls(**payload)
        _round_trip(item, supplied, label="portable refinement boundary")
        return item


def _revision_document(row: Mapping[str, Any]) -> Mapping[str, Any]:
    revision = row.get("revision")
    if not isinstance(revision, Mapping):
        raise ValueError("portable refinement projection revision row is missing revision document")
    return revision


def project_portable_refinement_boundary(
    projection: Mapping[str, Any],
    *,
    workspace_id: str,
    scope_id: str,
    problem_id: str,
) -> PortableRefinementBoundary:
    """Project a durable S5.1 refinement report into the S5.7 reference-only ABI."""

    if projection.get("valid") is not True:
        raise ValueError("portable refinement projection requires a valid durable refinement report")
    semantic = projection.get("semantic_evolution")
    if not isinstance(semantic, Mapping) or semantic.get("valid") is not True:
        raise ValueError("portable refinement projection requires valid semantic-evolution history")

    workspace = _required("workspace_id", workspace_id)
    scope = _required("scope_id", scope_id)
    problem = _required("problem_id", problem_id)

    revisions: dict[str, PortableRevisionRef] = {}
    for revision_id, raw in (semantic.get("revisions") or {}).items():
        row = _revision_document(raw)
        if row.get("problem_id") != problem:
            continue
        revision = PortableRevisionRef(str(revision_id), _sha256("revision fingerprint", row.get("fingerprint")))
        revisions[revision.revision_id] = revision
    if not revisions:
        raise KeyError(f"portable refinement projection found no revisions for problem: {problem}")

    proposals: dict[str, Mapping[str, Any]] = {}
    evidence_ids: set[str] = set()
    obligation_ids: set[str] = set()
    conflict_ids: set[str] = set()
    core_ids: set[str] = set()

    for proposal_id, raw in (projection.get("proposals") or {}).items():
        document = raw.get("proposal") or {}
        if document.get("workspace_id") != workspace or document.get("scope_id") != scope:
            continue
        if document.get("base_revision_id") not in revisions:
            continue
        proposals[str(proposal_id)] = document
        evidence_ids.add(_required("proposal record evidence_id", raw.get("evidence_id")))
        evidence_ids.update(str(item) for item in document.get("trigger_evidence_ids") or ())
        conflict_ids.update(str(item) for item in document.get("trigger_conflict_ids") or ())
        core_ids.update(str(item) for item in document.get("trigger_core_ids") or ())
        effect = document.get("expected_semantic_effect") or {}
        obligation_ids.update(str(item) for item in effect.get("impacted_obligation_ids") or ())

    proposal_ids = set(proposals)
    validations: set[str] = set()
    for validation_id, raw in (projection.get("validations") or {}).items():
        document = raw.get("validation") or {}
        if document.get("proposal_id") not in proposal_ids:
            continue
        validations.add(str(validation_id))
        evidence_ids.add(_required("validation record evidence_id", raw.get("evidence_id")))
        evidence_ids.update(str(item) for item in document.get("supporting_evidence_ids") or ())

    applications: set[str] = set()
    for application_id, raw in (projection.get("applications") or {}).items():
        document = raw.get("application") or {}
        if document.get("proposal_id") not in proposal_ids:
            continue
        applications.add(str(application_id))
        evidence_ids.add(_required("application record evidence_id", raw.get("evidence_id")))
        for key in (
            "scoped_authorization_evidence_id",
            "problem_transition_evidence_id",
        ):
            if document.get(key):
                evidence_ids.add(str(document[key]))
        if raw.get("truth_impact_evidence_id"):
            evidence_ids.add(str(raw["truth_impact_evidence_id"]))

    terminations: set[str] = set()
    for termination_id, raw in (projection.get("terminations") or {}).items():
        document = raw.get("termination") or {}
        if document.get("problem_id") != problem:
            continue
        terminations.add(str(termination_id))
        evidence_ids.add(_required("termination record evidence_id", raw.get("evidence_id")))
        evidence_ids.update(str(item) for item in document.get("evidence_ids") or ())
        obligation_ids.update(str(item) for item in document.get("blocking_obligation_ids") or ())

    transitions: list[PortableProblemTransitionRef] = []
    for delta_id, raw in (semantic.get("transitions") or {}).items():
        delta = raw.get("delta") or {}
        target = raw.get("target_revision") or {}
        base_revision_id = str(delta.get("base_revision_id") or "")
        target_revision_id = str(target.get("revision_id") or "")
        if base_revision_id not in revisions or target_revision_id not in revisions:
            continue
        transition_evidence_id = _required("transition evidence_id", raw.get("transition_evidence_id"))
        evidence_ids.add(transition_evidence_id)
        transitions.append(
            PortableProblemTransitionRef(
                delta_id=str(delta_id),
                delta_fingerprint=_sha256("delta fingerprint", delta.get("fingerprint")),
                base_revision_id=base_revision_id,
                target_revision_id=target_revision_id,
                transition_evidence_id=transition_evidence_id,
            )
        )

    return PortableRefinementBoundary(
        workspace_id=workspace,
        scope_id=scope,
        problem_id=problem,
        revision_refs=tuple(revisions.values()),
        proposal_ids=tuple(proposal_ids),
        validation_ids=tuple(validations),
        application_ids=tuple(applications),
        termination_ids=tuple(terminations),
        evidence_ids=tuple(evidence_ids),
        obligation_ids=tuple(obligation_ids),
        conflict_ids=tuple(conflict_ids),
        core_ids=tuple(core_ids),
        transition_refs=tuple(transitions),
    )


def refinement_portable_boundary_contract() -> dict[str, Any]:
    return {
        "contract_id": REFINEMENT_PORTABLE_BOUNDARY_CONTRACT_ID,
        "contract_version": REFINEMENT_PORTABLE_BOUNDARY_CONTRACT_VERSION,
        "stability": REFINEMENT_PORTABLE_BOUNDARY_STABILITY,
        "gate": REFINEMENT_PORTABLE_BOUNDARY_GATE,
        "carries": [
            "REFINEMENT_IDS",
            "REVISION_IDS_AND_FINGERPRINTS",
            "EVIDENCE_REFS",
            "OBLIGATION_REFS",
            "CONFLICT_AND_CORE_REFS",
            "PROBLEM_TRANSITION_REFS",
        ],
        "excluded_engines": list(PORTABLE_REFINEMENT_EXCLUDED_ENGINES),
        "embedded_payloads": "NONE_REFERENCE_ONLY",
        "canonical_source": "EXISTING_S5.1_DURABLE_REFINEMENT_PROJECTION",
        "authority_ceiling": deepcopy(REFINEMENT_PORTABLE_AUTHORITY_CEILING),
        "s6_relationship": "REFERENCE_ABI_ONLY_MACHINE_IR_AND_PORTABLE_REDUCER_BEGIN_IN_S6",
    }


__all__ = [
    "REFINEMENT_PORTABLE_BOUNDARY_CONTRACT_ID",
    "REFINEMENT_PORTABLE_BOUNDARY_CONTRACT_VERSION",
    "REFINEMENT_PORTABLE_BOUNDARY_STABILITY",
    "REFINEMENT_PORTABLE_BOUNDARY_GATE",
    "PORTABLE_REFINEMENT_EXCLUDED_ENGINES",
    "REFINEMENT_PORTABLE_AUTHORITY_CEILING",
    "PortableRevisionRef",
    "PortableProblemTransitionRef",
    "PortableRefinementBoundary",
    "project_portable_refinement_boundary",
    "refinement_portable_boundary_contract",
]
