from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
import hashlib
import json
from typing import Any, Iterable

from .calculus import canonical_json


CERTIFICATE_STATUSES = {"PROPOSED", "VERIFIED", "REJECTED", "INCONCLUSIVE", "EXPIRED"}


def fingerprint(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


@dataclass
class AssurancePolicy:
    require_certificate_for_hard_constraint: bool = True
    accepted_verification_levels: list[str] = field(default_factory=lambda: ["PROVEN", "VALIDATED"])

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CertificateRecord:
    certificate_id: str
    kind: str
    subject_type: str
    subject_id: str
    payload: dict[str, Any]
    verifier_id: str
    status: str = "PROPOSED"
    scope: dict[str, Any] = field(default_factory=dict)
    created_sequence: int = 0
    verified_sequence: int | None = None

    def __post_init__(self):
        if not all([self.certificate_id, self.kind, self.subject_type, self.subject_id, self.verifier_id]):
            raise ValueError("certificate identity, subject, kind, and verifier are required")
        if self.status not in CERTIFICATE_STATUSES:
            raise ValueError(f"invalid certificate status: {self.status}")

    @property
    def payload_fingerprint(self) -> str:
        return fingerprint(self.payload)

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["payload_fingerprint"] = self.payload_fingerprint
        return value


@dataclass
class CertificateVerification:
    verification_id: str
    certificate_id: str
    verifier_id: str
    valid: bool | None
    level: str
    reason: str = ""
    evidence: dict[str, Any] = field(default_factory=dict)
    sequence: int = 0

    def __post_init__(self):
        if not self.verification_id or not self.certificate_id or not self.verifier_id:
            raise ValueError("verification identity and verifier are required")
        if self.level not in {"PROVEN", "VALIDATED", "CORROBORATED", "PROVISIONAL", "HEURISTIC", "REJECTED"}:
            raise ValueError(f"invalid verification level: {self.level}")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class HistoryIssue:
    code: str
    message: str
    severity: str = "ERROR"
    sequence: int | None = None
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class HistoryCheckReport:
    status: str
    machine_id: str
    checked_sequence: int
    issues: list[HistoryIssue] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return self.status == "PASS" and not any(issue.severity == "ERROR" for issue in self.issues)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "machine_id": self.machine_id,
            "checked_sequence": self.checked_sequence,
            "valid": self.valid,
            "issues": [issue.to_dict() for issue in self.issues],
        }


def projection_payload(constraint: dict[str, Any]) -> dict[str, Any]:
    return {
        "constraint_id": constraint.get("constraint_id"),
        "body": deepcopy(constraint.get("body") or []),
        "guard": deepcopy(constraint.get("guard") or {"const": True}),
        "source_conflict_id": constraint.get("source_conflict_id"),
        "source_explanation_id": constraint.get("source_explanation_id"),
        "evidence_ids": sorted(set(constraint.get("evidence_ids") or [])),
        "target_strength": "HARD",
        "scope": deepcopy(constraint.get("scope") or {}),
    }


class ProjectionCertificateVerifier:
    verifier_id = "aasm.projection"

    def verify(
        self,
        certificate: CertificateRecord,
        constraint: dict[str, Any],
        *,
        sequence: int = 0,
    ) -> CertificateVerification:
        expected = projection_payload(constraint)
        valid = certificate.subject_type == "LEARNED_CONSTRAINT" and certificate.subject_id == constraint.get("constraint_id") and certificate.payload == expected
        return CertificateVerification(
            verification_id="verify_" + fingerprint({
                "certificate": certificate.certificate_id,
                "constraint": constraint.get("constraint_id"),
                "sequence": sequence,
            })[:16],
            certificate_id=certificate.certificate_id,
            verifier_id=self.verifier_id,
            valid=valid,
            level="PROVEN" if valid else "REJECTED",
            reason="projection payload exactly matched" if valid else "certificate does not cover the current constraint projection",
            evidence={"expected_fingerprint": fingerprint(expected), "actual_fingerprint": certificate.payload_fingerprint},
            sequence=sequence,
        )


class DetachedDigestVerifier:
    verifier_id = "aasm.sha256"

    def verify_bytes(
        self,
        certificate: CertificateRecord,
        data: bytes,
        *,
        sequence: int = 0,
    ) -> CertificateVerification:
        expected = str(certificate.payload.get("sha256", ""))
        actual = hashlib.sha256(data).hexdigest()
        valid = bool(expected) and expected == actual
        return CertificateVerification(
            verification_id="verify_" + fingerprint({"certificate": certificate.certificate_id, "sha256": actual})[:16],
            certificate_id=certificate.certificate_id,
            verifier_id=self.verifier_id,
            valid=valid,
            level="PROVEN" if valid else "REJECTED",
            reason="digest matched" if valid else "digest mismatch",
            evidence={"expected_sha256": expected, "actual_sha256": actual},
            sequence=sequence,
        )


def check_history(snapshot: Any, events: Iterable[Any]) -> HistoryCheckReport:
    issues: list[HistoryIssue] = []
    rows = list(events)
    machine_id = str(getattr(snapshot, "machine_id", ""))
    previous_sequence = 0
    seen_ids: set[str] = set()
    terminal_seen = False
    for event in rows:
        sequence = int(getattr(event, "sequence", 0))
        event_id = str(getattr(event, "event_id", ""))
        if sequence <= previous_sequence:
            issues.append(HistoryIssue("NON_MONOTONIC_SEQUENCE", f"event sequence {sequence} follows {previous_sequence}", sequence=sequence))
        previous_sequence = sequence
        if event_id in seen_ids:
            issues.append(HistoryIssue("DUPLICATE_EVENT_ID", f"duplicate event ID {event_id}", sequence=sequence))
        seen_ids.add(event_id)
        event_machine = str(getattr(event, "machine_id", ""))
        if event_machine and machine_id and event_machine != machine_id:
            issues.append(HistoryIssue("MACHINE_ID_MISMATCH", f"event belongs to {event_machine}, expected {machine_id}", sequence=sequence))
        from_state = getattr(event, "from_state", None)
        to_state = getattr(event, "to_state", None)
        if terminal_seen and from_state != to_state:
            issues.append(HistoryIssue("TERMINAL_NOT_ABSORBING", "state-changing event followed a terminal transition", sequence=sequence))
        if to_state in {"COMPLETE", "FAIL"}:
            terminal_seen = True

    if rows and int(getattr(snapshot, "version", 0)) < 0:
        issues.append(HistoryIssue("NEGATIVE_SNAPSHOT_VERSION", "snapshot version cannot be negative"))
    calculus = deepcopy(getattr(snapshot, "calculus", {}) or {})
    if getattr(snapshot, "state", None) == "COMPLETE":
        unresolved = [
            obligation_id
            for obligation_id, obligation in calculus.get("obligations", {}).items()
            if obligation.get("mandatory", True)
            and obligation.get("persistent", True)
            and obligation.get("status") not in {"COMMITTED", "REJECTED", "SUPERSEDED", "IMPOSSIBLE"}
        ]
        if unresolved:
            issues.append(HistoryIssue("COMPLETE_WITH_UNRESOLVED_OBLIGATIONS", f"unresolved obligations: {sorted(unresolved)}"))
    status = "PASS" if not any(issue.severity == "ERROR" for issue in issues) else "FAIL"
    return HistoryCheckReport(
        status=status,
        machine_id=machine_id,
        checked_sequence=previous_sequence,
        issues=issues,
    )
