from __future__ import annotations

from copy import deepcopy
from typing import Any, Iterable, Mapping

from .cross_run_knowledge import (
    CROSS_RUN_KNOWLEDGE_CONTRACT_ID,
    CrossRunKnowledgeEnvelope,
)
from .evidence import EvidenceRecord
from .optimization import OptimizationModel
from .scoped_authority import AuthorityRequest
from .semantic_result import canonical_semantic_json, semantic_fingerprint
from .solver_learning import (
    CORRECTNESS_SENSITIVE_KINDS,
    SOLVER_LEARNING_CONTRACT_ID,
    SOLVER_LEARNING_CONTRACT_VERSION,
    SolverLearningArtifact,
    SolverLearningValidation,
    revalidate_finite_solver_learning,
    solver_learning_contract,
    validate_native_accelerator_hint,
)


SOLVER_LEARNING_RUNTIME_CONTRACT_ID = "aasm.solver.learning.runtime.v1"
SOLVER_LEARNING_RUNTIME_CONTRACT_VERSION = "0.1.0"
SOLVER_LEARNING_RUNTIME_STABILITY = "FOUNDATION_EXPERIMENTAL"
SOLVER_LEARNING_AUTHORITY_CAPABILITIES = {
    "export": "solver.learning.export",
    "import": "solver.learning.import",
    "validate": "solver.learning.validate",
}

_SOLVER_LEARNING_RECORD_TYPE = "aasm_solver_learning_record_type"
_SOLVER_LEARNING_DOCUMENT = "document"


def solver_learning_runtime_contract() -> dict[str, Any]:
    return {
        "contract_id": SOLVER_LEARNING_RUNTIME_CONTRACT_ID,
        "contract_version": SOLVER_LEARNING_RUNTIME_CONTRACT_VERSION,
        "stability": SOLVER_LEARNING_RUNTIME_STABILITY,
        "artifact_contract_id": SOLVER_LEARNING_CONTRACT_ID,
        "cross_run_transport": "EXISTING_AASM_V48_REUSE_RESULT_ENVELOPE",
        "cross_run_admission": "EXISTING_AASM_V48_ADMISSION_REQUIRED",
        "cross_run_authority_transfer": "NEVER",
        "imported_pruning_state": "INERT_UNTIL_RECEIVING_RUN_LOCAL_REVALIDATION",
        "performance_hint_authority": "NEVER_TRUTH_OR_POLICY",
        "application": "NO_AUTOMATIC_APPLICATION_IN_V0.53_FOUNDATION",
    }


