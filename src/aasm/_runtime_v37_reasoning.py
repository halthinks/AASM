from __future__ import annotations

from copy import deepcopy
from typing import Any, Sequence

from .evidence import EvidenceRecord
from .reasoning import (
    EPISTEMIC_ADMISSION_CONTRACT_ID,
    REASONING_ARTIFACT_CONTRACT_ID,
    REASONING_COMMIT_CONTRACT_ID,
    ReasoningArtifact,
    ReasoningCommit,
    ReasoningTransition,
    next_reasoning_state,
    project_reasoning_evidence,
    reasoning_artifact_document,
    reasoning_commit_document,
    reasoning_contract,
    reasoning_transition_document,
)


class ReasoningRuntimeMixin:
    """Event-sourced v0.37 reasoning and epistemic-admission surface."""

    def _reasoning_projection(self) -> dict[str, Any]:
        records = self.snapshot.evidence.get("records", []) if isinstance(self.snapshot.evidence, dict) else []
        return project_reasoning_evidence(records)

    def _reasoning_entry(self, artifact_id: str) -> dict[str, Any]:
        projection = self._reasoning_projection()
        if not projection["valid"]:
            raise RuntimeError(f"invalid durable reasoning projection: {projection['issues']}")
        try:
            return projection["artifacts"][artifact_id]
        except KeyError:
            raise KeyError(artifact_id) from None

    def _require_evidence_ids(self, ids: Sequence[str]) -> list[str]:
        values = sorted(set(map(str, ids)))
        known = {str(row.get("evidence_id")) for row in self.snapshot.evidence.get("records", [])}
        missing = [value for value in values if value not in known]
        if missing:
            raise KeyError(f"unknown evidence references: {missing}")
        return values

    def _proposal_evidence_ids(self, artifact_ids: Sequence[str]) -> list[str]:
        projection = self._reasoning_projection()
        if not projection["valid"]:
            raise RuntimeError(f"invalid durable reasoning projection: {projection['issues']}")
        ids = sorted(set(map(str, artifact_ids)))
        missing = [value for value in ids if value not in projection["artifacts"]]
        if missing:
            raise KeyError(f"unknown reasoning artifacts: {missing}")
        return sorted({projection["artifacts"][value]["proposal_evidence_id"] for value in ids})

    def propose_artifact(self, artifact: ReasoningArtifact | dict[str, Any], *, reason: str = "reasoning artifact proposed") -> dict[str, Any]:
        artifact = artifact if isinstance(artifact, ReasoningArtifact) else ReasoningArtifact.from_dict(artifact)
        projection = self._reasoning_projection()
        if not projection["valid"]:
            raise RuntimeError(f"invalid durable reasoning projection: {projection['issues']}")
        if artifact.artifact_id in projection["artifacts"]:
            raise ValueError(f"reasoning artifact already exists: {artifact.artifact_id}")
        evidence = self._require_evidence_ids(artifact.evidence_ids)
        premises = self._proposal_evidence_ids(artifact.premise_artifact_ids) if artifact.premise_artifact_ids else []
        stored = self.add_evidence(EvidenceRecord(
            kind="reasoning_artifact",
            statement=reasoning_artifact_document(artifact),
            source=REASONING_ARTIFACT_CONTRACT_ID,
            confidence=artifact.confidence,
            derived_from=sorted(set([*evidence, *premises])),
            metadata={
                "reasoning_record_type": "ARTIFACT",
                "reasoning_contract_id": REASONING_ARTIFACT_CONTRACT_ID,
                "artifact_id": artifact.artifact_id,
                "artifact_kind": artifact.kind,
                "artifact_fingerprint": artifact.fingerprint,
                "producer_id": artifact.producer.producer_id,
                "authority_class": artifact.producer.authority_class,
                "scope": deepcopy(artifact.scope),
            },
        ), reason=reason)
        out = self.reasoning_report(artifact.artifact_id)
        out["proposal_evidence_id"] = stored.evidence_id
        return out

    def _record_reasoning_transition(self, transition: ReasoningTransition, *, reason: str) -> dict[str, Any]:
        entry = self._reasoning_entry(transition.artifact_id)
        evidence = self._require_evidence_ids(transition.evidence_ids)
        related = self._proposal_evidence_ids(transition.related_artifact_ids) if transition.related_artifact_ids else []
        next_reasoning_state(entry["state"], transition, entry)
        parents = [entry["proposal_evidence_id"]]
        if entry["history"]:
            parents.append(entry["history"][-1]["evidence_id"])
        stored = self.add_evidence(EvidenceRecord(
            kind="reasoning_transition",
            statement=reasoning_transition_document(transition),
            source=EPISTEMIC_ADMISSION_CONTRACT_ID,
            derived_from=sorted(set([*parents, *evidence, *related])),
            metadata={
                "reasoning_record_type": "TRANSITION",
                "reasoning_contract_id": EPISTEMIC_ADMISSION_CONTRACT_ID,
                "artifact_id": transition.artifact_id,
                "action": transition.action,
                "actor_id": transition.actor_id,
                "authority_class": transition.authority_class,
                "transition_fingerprint": transition.fingerprint,
            },
        ), reason=reason)
        out = self.reasoning_report(transition.artifact_id)
        out["transition_evidence_id"] = stored.evidence_id
        return out

    def support_artifact(self, artifact_id: str, *, supporter_id: str, authority_class: str = "PROPOSER",
                         evidence_ids: Sequence[str] = (), supporting_artifact_ids: Sequence[str] = (),
                         reason: str = "reasoning artifact supported") -> dict[str, Any]:
        if not evidence_ids and not supporting_artifact_ids:
            raise ValueError("support requires evidence_ids or supporting_artifact_ids")
        return self._record_reasoning_transition(ReasoningTransition(
            artifact_id, "SUPPORT", supporter_id, authority_class, tuple(evidence_ids),
            tuple(supporting_artifact_ids), reason=reason,
        ), reason=reason)

    def contest_artifact(self, artifact_id: str, *, contester_id: str, authority_class: str = "PROPOSER",
                         evidence_ids: Sequence[str] = (), counter_artifact_ids: Sequence[str] = (),
                         reason: str = "reasoning artifact contested") -> dict[str, Any]:
        if not evidence_ids and not counter_artifact_ids:
            raise ValueError("contest requires evidence_ids or counter_artifact_ids")
        return self._record_reasoning_transition(ReasoningTransition(
            artifact_id, "CONTEST", contester_id, authority_class, tuple(evidence_ids),
            tuple(counter_artifact_ids), reason=reason,
        ), reason=reason)

    def request_verification(self, artifact_id: str, *, verifier_ids: Sequence[str], requester_id: str,
                             authority_class: str = "PROPOSER",
                             reason: str = "reasoning artifact verification requested") -> dict[str, Any]:
        return self._record_reasoning_transition(ReasoningTransition(
            artifact_id=artifact_id, action="REQUEST_VERIFICATION", actor_id=requester_id,
            authority_class=authority_class, verifier_ids=tuple(verifier_ids), reason=reason,
        ), reason=reason)

    def record_verification(self, artifact_id: str, *, verifier_id: str, verdict: str,
                            evidence_ids: Sequence[str] = (), related_artifact_ids: Sequence[str] = (),
                            authority_class: str = "VERIFIER",
                            reason: str = "reasoning artifact verification recorded",
                            metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        entry = self._reasoning_entry(artifact_id)
        artifact = ReasoningArtifact.from_dict(entry["artifact"])
        if verifier_id == artifact.producer.producer_id:
            raise ValueError("self-verification is not an admissible reasoning transition")
        if authority_class not in {"VERIFIER", "CONTROLLER"}:
            raise PermissionError("recording verification requires VERIFIER or CONTROLLER authority")
        if not evidence_ids and not related_artifact_ids:
            raise ValueError("verification requires evidence_ids or related_artifact_ids")
        requested = {v for row in entry["verification_requests"] for v in row.get("verifier_ids", [])}
        required = {row.verifier_id for row in artifact.verifier_requirements}
        if verifier_id not in requested and verifier_id not in required:
            raise ValueError(f"verifier {verifier_id} was not requested and is not a required verifier")
        return self._record_reasoning_transition(ReasoningTransition(
            artifact_id=artifact_id, action="VERIFY", actor_id=verifier_id, authority_class=authority_class,
            evidence_ids=tuple(evidence_ids), related_artifact_ids=tuple(related_artifact_ids),
            verdict=verdict, reason=reason, metadata=deepcopy(metadata or {}),
        ), reason=reason)

    def authorize_artifact(self, artifact_id: str, *, authority_id: str, authority_class: str,
                           evidence_ids: Sequence[str] = (),
                           reason: str = "reasoning artifact authorized") -> dict[str, Any]:
        if authority_class not in {"POLICY", "CONTROLLER"}:
            raise PermissionError("artifact authorization requires POLICY or CONTROLLER authority")
        entry = self._reasoning_entry(artifact_id)
        if entry["state"] != "VERIFIED":
            raise ValueError(f"artifact authorization requires VERIFIED state, found {entry['state']}")
        verification = [row["evidence_id"] for row in entry["verifications"] if row.get("verdict") == "PASS"]
        return self._record_reasoning_transition(ReasoningTransition(
            artifact_id=artifact_id, action="AUTHORIZE", actor_id=authority_id, authority_class=authority_class,
            evidence_ids=tuple(sorted(set([*evidence_ids, *verification]))), reason=reason,
        ), reason=reason)

    def refute_artifact(self, artifact_id: str, *, verifier_id: str, evidence_ids: Sequence[str] = (),
                        refutation_artifact_ids: Sequence[str] = (), authority_class: str = "VERIFIER",
                        reason: str = "reasoning artifact refuted") -> dict[str, Any]:
        if authority_class not in {"VERIFIER", "POLICY", "CONTROLLER"}:
            raise PermissionError("artifact refutation requires VERIFIER, POLICY, or CONTROLLER authority")
        if not evidence_ids and not refutation_artifact_ids:
            raise ValueError("refutation requires evidence_ids or refutation_artifact_ids")
        artifact = ReasoningArtifact.from_dict(self._reasoning_entry(artifact_id)["artifact"])
        if verifier_id == artifact.producer.producer_id:
            raise ValueError("artifact producer cannot self-refute through the verifier authority path")
        return self._record_reasoning_transition(ReasoningTransition(
            artifact_id=artifact_id, action="REFUTE", actor_id=verifier_id, authority_class=authority_class,
            evidence_ids=tuple(evidence_ids), related_artifact_ids=tuple(refutation_artifact_ids), reason=reason,
        ), reason=reason)

    def mark_stale(self, artifact_id: str, *, reason: str, authority_id: str,
                   authority_class: str = "VERIFIER", evidence_ids: Sequence[str] = ()) -> dict[str, Any]:
        if not reason.strip():
            raise ValueError("mark_stale requires a reason")
        return self._record_reasoning_transition(ReasoningTransition(
            artifact_id=artifact_id, action="STALE", actor_id=authority_id, authority_class=authority_class,
            evidence_ids=tuple(evidence_ids), reason=reason,
        ), reason=reason)

    def reject_artifact(self, artifact_id: str, *, authority_id: str, authority_class: str,
                        reason: str, evidence_ids: Sequence[str] = ()) -> dict[str, Any]:
        if not reason.strip():
            raise ValueError("reject_artifact requires a reason")
        return self._record_reasoning_transition(ReasoningTransition(
            artifact_id=artifact_id, action="REJECT", actor_id=authority_id, authority_class=authority_class,
            evidence_ids=tuple(evidence_ids), reason=reason,
        ), reason=reason)

    def reasoning_commit(self, artifact_ids: Sequence[str], *, authority_id: str, authority_class: str,
                         metadata: dict[str, Any] | None = None,
                         reason: str = "reasoning commit recorded") -> dict[str, Any]:
        projection = self._reasoning_projection()
        if not projection["valid"]:
            raise RuntimeError(f"invalid durable reasoning projection: {projection['issues']}")
        selected = sorted(set(map(str, artifact_ids)))
        if not selected:
            raise ValueError("reasoning commit requires artifact_ids")
        missing = [value for value in selected if value not in projection["artifacts"]]
        if missing:
            raise KeyError(f"unknown reasoning artifacts: {missing}")
        unauthorized = [value for value in selected if projection["artifacts"][value]["state"] != "AUTHORIZED"]
        if unauthorized:
            raise ValueError(f"reasoning commit requires AUTHORIZED artifacts: {unauthorized}")
        commit = ReasoningCommit(
            {value: projection["artifacts"][value]["artifact"]["fingerprint"] for value in selected},
            authority_id, authority_class,
            projection["latest_commit"]["commit_id"] if projection["latest_commit"] else None,
            deepcopy(metadata or {}),
        )
        derived = [
            (projection["artifacts"][value]["history"][-1]["evidence_id"]
             if projection["artifacts"][value]["history"]
             else projection["artifacts"][value]["proposal_evidence_id"])
            for value in selected
        ]
        if projection["latest_commit"]:
            derived.append(projection["latest_commit"]["evidence_id"])
        stored = self.add_evidence(EvidenceRecord(
            kind="reasoning_commit",
            statement=reasoning_commit_document(commit),
            source=REASONING_COMMIT_CONTRACT_ID,
            derived_from=sorted(set(derived)),
            metadata={
                "reasoning_record_type": "COMMIT",
                "reasoning_contract_id": REASONING_COMMIT_CONTRACT_ID,
                "commit_id": commit.commit_id,
                "commit_fingerprint": commit.fingerprint,
                "authority_id": authority_id,
                "authority_class": authority_class,
            },
        ), reason=reason)
        return {
            "contract": reasoning_contract(),
            "evidence_id": stored.evidence_id,
            "commit": commit.to_dict(),
            "projection_fingerprint": self._reasoning_projection()["projection_fingerprint"],
        }

    def reasoning_report(self, artifact_id: str | None = None) -> dict[str, Any]:
        projection = self._reasoning_projection()
        if artifact_id is None:
            return projection
        try:
            entry = projection["artifacts"][artifact_id]
        except KeyError:
            raise KeyError(artifact_id) from None
        return {
            "contract": projection["contract"], "valid": projection["valid"], "issues": projection["issues"],
            "projection_fingerprint": projection["projection_fingerprint"], **deepcopy(entry),
        }

    def reasoning_provenance(self, artifact_id: str) -> dict[str, Any]:
        entry = self._reasoning_entry(artifact_id)
        ids = [entry["proposal_evidence_id"], *[row["evidence_id"] for row in entry["history"]]]
        records = {}
        for evidence_id in ids:
            for record in self.evidence_lineage(evidence_id):
                records[record.evidence_id] = record
        return {
            "contract": reasoning_contract(), "artifact_id": artifact_id, "state": entry["state"],
            "records": [deepcopy(record.__dict__) for _, record in sorted(records.items())],
        }

    def reasoning_contract_report(self) -> dict[str, Any]:
        return reasoning_contract()


__all__ = ["ReasoningRuntimeMixin"]
