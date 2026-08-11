from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
import hashlib
from typing import Any, Iterable

from .calculus import (
    assert_calculus_invariants,
    canonical_json,
    condition_holds,
    decision_values,
    normalize_calculus_state,
)


CERTIFICATE_STATUSES = {"PROPOSED", "VERIFIED", "REJECTED", "INCONCLUSIVE", "EXPIRED"}
VERIFICATION_LEVELS = {
    "PROVEN",
    "VALIDATED",
    "CORROBORATED",
    "PROVISIONAL",
    "HEURISTIC",
    "REJECTED",
}


def fingerprint(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def default_assurance_policy() -> dict[str, Any]:
    return {
        "require_certificate_for_hard_constraint": True,
        "accepted_verification_levels": ["PROVEN", "VALIDATED"],
        "accepted_certificate_kinds": ["PROJECTION"],
        "accepted_verifier_ids": ["aasm.projection"],
        "required_subject_type": "LEARNED_CONSTRAINT",
    }


def normalize_assurance_state(raw: dict[str, Any] | None) -> dict[str, Any]:
    state = {
        "schema_version": 1,
        "policy": default_assurance_policy(),
        "certificates": {},
        "verifications": {},
        "history_checks": [],
        "minimizations": {},
        "generalizations": {},
    }
    if not raw:
        return state
    out = deepcopy(state)
    out.update(deepcopy(raw))
    policy = default_assurance_policy()
    policy.update(deepcopy((raw or {}).get("policy") or {}))
    out["policy"] = policy
    for key, default in (
        ("certificates", {}),
        ("verifications", {}),
        ("history_checks", []),
        ("minimizations", {}),
        ("generalizations", {}),
    ):
        out.setdefault(key, deepcopy(default))
    return out


@dataclass
class AssurancePolicy:
    require_certificate_for_hard_constraint: bool = True
    accepted_verification_levels: list[str] = field(
        default_factory=lambda: ["PROVEN", "VALIDATED"]
    )
    accepted_certificate_kinds: list[str] = field(default_factory=lambda: ["PROJECTION"])
    accepted_verifier_ids: list[str] = field(default_factory=lambda: ["aasm.projection"])
    required_subject_type: str = "LEARNED_CONSTRAINT"

    def __post_init__(self):
        self.accepted_verification_levels = sorted(set(self.accepted_verification_levels))
        unknown = set(self.accepted_verification_levels) - VERIFICATION_LEVELS
        if unknown:
            raise ValueError(f"unknown accepted verification levels: {sorted(unknown)}")
        self.accepted_certificate_kinds = sorted(set(self.accepted_certificate_kinds))
        self.accepted_verifier_ids = sorted(set(self.accepted_verifier_ids))
        if not self.required_subject_type:
            raise ValueError("required_subject_type cannot be empty")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "AssurancePolicy":
        policy = default_assurance_policy()
        policy.update(deepcopy(data or {}))
        return cls(**policy)


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
        if self.level not in VERIFICATION_LEVELS:
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
    checked_event_id: str | None = None
    reconstructed_snapshot_hash: str | None = None
    persisted_snapshot_hash: str | None = None
    reconstructed_version: int | None = None
    persisted_version: int | None = None

    @property
    def valid(self) -> bool:
        return self.status == "PASS" and not any(issue.severity == "ERROR" for issue in self.issues)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "machine_id": self.machine_id,
            "checked_sequence": self.checked_sequence,
            "checked_event_id": self.checked_event_id,
            "valid": self.valid,
            "reconstructed_snapshot_hash": self.reconstructed_snapshot_hash,
            "persisted_snapshot_hash": self.persisted_snapshot_hash,
            "reconstructed_version": self.reconstructed_version,
            "persisted_version": self.persisted_version,
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
        valid = (
            certificate.subject_type == "LEARNED_CONSTRAINT"
            and certificate.subject_id == constraint.get("constraint_id")
            and certificate.payload == expected
            and certificate.verifier_id == self.verifier_id
        )
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
            reason=(
                "projection payload exactly matched"
                if valid
                else "certificate does not cover the current constraint projection"
            ),
            evidence={
                "expected_fingerprint": fingerprint(expected),
                "actual_fingerprint": certificate.payload_fingerprint,
            },
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


def hard_constraint_certification_issues(
    calculus: dict[str, Any],
    assurance_state: dict[str, Any] | None,
    *,
    current_sequence: int | None = None,
) -> list[HistoryIssue]:
    """Return every certificate-policy violation for active hard constraints."""

    state = normalize_assurance_state(assurance_state)
    policy = AssurancePolicy.from_dict(state.get("policy"))
    if not policy.require_certificate_for_hard_constraint:
        return []

    issues: list[HistoryIssue] = []
    certificates = state.get("certificates", {})
    verifications = state.get("verifications", {})
    for constraint_id, constraint in normalize_calculus_state(calculus).get("constraints", {}).items():
        if constraint.get("strength") != "HARD" or constraint.get("status") != "ACTIVE":
            continue
        certificate_id = constraint.get("certificate_id")
        if not certificate_id:
            issues.append(HistoryIssue(
                "UNCERTIFIED_HARD_CONSTRAINT",
                f"active hard constraint {constraint_id} has no certificate",
                data={"constraint_id": constraint_id},
            ))
            continue
        certificate = certificates.get(certificate_id)
        if certificate is None:
            issues.append(HistoryIssue(
                "MISSING_HARD_CONSTRAINT_CERTIFICATE",
                f"constraint {constraint_id} references unknown certificate {certificate_id}",
                data={"constraint_id": constraint_id, "certificate_id": certificate_id},
            ))
            continue
        if certificate.get("status") != "VERIFIED":
            issues.append(HistoryIssue(
                "UNVERIFIED_HARD_CONSTRAINT_CERTIFICATE",
                f"certificate {certificate_id} is {certificate.get('status')}, not VERIFIED",
                data={"constraint_id": constraint_id, "certificate_id": certificate_id},
            ))
        if certificate.get("kind") not in policy.accepted_certificate_kinds:
            issues.append(HistoryIssue(
                "UNACCEPTED_CERTIFICATE_KIND",
                f"certificate {certificate_id} kind {certificate.get('kind')} is not accepted",
                data={"accepted": policy.accepted_certificate_kinds},
            ))
        if certificate.get("subject_type") != policy.required_subject_type:
            issues.append(HistoryIssue(
                "CERTIFICATE_SUBJECT_TYPE_MISMATCH",
                f"certificate {certificate_id} subject type does not satisfy policy",
                data={"required": policy.required_subject_type},
            ))
        if certificate.get("subject_id") != constraint_id:
            issues.append(HistoryIssue(
                "CERTIFICATE_SUBJECT_MISMATCH",
                f"certificate {certificate_id} does not name constraint {constraint_id}",
            ))
        if (
            policy.accepted_verifier_ids
            and certificate.get("verifier_id") not in policy.accepted_verifier_ids
        ):
            issues.append(HistoryIssue(
                "UNACCEPTED_CERTIFICATE_VERIFIER",
                f"certificate {certificate_id} verifier {certificate.get('verifier_id')} is not accepted",
                data={"accepted": policy.accepted_verifier_ids},
            ))
        expected_payload = projection_payload(constraint)
        expected_fingerprint = fingerprint(expected_payload)
        if certificate.get("payload") != expected_payload:
            issues.append(HistoryIssue(
                "CERTIFICATE_PROJECTION_MISMATCH",
                f"certificate {certificate_id} does not cover the current projection of {constraint_id}",
                data={"expected_fingerprint": expected_fingerprint},
            ))
        if certificate.get("payload_fingerprint") != expected_fingerprint:
            issues.append(HistoryIssue(
                "CERTIFICATE_FINGERPRINT_MISMATCH",
                f"certificate {certificate_id} fingerprint does not match the current constraint",
                data={"expected_fingerprint": expected_fingerprint},
            ))
        verification_id = certificate.get("verification_id")
        verification = verifications.get(verification_id) if verification_id else None
        if verification is None:
            issues.append(HistoryIssue(
                "MISSING_CERTIFICATE_VERIFICATION",
                f"certificate {certificate_id} has no durable verification record",
            ))
            continue
        if verification.get("certificate_id") != certificate_id:
            issues.append(HistoryIssue(
                "VERIFICATION_CERTIFICATE_MISMATCH",
                f"verification {verification_id} names a different certificate",
            ))
        if verification.get("valid") is not True:
            issues.append(HistoryIssue(
                "INVALID_CERTIFICATE_VERIFICATION",
                f"verification {verification_id} did not accept certificate {certificate_id}",
            ))
        if verification.get("level") not in policy.accepted_verification_levels:
            issues.append(HistoryIssue(
                "UNACCEPTED_VERIFICATION_LEVEL",
                f"verification {verification_id} level {verification.get('level')} is not accepted",
                data={"accepted": policy.accepted_verification_levels},
            ))
        if verification.get("verifier_id") != certificate.get("verifier_id"):
            issues.append(HistoryIssue(
                "VERIFIER_ID_MISMATCH",
                f"verification {verification_id} was produced by a different verifier",
            ))
        expires_sequence = certificate.get("expires_sequence")
        if (
            current_sequence is not None
            and expires_sequence is not None
            and int(expires_sequence) < int(current_sequence)
        ):
            issues.append(HistoryIssue(
                "EXPIRED_HARD_CONSTRAINT_CERTIFICATE",
                f"certificate {certificate_id} expired before sequence {current_sequence}",
                data={"expires_sequence": int(expires_sequence)},
            ))
    return issues


def assert_hard_constraint_certification(
    calculus: dict[str, Any],
    assurance_state: dict[str, Any] | None,
    *,
    current_sequence: int | None = None,
) -> None:
    issues = hard_constraint_certification_issues(
        calculus,
        assurance_state,
        current_sequence=current_sequence,
    )
    if issues:
        raise ValueError("; ".join(f"{issue.code}: {issue.message}" for issue in issues))


def check_history(snapshot: Any, events: Iterable[Any]) -> HistoryCheckReport:
    """Replay a durable event stream and compare it with persisted state."""

    from .core.reducer import reduce_event
    from .persistence.serde import snapshot_to_dict

    issues: list[HistoryIssue] = []
    rows = list(events)
    machine_id = str(getattr(snapshot, "machine_id", ""))
    previous_sequence = 0
    checked_event_id: str | None = None
    seen_ids: set[str] = set()
    replayed = None
    expected_machine_id: str | None = None
    transition_map: dict[str, set[str]] = {}
    terminal_states = {"COMPLETE", "FAIL"}
    prior_hard_ids: set[str] = set()

    if not rows:
        issues.append(HistoryIssue("EMPTY_HISTORY", "durable history is empty"))

    for index, event in enumerate(rows, start=1):
        sequence = int(getattr(event, "sequence", 0))
        event_id = str(getattr(event, "event_id", ""))
        event_type = str(getattr(event, "event_type", ""))
        event_machine = str(getattr(event, "machine_id", ""))
        if sequence != index:
            issues.append(HistoryIssue(
                "NON_CONTIGUOUS_SEQUENCE",
                f"expected event sequence {index}, found {sequence}",
                sequence=sequence,
            ))
        if sequence <= previous_sequence:
            issues.append(HistoryIssue(
                "NON_MONOTONIC_SEQUENCE",
                f"event sequence {sequence} follows {previous_sequence}",
                sequence=sequence,
            ))
        previous_sequence = sequence
        checked_event_id = event_id or checked_event_id
        if not event_id:
            issues.append(HistoryIssue("MISSING_EVENT_ID", "event ID is empty", sequence=sequence))
        elif event_id in seen_ids:
            issues.append(HistoryIssue(
                "DUPLICATE_EVENT_ID",
                f"duplicate event ID {event_id}",
                sequence=sequence,
            ))
        seen_ids.add(event_id)
        if int(getattr(event, "schema_version", 0)) < 1:
            issues.append(HistoryIssue(
                "INVALID_EVENT_SCHEMA_VERSION",
                "event schema_version must be positive",
                sequence=sequence,
            ))

        if expected_machine_id is None and event_machine:
            expected_machine_id = event_machine
        if event_machine and expected_machine_id and event_machine != expected_machine_id:
            issues.append(HistoryIssue(
                "MACHINE_ID_MISMATCH",
                f"event belongs to {event_machine}, expected {expected_machine_id}",
                sequence=sequence,
            ))
        if event_machine and machine_id and event_machine != machine_id:
            issues.append(HistoryIssue(
                "PERSISTED_MACHINE_ID_MISMATCH",
                f"event belongs to {event_machine}, persisted snapshot belongs to {machine_id}",
                sequence=sequence,
            ))

        if replayed is not None:
            from_state = getattr(event, "from_state", None)
            if from_state is not None and str(from_state) != str(replayed.state):
                issues.append(HistoryIssue(
                    "STATE_CONTINUITY_ERROR",
                    f"event expects state {from_state}, replay is in {replayed.state}",
                    sequence=sequence,
                ))
            if event_type == "transition_committed":
                target = str(getattr(event, "to_state", ""))
                allowed = transition_map.get(str(replayed.state))
                if allowed is not None and target not in allowed:
                    issues.append(HistoryIssue(
                        "ILLEGAL_REPLAY_TRANSITION",
                        f"transition {replayed.state}->{target} is not in the machine definition",
                        sequence=sequence,
                    ))
                if str(replayed.state) in terminal_states and target != str(replayed.state):
                    issues.append(HistoryIssue(
                        "TERMINAL_NOT_ABSORBING",
                        "a state-changing transition followed a terminal state",
                        sequence=sequence,
                    ))

        before_state = replayed
        try:
            replayed = reduce_event(replayed, event)
        except Exception as exc:
            issues.append(HistoryIssue(
                "REPLAY_REDUCER_ERROR",
                f"{type(exc).__name__}: {exc}",
                sequence=sequence,
            ))
            break

        if index == 1:
            definition = deepcopy((getattr(event, "data", {}) or {}).get("machine_definition") or {})
            terminal_states = set(definition.get("terminal_states") or terminal_states)
            transition_map = {
                str(source): set(map(str, targets or []))
                for source, targets in (definition.get("transitions") or {}).items()
            }

        if before_state is not None and str(before_state.state) in terminal_states:
            if str(replayed.state) != str(before_state.state):
                issues.append(HistoryIssue(
                    "TERMINAL_NOT_ABSORBING",
                    "reducer changed the machine state after a terminal state",
                    sequence=sequence,
                ))

        current_calculus = normalize_calculus_state(getattr(replayed, "calculus", {}) or {})
        hard_ids = {
            constraint_id
            for constraint_id, constraint in current_calculus.get("constraints", {}).items()
            if constraint.get("strength") == "HARD"
        }
        missing_hard_records = sorted(prior_hard_ids - set(current_calculus.get("constraints", {})))
        if missing_hard_records:
            issues.append(HistoryIssue(
                "HARD_CONSTRAINT_RECORD_LOST",
                f"hard constraint records disappeared during replay: {missing_hard_records}",
                sequence=sequence,
            ))
        prior_hard_ids |= hard_ids

    reconstructed_hash = None
    persisted_hash = fingerprint(snapshot_to_dict(snapshot))
    reconstructed_version = None
    persisted_version = int(getattr(snapshot, "version", 0))
    if replayed is not None:
        reconstructed_payload = snapshot_to_dict(replayed)
        reconstructed_hash = fingerprint(reconstructed_payload)
        reconstructed_version = int(getattr(replayed, "version", 0))
        if reconstructed_payload != snapshot_to_dict(snapshot):
            issues.append(HistoryIssue(
                "PERSISTED_SNAPSHOT_MISMATCH",
                "replayed history does not exactly reproduce the persisted snapshot",
                data={
                    "reconstructed_snapshot_hash": reconstructed_hash,
                    "persisted_snapshot_hash": persisted_hash,
                    "reconstructed_version": reconstructed_version,
                    "persisted_version": persisted_version,
                },
            ))
        try:
            assert_calculus_invariants(getattr(replayed, "calculus", {}) or {})
        except Exception as exc:
            issues.append(HistoryIssue(
                "CALCULUS_INVARIANT_FAILURE",
                f"{type(exc).__name__}: {exc}",
            ))
        issues.extend(hard_constraint_certification_issues(
            getattr(replayed, "calculus", {}) or {},
            getattr(replayed, "assurance_state", {}) or {},
            current_sequence=previous_sequence,
        ))

        calculus = normalize_calculus_state(getattr(replayed, "calculus", {}) or {})
        values = decision_values(calculus)
        for lock_id, lock in calculus.get("locks", {}).items():
            if lock.get("status") == "ACTIVE" and not condition_holds(lock.get("condition"), values):
                issues.append(HistoryIssue(
                    "STALE_ACTIVE_LOCK",
                    f"active lock {lock_id} is false under the reconstructed model",
                    data={"lock_id": lock_id},
                ))

        binding = deepcopy(getattr(replayed, "profile_binding", {}) or {})
        profile_snapshot = binding.get("profile_snapshot")
        profile_fingerprint = binding.get("profile_fingerprint")
        if profile_snapshot and profile_fingerprint:
            actual = fingerprint(profile_snapshot)
            if actual != profile_fingerprint:
                issues.append(HistoryIssue(
                    "PROFILE_FINGERPRINT_MISMATCH",
                    "active profile snapshot does not match its recorded fingerprint",
                    data={"expected": profile_fingerprint, "actual": actual},
                ))

        if getattr(replayed, "state", None) == "COMPLETE":
            unresolved = [
                obligation_id
                for obligation_id, obligation in calculus.get("obligations", {}).items()
                if obligation.get("mandatory", True)
                and obligation.get("persistent", True)
                and obligation.get("status")
                not in {"COMMITTED", "REJECTED", "SUPERSEDED", "IMPOSSIBLE"}
            ]
            if unresolved:
                issues.append(HistoryIssue(
                    "COMPLETE_WITH_UNRESOLVED_OBLIGATIONS",
                    f"unresolved obligations: {sorted(unresolved)}",
                ))

    if persisted_version < 0:
        issues.append(HistoryIssue(
            "NEGATIVE_SNAPSHOT_VERSION",
            "snapshot version cannot be negative",
        ))

    status = "PASS" if not any(issue.severity == "ERROR" for issue in issues) else "FAIL"
    return HistoryCheckReport(
        status=status,
        machine_id=machine_id,
        checked_sequence=previous_sequence,
        checked_event_id=checked_event_id,
        reconstructed_snapshot_hash=reconstructed_hash,
        persisted_snapshot_hash=persisted_hash,
        reconstructed_version=reconstructed_version,
        persisted_version=persisted_version,
        issues=issues,
    )
