from __future__ import annotations

from typing import Any

from .evidence import EvidenceRecord
from .optimization import OptimizationModel, OptimizationResult
from .proof_claims import certify_optimization_result, solver_proof_contract


def _proof_value(snapshot, evidence_id: str):
    for row in snapshot.evidence.get("records", []):
        if str(row.get("evidence_id")) == str(evidence_id):
            return dict(row)
    return None


def _proof_projection(snapshot, kind: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for value in snapshot.evidence.get("records", []):
        metadata = value.get("metadata") or {}
        if metadata.get("proof_record_type") != kind:
            continue
        evidence_id = str(value.get("evidence_id") or "")
        object_id = str(metadata.get("object_id") or evidence_id)
        out[object_id] = metadata.get("document") or {}
    return out


class ProofClaimRuntimeMixin:
    """v0.50 proof-carrying solver claims over the existing Evidence/event plane."""

    def solver_proof_contract_report(self) -> dict[str, Any]:
        return solver_proof_contract()

    def solver_proof_claim_report(self, claim_id: str | None = None) -> dict[str, Any]:
        claims = _proof_projection(self.snapshot, "solver_claim")
        artifacts = _proof_projection(self.snapshot, "solver_proof_artifact")
        certificates = _proof_projection(self.snapshot, "solver_claim_certificate")
        report = {
            "contract": solver_proof_contract(),
            "claims": claims,
            "proof_artifacts": artifacts,
            "certificates": certificates,
        }
        if claim_id is None:
            return report
        if claim_id not in claims:
            raise KeyError(claim_id)
        report["claim"] = claims[claim_id]
        report["claim_proof_artifacts"] = {
            key: row for key, row in artifacts.items() if row.get("claim_id") == claim_id
        }
        report["claim_certificates"] = {
            key: row for key, row in certificates.items() if row.get("claim_id") == claim_id
        }
        return report

    def _record_proof_document(self, *, record_type: str, object_id: str, document: dict[str, Any], source: str, derived_from=()):
        existing = _proof_value(self.snapshot, object_id)
        if existing is not None:
            metadata = existing.get("metadata") or {}
            if metadata.get("proof_record_type") != record_type or metadata.get("document") != document:
                raise ValueError(f"proof evidence id collision: {object_id}")
            return existing
        record = EvidenceRecord(
            kind="claim",
            statement=f"AASM {record_type}: {object_id}",
            source=source,
            derived_from=list(derived_from),
            metadata={
                "proof_record_type": record_type,
                "object_id": object_id,
                "document": document,
                "authority": "EVIDENCE_ONLY",
            },
            evidence_id=object_id,
        )
        self.add_evidence(record)
        return _proof_value(self.snapshot, object_id)

    def certify_optimization_claim(
        self,
        model: OptimizationModel,
        result: OptimizationResult,
        *,
        max_states: int = 100_000,
        problem_fingerprint: str = "",
        formulation_fingerprint: str = "",
        persist_failure_claim: bool = True,
    ) -> dict[str, Any]:
        certification = certify_optimization_result(
            model,
            result,
            max_states=max_states,
            problem_fingerprint=problem_fingerprint,
            formulation_fingerprint=formulation_fingerprint,
        )
        claim = certification["claim"]
        claim_id = claim["claim_id"]
        self._record_proof_document(
            record_type="solver_claim",
            object_id=claim_id,
            document={**claim, "verification_level": "SOLVER_VALIDATED"},
            source=result.solver.provider_id,
        )
        if certification["status"] != "PASS":
            if not persist_failure_claim:
                return certification
            return {**certification, "durable_claim_evidence_id": claim_id}
        artifact = certification["proof_artifact"]
        certificate = certification["certificate"]
        artifact_id = artifact["artifact_id"]
        certificate_id = certificate["certificate_id"]
        self._record_proof_document(
            record_type="solver_proof_artifact",
            object_id=artifact_id,
            document=artifact,
            source=artifact["producer_id"],
            derived_from=(claim_id,),
        )
        self._record_proof_document(
            record_type="solver_claim_certificate",
            object_id=certificate_id,
            document=certificate,
            source=certificate["checker_id"],
            derived_from=(claim_id, artifact_id),
        )
        return {
            **certification,
            "durable_claim_evidence_id": claim_id,
            "durable_proof_artifact_evidence_id": artifact_id,
            "durable_certificate_evidence_id": certificate_id,
        }
