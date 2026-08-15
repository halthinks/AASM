from __future__ import annotations

from copy import deepcopy
from typing import Mapping

from ._runtime_v53_solver_learning import (
    SOLVER_LEARNING_AUTHORITY_CAPABILITIES,
    SolverLearningRuntimeMixin,
)
from .cross_run_knowledge import CrossRunKnowledgeEnvelope
from .optimization import OptimizationRequest
from .runtime_v53 import AASMEngine as V53AuthorityEngine
from .solver_learning import (
    CORRECTNESS_SENSITIVE_KINDS,
    SOLVER_LEARNING_APPLICATION_CONTRACT_ID,
    SOLVER_LEARNING_CONTRACT_ID,
    SOLVER_LEARNING_CONTRACT_VERSION,
    SolverLearningArtifact,
    SolverLearningValidation,
    apply_solver_learning_to_optimization_request,
    solver_learning_application_contract,
)


SOLVER_LEARNING_APPLY_CAPABILITY = "solver.learning.apply"


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

    def _latest_solver_learning_validation(
        self,
        learning_id: str,
        *,
        workspace_id: str,
        scope_id: str,
        artifact_fingerprint: str,
    ) -> tuple[SolverLearningValidation, str]:
        rows = [
            row
            for row in self._solver_learning_rows(
                workspace_id=workspace_id,
                scope_id=scope_id,
                record_types=("validation",),
            )
            if row["document"].get("learning_id") == learning_id
            and row["document"].get("artifact_fingerprint") == artifact_fingerprint
        ]
        if not rows:
            raise PermissionError(
                "solver learning application requires a local validation Evidence record for the exact artifact"
            )
        row = rows[-1]
        validation = SolverLearningValidation.from_dict(row["document"]["validation"])
        if validation.status != "PASS":
            raise PermissionError("solver learning application requires latest matching PASS validation")
        return validation, str(row["evidence_id"])

    def apply_solver_learning(
        self,
        learning_id: str,
        request: OptimizationRequest | Mapping,
        *,
        workspace_id: str,
        scope_id: str,
        actor_principal_id: str,
        at_time: float = 0.0,
    ) -> dict:
        """Build an optimization request that explicitly consumes validated learning.

        This method does not execute the solver and does not mutate machine truth.
        Execution remains on the existing optimization provider/scheduler path.
        """
        parsed = request if isinstance(request, OptimizationRequest) else OptimizationRequest.from_dict(request)
        artifact_row = self._solver_learning_artifact_row(
            learning_id,
            workspace_id=workspace_id,
            scope_id=scope_id,
        )
        artifact = SolverLearningArtifact.from_dict(artifact_row["document"]["artifact"])
        validation, validation_evidence_id = self._latest_solver_learning_validation(
            learning_id,
            workspace_id=workspace_id,
            scope_id=scope_id,
            artifact_fingerprint=artifact.fingerprint,
        )
        authorization = self._authorize_solver_learning_action(
            actor_principal_id=actor_principal_id,
            workspace_id=workspace_id,
            scope_id=scope_id,
            capability=SOLVER_LEARNING_APPLY_CAPABILITY,
            at_time=at_time,
            learning_id=learning_id,
        )
        application, updated_request = apply_solver_learning_to_optimization_request(
            artifact,
            validation,
            parsed,
        )
        evidence_id = self._record_solver_learning_document(
            record_type="application",
            object_id=application.application_id,
            workspace_id=workspace_id,
            scope_id=scope_id,
            document={
                "application": application.to_dict(),
                "request": updated_request.to_dict(),
                "original_request_fingerprint": parsed.fingerprint,
                "truth_authority": "NONE",
                "policy_authority": "NONE",
                "solver_execution": "EXISTING_AASM_OPTIMIZATION_PROVIDER_PATH_ONLY",
            },
            source=SOLVER_LEARNING_APPLICATION_CONTRACT_ID,
            derived_from=[
                artifact_row["evidence_id"],
                validation_evidence_id,
                authorization["evidence_id"],
            ],
            reason="v0.53 validated solver learning application recorded",
        )
        return {
            "contract": solver_learning_application_contract(),
            "application": application.to_dict(),
            "request": updated_request.to_dict(),
            "evidence_id": evidence_id,
            "authority_decision_evidence_id": authorization["evidence_id"],
            "executed": False,
        }

    def solver_learning_report(
        self,
        *,
        workspace_id: str,
        scope_id: str | None = None,
    ) -> dict:
        report = super().solver_learning_report(workspace_id=workspace_id, scope_id=scope_id)
        applications = {}
        for row in self._solver_learning_rows(
            workspace_id=workspace_id,
            scope_id=scope_id,
            record_types=("application",),
        ):
            applications[str(row["evidence_id"])] = {
                "document": deepcopy(row["document"]),
                "derived_from": list(row["derived_from"]),
            }
        report["applications"] = applications
        report["authority_capabilities"] = {
            **report.get("authority_capabilities", {}),
            "apply": SOLVER_LEARNING_APPLY_CAPABILITY,
        }
        report["application_contract"] = solver_learning_application_contract()
        return report


__all__ = ["AASMEngine", "SOLVER_LEARNING_APPLY_CAPABILITY"]
