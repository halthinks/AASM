from __future__ import annotations

from typing import Mapping

from ._runtime_v53_solver_learning import (
    SOLVER_LEARNING_AUTHORITY_CAPABILITIES,
    SolverLearningRuntimeMixin,
)
from .cross_run_knowledge import CrossRunKnowledgeEnvelope
from .runtime_v53 import AASMEngine as V53AuthorityEngine
from .solver_learning import (
    CORRECTNESS_SENSITIVE_KINDS,
    SOLVER_LEARNING_CONTRACT_ID,
    SOLVER_LEARNING_CONTRACT_VERSION,
    SolverLearningArtifact,
)


class AASMEngine(SolverLearningRuntimeMixin, V53AuthorityEngine):
    """Experimental full v0.53 composition: scoped authority + solver learning."""

    def admit_cross_run_solver_learning(
        self,
        envelope_id: str,
        *,
        expected_model_fingerprint: str,
        workspace_id: str,
        scope_id: str,
        actor_principal_id: str,
        at_time: float = 0.0,
    ) -> dict:
        """Materialize committed v0.48 foreign learning as inert local Evidence.

        v0.48 owns the transport/admission projection. A committed foreign
        envelope is therefore read from ``cross_run_knowledge_report().envelopes``
        and must still be ACTIVE. v0.53 adds scoped import authority and never
        interprets v0.48 admission as truth or local authority.
        """
        report = self.cross_run_knowledge_report()
        admission = report.get("envelopes", {}).get(envelope_id)
        if admission is None:
            raise KeyError(
                f"solver learning envelope has no committed v0.48 admission: {envelope_id}"
            )
        if admission.get("status") != "ACTIVE":
            raise PermissionError(
                f"solver learning envelope is not ACTIVE in v0.48 admission projection: {envelope_id}"
            )
        if admission.get("target_scope_id") != scope_id:
            raise PermissionError(
                "solver learning import scope does not match committed cross-run admission"
            )

        envelope = CrossRunKnowledgeEnvelope.from_dict(admission["envelope"])
        if envelope.knowledge_kind != "REUSE_RESULT":
            raise ValueError(
                "solver learning envelope must use the v0.48 REUSE_RESULT transport kind"
            )
        if envelope.metadata.get("solver_learning_contract_id") != SOLVER_LEARNING_CONTRACT_ID:
            raise ValueError("cross-run solver learning metadata contract mismatch")
        if envelope.metadata.get("solver_learning_contract_version") != SOLVER_LEARNING_CONTRACT_VERSION:
            raise ValueError("cross-run solver learning metadata version mismatch")
        if not isinstance(envelope.content, Mapping):
            raise ValueError(
                "cross-run solver learning content must be a solver-learning document"
            )
        if envelope.content.get("contract_id") != SOLVER_LEARNING_CONTRACT_ID:
            raise ValueError("cross-run solver learning content contract mismatch")
        if envelope.content.get("contract_version") != SOLVER_LEARNING_CONTRACT_VERSION:
            raise ValueError("cross-run solver learning content version mismatch")

        artifact = SolverLearningArtifact.from_dict(envelope.content)
        source_key = f"SOLVER_LEARNING:{artifact.learning_id}"
        if envelope.source_fingerprints.get(source_key) != artifact.fingerprint:
            raise ValueError("cross-run solver learning source fingerprint mismatch")
        if artifact.model_fingerprint != expected_model_fingerprint:
            raise ValueError("imported solver learning model fingerprint mismatch")

        authorization = self._authorize_solver_learning_action(
            actor_principal_id=actor_principal_id,
            workspace_id=workspace_id,
            scope_id=scope_id,
            capability=SOLVER_LEARNING_AUTHORITY_CAPABILITIES["import"],
            at_time=at_time,
            learning_id=artifact.learning_id,
        )
        activation_status = (
            "REVALIDATION_REQUIRED"
            if artifact.learning_kind in CORRECTNESS_SENSITIVE_KINDS
            else "PERFORMANCE_HINT_PENDING_LOCAL_VALIDATION"
        )
        admission_evidence_id = str(admission["admission_evidence_id"])
        evidence_id = self._record_solver_learning_document(
            record_type="imported_artifact",
            object_id=artifact.learning_id,
            workspace_id=workspace_id,
            scope_id=scope_id,
            document={
                "artifact": artifact.to_dict(),
                "envelope_id": envelope_id,
                "source_run_id": envelope.source_run_id,
                "cross_run_admission_evidence_id": admission_evidence_id,
                "authority_inherited": False,
                "truth_authority": "NONE",
                "activation_status": activation_status,
            },
            source=SOLVER_LEARNING_CONTRACT_ID,
            derived_from=[admission_evidence_id, authorization["evidence_id"]],
            reason="v0.53 admitted solver learning materialized as inert local Evidence",
        )
        return {
            "artifact": artifact.to_dict(),
            "evidence_id": evidence_id,
            "activation_status": activation_status,
            "authority_decision_evidence_id": authorization["evidence_id"],
            "authority_inherited": False,
        }


__all__ = ["AASMEngine"]
