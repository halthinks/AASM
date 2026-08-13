from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from typing import Any, Iterable, Mapping

from .semantic_result import canonical_semantic_json, semantic_fingerprint


REASONING_ARTIFACT_CONTRACT_ID = "aasm.reasoning.artifact.v1"
REASONING_ARTIFACT_CONTRACT_VERSION = "0.1.0"
EPISTEMIC_ADMISSION_CONTRACT_ID = "aasm.reasoning.admission.v1"
EPISTEMIC_ADMISSION_CONTRACT_VERSION = "0.1.0"
REASONING_COMMIT_CONTRACT_ID = "aasm.reasoning.commit.v1"
REASONING_COMMIT_CONTRACT_VERSION = "0.1.0"

REASONING_ARTIFACT_KINDS = (
    "Claim",
    "Hypothesis",
    "Lemma",
    "Invariant",
    "Counterexample",
    "Definition",
    "Assumption",
    "Observation",
    "Derivation",
    "Refutation",
    "ObjectiveResult",
)
REASONING_AUTHORITY_CLASSES = ("PROPOSER", "OBSERVER", "VERIFIER", "POLICY", "CONTROLLER")
REASONING_STATES = (
    "PROPOSED",
    "SUPPORTED",
    "CONTESTED",
    "VERIFICATION_REQUESTED",
    "VERIFIED",
    "AUTHORIZED",
    "REFUTED",
    "STALE",
    "REJECTED",
)
REASONING_ACTIONS = (
    "SUPPORT",
    "CONTEST",
    "REQUEST_VERIFICATION",
    "VERIFY",
    "AUTHORIZE",
    "REFUTE",
    "STALE",
    "REJECT",
)
TERMINAL_REASONING_STATES = {"REFUTED", "REJECTED"}

_VERIFY_AUTHORITIES = {"VERIFIER", "CONTROLLER"}
_AUTHORIZE_AUTHORITIES = {"POLICY", "CONTROLLER"}
_REFUTE_AUTHORITIES = {"VERIFIER", "POLICY", "CONTROLLER"}
_STALE_AUTHORITIES = {"VERIFIER", "POLICY", "CONTROLLER"}
_REJECT_AUTHORITIES = {"POLICY", "CONTROLLER"}