class SolverLearningRuntimeMixin:
    def solver_learning_contract_report(self) -> dict[str, Any]:
        return solver_learning_contract()

    def solver_learning_runtime_contract_report(self) -> dict[str, Any]:
        return solver_learning_runtime_contract()

    def _validate_solver_learning_context(self, workspace_id: str, scope_id: str) -> None:
        self._workspace_authority_inputs(workspace_id)
        scope_state = self._scope_state_for_authority()
        record = scope_state["records"].get(scope_id)
        if not record or record.get("status") != "ACTIVE":
            raise PermissionError(f"solver learning scope is not active: {scope_id}")

    def _authorize_solver_learning_action(
        self,
        *,
        actor_principal_id: str,
        workspace_id: str,
        scope_id: str,
        capability: str,
        at_time: float,
        learning_id: str,
    ) -> dict[str, Any]:
        self._validate_solver_learning_context(workspace_id, scope_id)
        result = self.authorize_scoped_request(
            AuthorityRequest(
                actor_principal_id,
                workspace_id,
                scope_id,
                capability,
                at_time=at_time,
                machine_id=self.snapshot.machine_id,
                metadata={"solver_learning_id": learning_id},
            ),
            reason=f"v0.53 solver learning authority evaluated: {capability}",
        )
        if not result["decision"]["allowed"]:
            raise PermissionError(
                f"v0.53 solver learning authority denied {capability}: {result['decision']['reason']}"
            )
        return result

    def _record_solver_learning_document(
        self,
        *,
        record_type: str,
        object_id: str,
        workspace_id: str,
        scope_id: str,
        document: Mapping[str, Any],
        source: str,
        derived_from=(),
        reason: str,
    ) -> str:
        payload = {
            "workspace_id": workspace_id,
            "scope_id": scope_id,
            **deepcopy(dict(document)),
        }
        identity = {"record_type": record_type, "object_id": object_id, "document": payload}
        evidence_id = f"solver-learning-evidence-{semantic_fingerprint(identity)[:24]}"
        for row in self.snapshot.evidence.get("records", []):
            if row.get("evidence_id") != evidence_id:
                continue
            metadata = row.get("metadata") or {}
            if metadata.get(_SOLVER_LEARNING_RECORD_TYPE) != record_type or metadata.get(_SOLVER_LEARNING_DOCUMENT) != payload:
                raise ValueError(f"solver learning Evidence collision: {evidence_id}")
            return evidence_id
        stored = self.add_evidence(
            EvidenceRecord(
                kind="solver_learning",
                statement=canonical_semantic_json(payload),
                source=source,
                derived_from=list(sorted(set(map(str, derived_from)))),
                metadata={
                    _SOLVER_LEARNING_RECORD_TYPE: record_type,
                    "object_id": object_id,
                    _SOLVER_LEARNING_DOCUMENT: payload,
                    "authority": "EVIDENCE_ONLY",
                },
                evidence_id=evidence_id,
            ),
            reason=reason,
        )
        return stored.evidence_id

    def _solver_learning_rows(
        self,
        *,
        workspace_id: str,
        scope_id: str | None = None,
        record_types: Iterable[str] | None = None,
    ) -> list[dict[str, Any]]:
        allowed_types = None if record_types is None else set(map(str, record_types))
        rows = []
        for row in self.snapshot.evidence.get("records", []):
            if row.get("status", "active") != "active":
                continue
            metadata = row.get("metadata") or {}
            record_type = metadata.get(_SOLVER_LEARNING_RECORD_TYPE)
            if not record_type or (allowed_types is not None and record_type not in allowed_types):
                continue
            document = metadata.get(_SOLVER_LEARNING_DOCUMENT)
            if not isinstance(document, dict) or document.get("workspace_id") != workspace_id:
                continue
            if scope_id is not None and document.get("scope_id") != scope_id:
                continue
            rows.append({
                "record_type": record_type,
                "evidence_id": row.get("evidence_id"),
                "document": deepcopy(document),
                "derived_from": list(row.get("derived_from") or []),
            })
        return rows

    def _solver_learning_artifact_row(
        self,
        learning_id: str,
        *,
        workspace_id: str,
        scope_id: str,
        local_only: bool = False,
    ) -> dict[str, Any]:
        types = ("local_artifact",) if local_only else ("local_artifact", "imported_artifact")
        rows = [
            row for row in self._solver_learning_rows(workspace_id=workspace_id, scope_id=scope_id, record_types=types)
            if row["document"].get("artifact", {}).get("learning_id") == learning_id
        ]
        if not rows:
            raise KeyError(f"unknown solver learning artifact in access context: {learning_id}")
        fingerprints = {row["document"]["artifact"]["fingerprint"] for row in rows}
        if len(fingerprints) != 1:
            raise ValueError(f"solver learning artifact identity collision: {learning_id}")
        return rows[-1]

    def record_solver_learning_artifact(
        self,
        artifact: SolverLearningArtifact | Mapping[str, Any],
        *,
        workspace_id: str,
        scope_id: str,
        derived_from=(),
    ) -> dict[str, Any]:
        self._validate_solver_learning_context(workspace_id, scope_id)
        item = artifact if isinstance(artifact, SolverLearningArtifact) else SolverLearningArtifact.from_dict(artifact)
        local_evidence = {
            str(row.get("evidence_id")) for row in self.snapshot.evidence.get("records", []) if row.get("evidence_id")
        }
        missing = sorted(set(item.source_evidence_ids) - local_evidence)
        if missing:
            raise KeyError(f"solver learning source Evidence is not local: {missing}")
        lineage = tuple(sorted(set((*map(str, derived_from), *item.source_evidence_ids))))
        evidence_id = self._record_solver_learning_document(
            record_type="local_artifact",
            object_id=item.learning_id,
            workspace_id=workspace_id,
            scope_id=scope_id,
            document={"artifact": item.to_dict(), "activation_status": "LOCAL_EVIDENCE_ONLY"},
            source=SOLVER_LEARNING_CONTRACT_ID,
            derived_from=lineage,
            reason="v0.53 local solver learning artifact recorded",
        )
        return {"artifact": item.to_dict(), "evidence_id": evidence_id, "activation_status": "LOCAL_EVIDENCE_ONLY"}

    def export_solver_learning_artifact(
        self,
        learning_id: str,
        *,
        workspace_id: str,
        scope_id: str,
        actor_principal_id: str,
        at_time: float = 0.0,
        applicability_scope_ids: Iterable[str] = (),
    ) -> dict[str, Any]:
        row = self._solver_learning_artifact_row(
            learning_id,
            workspace_id=workspace_id,
            scope_id=scope_id,
            local_only=True,
        )
        artifact = SolverLearningArtifact.from_dict(row["document"]["artifact"])
        authorization = self._authorize_solver_learning_action(
            actor_principal_id=actor_principal_id,
            workspace_id=workspace_id,
            scope_id=scope_id,
            capability=SOLVER_LEARNING_AUTHORITY_CAPABILITIES["export"],
            at_time=at_time,
            learning_id=learning_id,
        )
        applicability = tuple(sorted(set(map(str, applicability_scope_ids)))) or (scope_id,)
        envelope = CrossRunKnowledgeEnvelope(
            source_run_id=self.snapshot.machine_id,
            source_machine_id=self.snapshot.machine_id,
            source_scope_id=scope_id,
            knowledge_kind="REUSE_RESULT",
            content=artifact.to_dict(),
            source_evidence_ids=(str(row["evidence_id"]),),
            source_fingerprints={
                f"SOLVER_LEARNING:{artifact.learning_id}": artifact.fingerprint,
            },
            source_authority_provenance={
                "authority_decision_evidence_id": str(authorization["evidence_id"]),
                "source_authority_is_provenance_only": True,
                "authority_transfer": "NEVER",
            },
            environment_fingerprint=artifact.environment_fingerprint,
            dependency_fingerprints=artifact.dependency_fingerprints,
            applicability_scope_ids=applicability,
            metadata={
                "solver_learning_contract_id": SOLVER_LEARNING_CONTRACT_ID,
                "solver_learning_contract_version": SOLVER_LEARNING_CONTRACT_VERSION,
                "solver_learning_id": artifact.learning_id,
                "learning_class": artifact.learning_class,
                "authority_inherited": False,
                "truth_authority": "NONE",
            },
        )
        evidence_id = self._record_solver_learning_document(
            record_type="export",
            object_id=envelope.envelope_id,
            workspace_id=workspace_id,
            scope_id=scope_id,
            document={"envelope": envelope.to_dict(), "artifact_fingerprint": artifact.fingerprint},
            source=CROSS_RUN_KNOWLEDGE_CONTRACT_ID,
            derived_from=[row["evidence_id"], authorization["evidence_id"]],
            reason="v0.53 solver learning exported through v0.48 envelope",
        )
        return {"envelope": envelope.to_dict(), "evidence_id": evidence_id, "authority_decision_evidence_id": authorization["evidence_id"]}

    def admit_cross_run_solver_learning(
        self,
        envelope_id: str,
        *,
        expected_model_fingerprint: str,
        workspace_id: str,
        scope_id: str,
        actor_principal_id: str,
        at_time: float = 0.0,
    ) -> dict[str, Any]:
        report = self.cross_run_knowledge_report()
        try:
            admission = report["admissions"][envelope_id]
        except KeyError:
            raise KeyError(f"solver learning envelope has no committed v0.48 admission: {envelope_id}") from None
        if admission.get("status") != "ADMITTED":
            raise PermissionError(f"solver learning envelope is not admitted: {envelope_id}")
        if admission.get("target_scope_id") != scope_id:
            raise PermissionError("solver learning import scope does not match committed cross-run admission")
        envelope = CrossRunKnowledgeEnvelope.from_dict(admission["envelope"])
        if envelope.knowledge_kind != "REUSE_RESULT":
            raise ValueError("solver learning envelope must use the v0.48 REUSE_RESULT transport kind")
        if envelope.metadata.get("solver_learning_contract_id") != SOLVER_LEARNING_CONTRACT_ID:
            raise ValueError("cross-run solver learning metadata contract mismatch")
        if envelope.metadata.get("solver_learning_contract_version") != SOLVER_LEARNING_CONTRACT_VERSION:
            raise ValueError("cross-run solver learning metadata version mismatch")
        if not isinstance(envelope.content, Mapping):
            raise ValueError("cross-run solver learning content must be a solver-learning document")
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
        evidence_id = self._record_solver_learning_document(
            record_type="imported_artifact",
            object_id=artifact.learning_id,
            workspace_id=workspace_id,
            scope_id=scope_id,
            document={
                "artifact": artifact.to_dict(),
                "envelope_id": envelope_id,
                "source_run_id": envelope.source_run_id,
                "cross_run_admission_evidence_id": admission["admission_evidence_id"],
                "authority_inherited": False,
                "truth_authority": "NONE",
                "activation_status": activation_status,
            },
            source=SOLVER_LEARNING_CONTRACT_ID,
            derived_from=[admission["admission_evidence_id"], authorization["evidence_id"]],
            reason="v0.53 admitted solver learning materialized as inert local Evidence",
        )
        return {
            "artifact": artifact.to_dict(),
            "evidence_id": evidence_id,
            "activation_status": activation_status,
            "authority_decision_evidence_id": authorization["evidence_id"],
            "authority_inherited": False,
        }

    def revalidate_solver_learning(
        self,
        learning_id: str,
        model: OptimizationModel,
        *,
        workspace_id: str,
        scope_id: str,
        actor_principal_id: str,
        at_time: float = 0.0,
        provider_id: str = "",
        provider_version: str = "",
        environment_fingerprint: str = "",
        max_total_states: int = 100_000,
        max_states_per_step: int = 1_000,
    ) -> dict[str, Any]:
        row = self._solver_learning_artifact_row(
            learning_id,
            workspace_id=workspace_id,
            scope_id=scope_id,
        )
        artifact = SolverLearningArtifact.from_dict(row["document"]["artifact"])
        authorization = self._authorize_solver_learning_action(
            actor_principal_id=actor_principal_id,
            workspace_id=workspace_id,
            scope_id=scope_id,
            capability=SOLVER_LEARNING_AUTHORITY_CAPABILITIES["validate"],
            at_time=at_time,
            learning_id=learning_id,
        )
        if artifact.learning_kind == "NATIVE_ACCELERATOR":
            validation = validate_native_accelerator_hint(
                artifact,
                model,
                provider_id=provider_id,
                provider_version=provider_version,
                environment_fingerprint=environment_fingerprint,
            )
        else:
            validation = revalidate_finite_solver_learning(
                artifact,
                model,
                max_total_states=max_total_states,
                max_states_per_step=max_states_per_step,
            )
        evidence_id = self._record_solver_learning_document(
            record_type="validation",
            object_id=validation.validation_id,
            workspace_id=workspace_id,
            scope_id=scope_id,
            document={
                "learning_id": learning_id,
                "artifact_fingerprint": artifact.fingerprint,
                "validation": validation.to_dict(),
                "cross_run_admission_implied_truth": False,
            },
            source=SOLVER_LEARNING_CONTRACT_ID,
            derived_from=[row["evidence_id"], authorization["evidence_id"]],
            reason="v0.53 receiving-run solver learning validation recorded",
        )
        return {
            "artifact": artifact.to_dict(),
            "validation": validation.to_dict(),
            "evidence_id": evidence_id,
            "authority_decision_evidence_id": authorization["evidence_id"],
        }

    def solver_learning_report(
        self,
        *,
        workspace_id: str,
        scope_id: str | None = None,
    ) -> dict[str, Any]:
        groups = {
            "local_artifacts": {},
            "exports": {},
            "imported_artifacts": {},
            "validations": {},
        }
        mapping = {
            "local_artifact": "local_artifacts",
            "export": "exports",
            "imported_artifact": "imported_artifacts",
            "validation": "validations",
        }
        for row in self._solver_learning_rows(workspace_id=workspace_id, scope_id=scope_id):
            bucket = mapping.get(row["record_type"])
            if bucket is not None:
                groups[bucket][str(row["evidence_id"])] = {
                    "document": deepcopy(row["document"]),
                    "derived_from": list(row["derived_from"]),
                }
        return {
            "contract": solver_learning_contract(),
            "runtime_contract": solver_learning_runtime_contract(),
            "workspace_id": workspace_id,
            "scope_id": scope_id,
            "authority_capabilities": deepcopy(SOLVER_LEARNING_AUTHORITY_CAPABILITIES),
            **groups,
        }


__all__ = [
    "SOLVER_LEARNING_RUNTIME_CONTRACT_ID",
    "SOLVER_LEARNING_RUNTIME_CONTRACT_VERSION",
    "SOLVER_LEARNING_RUNTIME_STABILITY",
    "SOLVER_LEARNING_AUTHORITY_CAPABILITIES",
    "solver_learning_runtime_contract",
    "SolverLearningRuntimeMixin",
]