def _jsonable(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        return _jsonable(value.to_dict())
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    raise TypeError(f"reasoning value is not JSON serializable: {type(value)!r}")


@dataclass(frozen=True)
class ReasoningProducer:
    producer_id: str
    authority_class: str = "PROPOSER"
    version: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.producer_id:
            raise ValueError("reasoning producer_id is required")
        if self.authority_class not in REASONING_AUTHORITY_CLASSES:
            raise ValueError(f"invalid reasoning authority class: {self.authority_class}")
        _jsonable(self.metadata)

    def to_dict(self) -> dict[str, Any]:
        return _jsonable(asdict(self))


@dataclass(frozen=True)
class VerifierRequirement:
    verifier_id: str
    required_verdict: str = "PASS"
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.verifier_id:
            raise ValueError("verifier_id is required")
        if self.required_verdict not in {"PASS"}:
            raise ValueError("required_verdict must be PASS")
        _jsonable(self.metadata)

    def to_dict(self) -> dict[str, Any]:
        return _jsonable(asdict(self))


@dataclass(frozen=True)
class ReasoningArtifact:
    kind: str
    statement: str
    producer: ReasoningProducer | dict[str, Any]
    subject_ids: tuple[str, ...] = ()
    premise_artifact_ids: tuple[str, ...] = ()
    evidence_ids: tuple[str, ...] = ()
    verifier_requirements: tuple[VerifierRequirement | dict[str, Any], ...] = ()
    confidence: float | None = None
    scope: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    artifact_id: str = ""

    def __post_init__(self):
        if self.kind not in REASONING_ARTIFACT_KINDS:
            raise ValueError(f"invalid reasoning artifact kind: {self.kind}")
        if not self.statement.strip():
            raise ValueError("reasoning artifact statement is required")
        producer = self.producer if isinstance(self.producer, ReasoningProducer) else ReasoningProducer(**deepcopy(self.producer))
        requirements = tuple(
            item if isinstance(item, VerifierRequirement) else VerifierRequirement(**deepcopy(item))
            for item in self.verifier_requirements
        )
        object.__setattr__(self, "producer", producer)
        object.__setattr__(self, "verifier_requirements", requirements)
        object.__setattr__(self, "subject_ids", tuple(sorted(set(str(value) for value in self.subject_ids))))
        object.__setattr__(self, "premise_artifact_ids", tuple(sorted(set(str(value) for value in self.premise_artifact_ids))))
        object.__setattr__(self, "evidence_ids", tuple(sorted(set(str(value) for value in self.evidence_ids))))
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            raise ValueError("reasoning artifact confidence must be between 0 and 1")
        _jsonable(self.scope)
        _jsonable(self.metadata)
        if not self.artifact_id:
            derived = semantic_fingerprint(self.identity_payload())[:20]
            object.__setattr__(self, "artifact_id", f"artifact-{derived}")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "statement": self.statement,
            "producer": self.producer.to_dict(),
            "subject_ids": list(self.subject_ids),
            "premise_artifact_ids": list(self.premise_artifact_ids),
            "evidence_ids": list(self.evidence_ids),
            "verifier_requirements": [row.to_dict() for row in self.verifier_requirements],
            "confidence": self.confidence,
            "scope": _jsonable(self.scope),
            "metadata": _jsonable(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"artifact_id": self.artifact_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"artifact_id": self.artifact_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ReasoningArtifact":
        payload = deepcopy(dict(data))
        payload.pop("fingerprint", None)
        return cls(**payload)


class Claim(ReasoningArtifact):
    def __init__(self, statement: str, producer: ReasoningProducer | dict[str, Any], **kwargs):
        super().__init__(kind="Claim", statement=statement, producer=producer, **kwargs)


class Hypothesis(ReasoningArtifact):
    def __init__(self, statement: str, producer: ReasoningProducer | dict[str, Any], **kwargs):
        super().__init__(kind="Hypothesis", statement=statement, producer=producer, **kwargs)


class Lemma(ReasoningArtifact):
    def __init__(self, statement: str, producer: ReasoningProducer | dict[str, Any], **kwargs):
        super().__init__(kind="Lemma", statement=statement, producer=producer, **kwargs)


class Invariant(ReasoningArtifact):
    def __init__(self, statement: str, producer: ReasoningProducer | dict[str, Any], **kwargs):
        super().__init__(kind="Invariant", statement=statement, producer=producer, **kwargs)


class Counterexample(ReasoningArtifact):
    def __init__(self, statement: str, producer: ReasoningProducer | dict[str, Any], **kwargs):
        super().__init__(kind="Counterexample", statement=statement, producer=producer, **kwargs)


class Definition(ReasoningArtifact):
    def __init__(self, statement: str, producer: ReasoningProducer | dict[str, Any], **kwargs):
        super().__init__(kind="Definition", statement=statement, producer=producer, **kwargs)


class Assumption(ReasoningArtifact):
    def __init__(self, statement: str, producer: ReasoningProducer | dict[str, Any], **kwargs):
        super().__init__(kind="Assumption", statement=statement, producer=producer, **kwargs)


class Observation(ReasoningArtifact):
    def __init__(self, statement: str, producer: ReasoningProducer | dict[str, Any], **kwargs):
        super().__init__(kind="Observation", statement=statement, producer=producer, **kwargs)


class Derivation(ReasoningArtifact):
    def __init__(self, statement: str, producer: ReasoningProducer | dict[str, Any], **kwargs):
        super().__init__(kind="Derivation", statement=statement, producer=producer, **kwargs)


class Refutation(ReasoningArtifact):
    def __init__(self, statement: str, producer: ReasoningProducer | dict[str, Any], **kwargs):
        super().__init__(kind="Refutation", statement=statement, producer=producer, **kwargs)


class ObjectiveResult(ReasoningArtifact):
    def __init__(self, statement: str, producer: ReasoningProducer | dict[str, Any], **kwargs):
        super().__init__(kind="ObjectiveResult", statement=statement, producer=producer, **kwargs)


@dataclass(frozen=True)
class ReasoningTransition:
    artifact_id: str
    action: str
    actor_id: str
    authority_class: str
    evidence_ids: tuple[str, ...] = ()
    related_artifact_ids: tuple[str, ...] = ()
    verifier_ids: tuple[str, ...] = ()
    verdict: str | None = None
    reason: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.artifact_id or not self.actor_id:
            raise ValueError("artifact_id and actor_id are required")
        if self.action not in REASONING_ACTIONS:
            raise ValueError(f"invalid reasoning action: {self.action}")
        if self.authority_class not in REASONING_AUTHORITY_CLASSES:
            raise ValueError(f"invalid reasoning authority class: {self.authority_class}")
        object.__setattr__(self, "evidence_ids", tuple(sorted(set(str(value) for value in self.evidence_ids))))
        object.__setattr__(self, "related_artifact_ids", tuple(sorted(set(str(value) for value in self.related_artifact_ids))))
        object.__setattr__(self, "verifier_ids", tuple(sorted(set(str(value) for value in self.verifier_ids))))
        if self.verdict is not None and self.verdict not in {"PASS", "FAIL"}:
            raise ValueError("verification verdict must be PASS or FAIL")
        _jsonable(self.metadata)

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(self.payload())

    def payload(self) -> dict[str, Any]:
        return _jsonable(asdict(self))

    def to_dict(self) -> dict[str, Any]:
        return {**self.payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ReasoningTransition":
        payload = deepcopy(dict(data))
        payload.pop("fingerprint", None)
        return cls(**payload)


@dataclass(frozen=True)
class ReasoningCommit:
    artifact_fingerprints: dict[str, str]
    authority_id: str
    authority_class: str
    parent_commit_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    commit_id: str = ""

    def __post_init__(self):
        if not self.artifact_fingerprints:
            raise ValueError("reasoning commit requires at least one artifact")
        if not self.authority_id:
            raise ValueError("reasoning commit authority_id is required")
        if self.authority_class not in _AUTHORIZE_AUTHORITIES:
            raise PermissionError("reasoning commit requires POLICY or CONTROLLER authority")
        normalized = {str(key): str(value) for key, value in sorted(self.artifact_fingerprints.items())}
        object.__setattr__(self, "artifact_fingerprints", normalized)
        _jsonable(self.metadata)
        if not self.commit_id:
            derived = semantic_fingerprint(self.identity_payload())[:20]
            object.__setattr__(self, "commit_id", f"reasoning-commit-{derived}")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "artifact_fingerprints": dict(self.artifact_fingerprints),
            "authority_id": self.authority_id,
            "authority_class": self.authority_class,
            "parent_commit_id": self.parent_commit_id,
            "metadata": _jsonable(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"commit_id": self.commit_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"commit_id": self.commit_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ReasoningCommit":
        payload = deepcopy(dict(data))
        payload.pop("fingerprint", None)
        return cls(**payload)


def reasoning_contract() -> dict[str, Any]:
    return {
        "artifact_contract_id": REASONING_ARTIFACT_CONTRACT_ID,
        "artifact_contract_version": REASONING_ARTIFACT_CONTRACT_VERSION,
        "admission_contract_id": EPISTEMIC_ADMISSION_CONTRACT_ID,
        "admission_contract_version": EPISTEMIC_ADMISSION_CONTRACT_VERSION,
        "commit_contract_id": REASONING_COMMIT_CONTRACT_ID,
        "commit_contract_version": REASONING_COMMIT_CONTRACT_VERSION,
        "artifact_kinds": list(REASONING_ARTIFACT_KINDS),
        "states": list(REASONING_STATES),
        "actions": list(REASONING_ACTIONS),
        "authority_classes": list(REASONING_AUTHORITY_CLASSES),
        "compiler_authority": "PROPOSAL_ONLY",
        "epistemic_admission": "POLICY_ADMITS",
        "durability_boundary": "AASM_EVIDENCE_EVENT_REDUCER_ONLY",
        "provenance": "APPEND_ONLY",
        "self_verification": "REJECTED",
        "direct_store_write": "NOT_AN_ADMISSION_PATH",
        "dependency_truth_maintenance": "RESERVED_FOR_V0.38",
    }


def _required_verifiers(artifact: ReasoningArtifact) -> set[str]:
    return {item.verifier_id for item in artifact.verifier_requirements}


def _verification_passes(entry: Mapping[str, Any]) -> set[str]:
    passes: set[str] = set()
    for row in entry.get("verifications", []):
        if row.get("verdict") == "PASS":
            passes.add(str(row.get("actor_id")))
    return passes


def _verification_complete(entry: Mapping[str, Any]) -> bool:
    artifact = ReasoningArtifact.from_dict(entry["artifact"])
    required = _required_verifiers(artifact)
    passes = _verification_passes(entry)
    return required.issubset(passes) if required else bool(passes)


def next_reasoning_state(current: str, transition: ReasoningTransition, entry: Mapping[str, Any] | None = None) -> str:
    if current not in REASONING_STATES:
        raise ValueError(f"unknown reasoning state: {current}")
    if current in TERMINAL_REASONING_STATES:
        raise ValueError(f"reasoning artifact is terminal: {current}")

    action = transition.action
    if action == "SUPPORT":
        if current not in {"PROPOSED", "SUPPORTED"}:
            raise ValueError(f"SUPPORT is invalid from {current}")
        return "SUPPORTED"
    if action == "CONTEST":
        if current not in {"PROPOSED", "SUPPORTED", "VERIFICATION_REQUESTED", "VERIFIED", "AUTHORIZED"}:
            raise ValueError(f"CONTEST is invalid from {current}")
        return "CONTESTED"
    if action == "REQUEST_VERIFICATION":
        if current not in {"PROPOSED", "SUPPORTED", "CONTESTED", "VERIFICATION_REQUESTED"}:
            raise ValueError(f"REQUEST_VERIFICATION is invalid from {current}")
        if not transition.verifier_ids:
            raise ValueError("verification request requires at least one verifier")
        return "VERIFICATION_REQUESTED"
    if action == "VERIFY":
        if current != "VERIFICATION_REQUESTED":
            raise ValueError(f"VERIFY is invalid from {current}")
        if transition.verdict == "FAIL":
            return "CONTESTED"
        if transition.verdict != "PASS":
            raise ValueError("VERIFY requires PASS or FAIL verdict")
        if entry is None:
            return "VERIFIED"
        simulated = deepcopy(dict(entry))
        simulated.setdefault("verifications", []).append(transition.to_dict())
        return "VERIFIED" if _verification_complete(simulated) else "VERIFICATION_REQUESTED"
    if action == "AUTHORIZE":
        if current != "VERIFIED":
            raise ValueError(f"AUTHORIZE is invalid from {current}")
        if transition.authority_class not in _AUTHORIZE_AUTHORITIES:
            raise PermissionError("artifact authorization requires POLICY or CONTROLLER authority")
        return "AUTHORIZED"
    if action == "REFUTE":
        if current not in {"CONTESTED", "VERIFICATION_REQUESTED", "VERIFIED", "AUTHORIZED"}:
            raise ValueError(f"REFUTE is invalid from {current}")
        if transition.authority_class not in _REFUTE_AUTHORITIES:
            raise PermissionError("artifact refutation requires VERIFIER, POLICY, or CONTROLLER authority")
        return "REFUTED"
    if action == "STALE":
        if current not in {"PROPOSED", "SUPPORTED", "CONTESTED", "VERIFICATION_REQUESTED", "VERIFIED", "AUTHORIZED", "STALE"}:
            raise ValueError(f"STALE is invalid from {current}")
        if transition.authority_class not in _STALE_AUTHORITIES:
            raise PermissionError("marking an artifact stale requires VERIFIER, POLICY, or CONTROLLER authority")
        return "STALE"
    if action == "REJECT":
        if current not in {"PROPOSED", "SUPPORTED", "CONTESTED", "VERIFICATION_REQUESTED"}:
            raise ValueError(f"REJECT is invalid from {current}")
        if transition.authority_class not in _REJECT_AUTHORITIES:
            raise PermissionError("artifact rejection requires POLICY or CONTROLLER authority")
        return "REJECTED"
    raise ValueError(f"unsupported reasoning action: {action}")


def project_reasoning_evidence(records: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    artifacts: dict[str, dict[str, Any]] = {}
    commits: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []

    for index, raw in enumerate(records):
        row = deepcopy(dict(raw))
        metadata = dict(row.get("metadata") or {})
        record_type = metadata.get("reasoning_record_type")
        if record_type not in {"ARTIFACT", "TRANSITION", "COMMIT"}:
            continue
        evidence_id = str(row.get("evidence_id") or "")
        try:
            document = row.get("statement") or "{}"
            payload = document if isinstance(document, Mapping) else __import__("json").loads(document)
            if record_type == "ARTIFACT":
                artifact = ReasoningArtifact.from_dict(payload)
                if artifact.artifact_id in artifacts:
                    raise ValueError(f"duplicate reasoning artifact: {artifact.artifact_id}")
                if metadata.get("reasoning_contract_id") != REASONING_ARTIFACT_CONTRACT_ID:
                    raise ValueError("artifact reasoning contract mismatch")
                if metadata.get("artifact_fingerprint") != artifact.fingerprint:
                    raise ValueError("artifact fingerprint mismatch")
                artifacts[artifact.artifact_id] = {
                    "artifact": artifact.to_dict(),
                    "proposal_evidence_id": evidence_id,
                    "state": "PROPOSED",
                    "history": [],
                    "supports": [],
                    "contests": [],
                    "verification_requests": [],
                    "verifications": [],
                    "authorizations": [],
                    "refutations": [],
                    "stale_events": [],
                    "rejections": [],
                }
            elif record_type == "TRANSITION":
                transition = ReasoningTransition.from_dict(payload)
                if metadata.get("reasoning_contract_id") != EPISTEMIC_ADMISSION_CONTRACT_ID:
                    raise ValueError("transition reasoning contract mismatch")
                if metadata.get("transition_fingerprint") != transition.fingerprint:
                    raise ValueError("transition fingerprint mismatch")
                if transition.artifact_id not in artifacts:
                    raise KeyError(f"unknown reasoning artifact: {transition.artifact_id}")
                entry = artifacts[transition.artifact_id]
                current = entry["state"]
                target = next_reasoning_state(current, transition, entry)
                history_row = {
                    "evidence_id": evidence_id,
                    "from_state": current,
                    "to_state": target,
                    **transition.to_dict(),
                }
                entry["history"].append(history_row)
                bucket = {
                    "SUPPORT": "supports",
                    "CONTEST": "contests",
                    "REQUEST_VERIFICATION": "verification_requests",
                    "VERIFY": "verifications",
                    "AUTHORIZE": "authorizations",
                    "REFUTE": "refutations",
                    "STALE": "stale_events",
                    "REJECT": "rejections",
                }[transition.action]
                entry[bucket].append(history_row)
                entry["state"] = target
            elif record_type == "COMMIT":
                if metadata.get("reasoning_contract_id") != REASONING_COMMIT_CONTRACT_ID:
                    raise ValueError("reasoning commit contract mismatch")
                commit = ReasoningCommit.from_dict(payload)
                if metadata.get("commit_fingerprint") != commit.fingerprint:
                    raise ValueError("reasoning commit fingerprint mismatch")
                missing = sorted(set(commit.artifact_fingerprints) - set(artifacts))
                if missing:
                    raise KeyError(f"reasoning commit references unknown artifacts: {missing}")
                mismatched = sorted(
                    artifact_id for artifact_id, fingerprint in commit.artifact_fingerprints.items()
                    if artifacts[artifact_id]["artifact"]["fingerprint"] != fingerprint
                )
                if mismatched:
                    raise ValueError(f"reasoning commit fingerprint mismatch for artifacts: {mismatched}")
                unauthorized = sorted(
                    artifact_id for artifact_id in commit.artifact_fingerprints
                    if artifacts[artifact_id]["state"] != "AUTHORIZED"
                )
                if unauthorized:
                    raise ValueError(f"reasoning commit contains non-authorized artifacts: {unauthorized}")
                commits.append({"evidence_id": evidence_id, **commit.to_dict()})
        except Exception as exc:
            issues.append({
                "record_index": index,
                "evidence_id": evidence_id,
                "record_type": record_type,
                "error": f"{type(exc).__name__}: {exc}",
            })

    return {
        "contract": reasoning_contract(),
        "valid": not issues,
        "issues": issues,
        "artifacts": artifacts,
        "commits": commits,
        "latest_commit": commits[-1] if commits else None,
        "artifact_count": len(artifacts),
        "commit_count": len(commits),
        "projection_fingerprint": semantic_fingerprint({
            "artifacts": artifacts,
            "commits": commits,
            "issues": issues,
        }),
    }


def reasoning_artifact_document(artifact: ReasoningArtifact) -> str:
    return canonical_semantic_json(artifact.to_dict())


def reasoning_transition_document(transition: ReasoningTransition) -> str:
    return canonical_semantic_json(transition.to_dict())


def reasoning_commit_document(commit: ReasoningCommit) -> str:
    return canonical_semantic_json(commit.to_dict())


def run_reasoning_conformance() -> dict[str, Any]:
    from .evidence import EvidenceRecord
    from .model import ProblemSpec
    from .runtime_v32 import AASMEngine

    engine = AASMEngine(ProblemSpec("reasoning conformance"))
    observation = engine.add_evidence(EvidenceRecord("observation", "fixture observation", source="conformance"))
    artifact = Claim(
        "fixture claim",
        ReasoningProducer("agent-a", "PROPOSER"),
        evidence_ids=(observation.evidence_id,),
        verifier_requirements=(VerifierRequirement("verifier-b"),),
    )
    proposed = engine.propose_artifact(artifact)

    self_verification_rejected = False
    try:
        engine.request_verification(artifact.artifact_id, verifier_ids=["agent-a"], requester_id="agent-a")
        engine.record_verification(
            artifact.artifact_id,
            verifier_id="agent-a",
            verdict="PASS",
            evidence_ids=[observation.evidence_id],
        )
    except ValueError:
        self_verification_rejected = True

    engine.request_verification(artifact.artifact_id, verifier_ids=["verifier-b"], requester_id="agent-a")
    engine.record_verification(
        artifact.artifact_id,
        verifier_id="verifier-b",
        verdict="PASS",
        evidence_ids=[observation.evidence_id],
    )

    low_authority_rejected = False
    try:
        engine.authorize_artifact(artifact.artifact_id, authority_id="agent-a", authority_class="PROPOSER")
    except PermissionError:
        low_authority_rejected = True

    authorized = engine.authorize_artifact(
        artifact.artifact_id,
        authority_id="policy-1",
        authority_class="POLICY",
    )
    commit = engine.reasoning_commit(
        [artifact.artifact_id],
        authority_id="policy-1",
        authority_class="POLICY",
    )

    nonexistent_evidence_rejected = False
    second = Hypothesis("second fixture", ReasoningProducer("agent-c", "PROPOSER"))
    engine.propose_artifact(second)
    try:
        engine.support_artifact(
            second.artifact_id,
            supporter_id="agent-c",
            evidence_ids=["evidence-does-not-exist"],
        )
    except KeyError:
        nonexistent_evidence_rejected = True

    replay_projection = project_reasoning_evidence(engine.replay().evidence.get("records", []))
    live_projection = engine.reasoning_report()
    tampered_records = deepcopy(engine.snapshot.evidence.get("records", []))
    tampered_records.append({
        "evidence_id": "tampered",
        "kind": "reasoning_transition",
        "statement": canonical_semantic_json({
            "artifact_id": "missing-artifact",
            "action": "AUTHORIZE",
            "actor_id": "intruder",
            "authority_class": "CONTROLLER",
        }),
        "metadata": {
            "reasoning_record_type": "TRANSITION",
            "reasoning_contract_id": EPISTEMIC_ADMISSION_CONTRACT_ID,
            "transition_fingerprint": "not-valid",
        },
    })
    tampered = project_reasoning_evidence(tampered_records)

    checks = {
        "artifact_proposed": proposed["artifact"]["artifact_id"] == artifact.artifact_id,
        "self_verification_rejected": self_verification_rejected,
        "independent_verification_required": authorized["state"] == "AUTHORIZED",
        "low_authority_rejected": low_authority_rejected,
        "nonexistent_evidence_rejected": nonexistent_evidence_rejected,
        "reasoning_commit_authorized_only": commit["commit"]["artifact_fingerprints"][artifact.artifact_id] == artifact.fingerprint,
        "exact_replay_projection": replay_projection["projection_fingerprint"] == live_projection["projection_fingerprint"],
        "direct_mutation_not_admitted": tampered["valid"] is False,
    }
    report = {
        "contract_id": EPISTEMIC_ADMISSION_CONTRACT_ID,
        "contract_version": EPISTEMIC_ADMISSION_CONTRACT_VERSION,
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "reasoning_projection_fingerprint": live_projection["projection_fingerprint"],
    }
    report["report_sha256"] = semantic_fingerprint(report)
    return report


__all__ = [
    "REASONING_ARTIFACT_CONTRACT_ID",
    "REASONING_ARTIFACT_CONTRACT_VERSION",
    "EPISTEMIC_ADMISSION_CONTRACT_ID",
    "EPISTEMIC_ADMISSION_CONTRACT_VERSION",
    "REASONING_COMMIT_CONTRACT_ID",
    "REASONING_COMMIT_CONTRACT_VERSION",
    "REASONING_ARTIFACT_KINDS",
    "REASONING_AUTHORITY_CLASSES",
    "REASONING_STATES",
    "REASONING_ACTIONS",
    "ReasoningProducer",
    "VerifierRequirement",
    "ReasoningArtifact",
    "Claim",
    "Hypothesis",
    "Lemma",
    "Invariant",
    "Counterexample",
    "Definition",
    "Assumption",
    "Observation",
    "Derivation",
    "Refutation",
    "ObjectiveResult",
    "ReasoningTransition",
    "ReasoningCommit",
    "reasoning_contract",
    "next_reasoning_state",
    "project_reasoning_evidence",
    "reasoning_artifact_document",
    "reasoning_transition_document",
    "reasoning_commit_document",
    "run_reasoning_conformance",
]
