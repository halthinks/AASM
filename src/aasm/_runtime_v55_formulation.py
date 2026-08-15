from __future__ import annotations

from copy import deepcopy
import json
from typing import Any, Mapping, Sequence

from .evidence import EvidenceRecord
from .formulation_execution import (
    FORMULATION_EXECUTION_BINDING_CONTRACT_ID,
    FormulationExecutionBinding,
    bind_formulation_execution_request,
    formulation_execution_contract,
    validate_formulation_governance_chain,
)
from .model_features import ModelAdmissionReport, ModelFeatureSet, ProviderCapabilityManifest
from .optimization import OptimizationRequest
from .semantic_result import canonical_semantic_json, semantic_fingerprint
from .solver_formulation import (
    SOLVER_FORMULATION_CONTRACT_ID,
    SolverFormulation,
    SolverFormulationCertificate,
    solver_formulation_contract,
)


FORMULATION_RUNTIME_CONTRACT_ID = "aasm.solver.formulation-runtime.v1"
FORMULATION_RUNTIME_CONTRACT_VERSION = "0.1.0"
FORMULATION_RUNTIME_STABILITY = "FOUNDATION_EXPERIMENTAL"
FORMULATION_RECORD_TYPE_KEY = "aasm_solver_formulation_record_type"
FORMULATION_DOCUMENT_KEY = "document"
REGISTERED_FORMULATION_RECORD = "REGISTERED_FORMULATION"
EXECUTION_BINDING_RECORD = "EXECUTION_BINDING"
_FORMULATION_AUTHORITIES = {"POLICY", "CONTROLLER"}


def formulation_runtime_contract() -> dict[str, Any]:
    return {
        "contract_id": FORMULATION_RUNTIME_CONTRACT_ID,
        "contract_version": FORMULATION_RUNTIME_CONTRACT_VERSION,
        "stability": FORMULATION_RUNTIME_STABILITY,
        "formulation_contract": solver_formulation_contract(),
        "execution_binding_contract": formulation_execution_contract(),
        "durability": "EXISTING_AASM_EVIDENCE_EVENT_REPLAY",
        "registry": "EVIDENCE_PROJECTION_NO_SIDE_TABLE",
        "registration_authority": "POLICY_OR_CONTROLLER",
        "execution_precondition": "REGISTERED_EXACT_PASS_FORMULATION_AND_EXACT_GOVERNANCE_CHAIN",
        "problem_revision_precondition": "CURRENT_USABLE_REVISION_MUST_MATCH_WHEN_FORMULATION_IS_REVISION_BOUND",
        "provider_execution": "EXISTING_AASM_OPTIMIZATION_PROVIDER_PATH_ONLY",
        "execution_authority": "NOT_GRANTED_HERE",
        "truth_authority": "NONE",
    }


def _admission_from_dict(value: Mapping[str, Any]) -> ModelAdmissionReport:
    payload = deepcopy(dict(value))
    payload.pop("fingerprint", None)
    for name in (
        "exact_features",
        "approximate_features",
        "verifier_only_features",
        "unsupported_features",
        "reasons",
    ):
        payload[name] = tuple(payload.get(name) or ())
    return ModelAdmissionReport(**payload)


def _certificate_from_dict(value: Mapping[str, Any]) -> SolverFormulationCertificate:
    payload = deepcopy(dict(value))
    payload.pop("fingerprint", None)
    payload["diagnostics"] = tuple(payload.get("diagnostics") or ())
    return SolverFormulationCertificate(**payload)


def _record_document(row: Mapping[str, Any]) -> dict[str, Any]:
    metadata = dict(row.get("metadata") or {})
    document = metadata.get(FORMULATION_DOCUMENT_KEY)
    if isinstance(document, Mapping):
        return deepcopy(dict(document))
    statement = row.get("statement")
    if isinstance(statement, str) and statement:
        parsed = json.loads(statement)
        if isinstance(parsed, Mapping):
            return deepcopy(dict(parsed))
    raise ValueError("formulation Evidence is missing its canonical document")


def project_formulation_evidence(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    formulations: dict[str, dict[str, Any]] = {}
    execution_bindings: dict[str, dict[str, Any]] = {}
    issues: list[dict[str, Any]] = []
    for index, raw in enumerate(records):
        row = deepcopy(dict(raw))
        if row.get("status", "active") != "active":
            continue
        metadata = dict(row.get("metadata") or {})
        record_type = metadata.get(FORMULATION_RECORD_TYPE_KEY)
        if record_type not in {REGISTERED_FORMULATION_RECORD, EXECUTION_BINDING_RECORD}:
            continue
        evidence_id = str(row.get("evidence_id") or "")
        try:
            document = _record_document(row)
            if record_type == REGISTERED_FORMULATION_RECORD:
                formulation = SolverFormulation.from_dict(document["formulation"])
                certificate = _certificate_from_dict(document["certificate"])
                feature_set = ModelFeatureSet.from_dict(document["feature_set"])
                manifest = ProviderCapabilityManifest.from_dict(document["provider_manifest"])
                admission = _admission_from_dict(document["admission_report"])
                governance = validate_formulation_governance_chain(
                    formulation,
                    certificate,
                    feature_set=feature_set,
                    provider_manifest=manifest,
                    admission_report=admission,
                )
                if not governance["valid"]:
                    raise ValueError(f"invalid durable formulation governance chain: {governance['errors']}")
                prior = formulations.get(formulation.formulation_id)
                candidate = {
                    "formulation": formulation.to_dict(),
                    "certificate": certificate.to_dict(),
                    "feature_set": feature_set.to_dict(),
                    "provider_manifest": manifest.to_dict(),
                    "admission_report": admission.to_dict(),
                    "authority_id": str(document.get("authority_id") or ""),
                    "authority_class": str(document.get("authority_class") or ""),
                    "evidence_id": evidence_id,
                }
                if prior is not None and prior != candidate:
                    raise ValueError(f"formulation identity collision: {formulation.formulation_id}")
                formulations[formulation.formulation_id] = candidate
            else:
                binding = FormulationExecutionBinding.from_dict(document["binding"])
                if binding.formulation_id not in formulations:
                    raise ValueError("execution binding references unregistered formulation")
                registered = formulations[binding.formulation_id]
                if binding.formulation_fingerprint != registered["formulation"]["fingerprint"]:
                    raise ValueError("execution binding formulation fingerprint mismatch")
                prior = execution_bindings.get(binding.binding_id)
                candidate = {"binding": binding.to_dict(), "evidence_id": evidence_id}
                if prior is not None and prior != candidate:
                    raise ValueError(f"formulation execution binding collision: {binding.binding_id}")
                execution_bindings[binding.binding_id] = candidate
        except Exception as exc:
            issues.append({
                "index": index,
                "evidence_id": evidence_id,
                "record_type": record_type,
                "error": f"{type(exc).__name__}: {exc}",
            })
    return {
        "runtime_contract": formulation_runtime_contract(),
        "valid": not issues,
        "issues": issues,
        "formulations": formulations,
        "execution_bindings": execution_bindings,
    }


class FormulationRuntimeMixin:
    def formulation_runtime_contract_report(self) -> dict[str, Any]:
        return formulation_runtime_contract()

    @staticmethod
    def _require_formulation_authority(authority_id: str, authority_class: str) -> None:
        if not str(authority_id).strip():
            raise ValueError("formulation authority_id is required")
        if authority_class not in _FORMULATION_AUTHORITIES:
            raise PermissionError("formulation registration requires POLICY or CONTROLLER authority")

    def _formulation_projection(self) -> dict[str, Any]:
        records = self.snapshot.evidence.get("records", []) if isinstance(self.snapshot.evidence, dict) else []
        return project_formulation_evidence(records)

    def _require_valid_formulation_projection(self) -> dict[str, Any]:
        report = self._formulation_projection()
        if not report["valid"]:
            raise RuntimeError(f"invalid durable formulation projection: {report['issues']}")
        return report

    def _record_formulation_document(
        self,
        *,
        record_type: str,
        object_id: str,
        document: Mapping[str, Any],
        source: str,
        derived_from: Sequence[str],
        reason: str,
    ) -> str:
        payload = deepcopy(dict(document))
        identity = {"record_type": record_type, "object_id": object_id, "document": payload}
        evidence_id = f"formulation-evidence-{semantic_fingerprint(identity)[:24]}"
        for row in self.snapshot.evidence.get("records", []):
            if row.get("evidence_id") != evidence_id:
                continue
            metadata = row.get("metadata") or {}
            if metadata.get(FORMULATION_RECORD_TYPE_KEY) != record_type or metadata.get(FORMULATION_DOCUMENT_KEY) != payload:
                raise ValueError(f"formulation Evidence collision: {evidence_id}")
            return evidence_id
        lineage = self._require_evidence_ids(tuple(derived_from))
        record = EvidenceRecord(
            kind="solver_formulation",
            statement=canonical_semantic_json(payload),
            source=source,
            derived_from=lineage,
            metadata={
                FORMULATION_RECORD_TYPE_KEY: record_type,
                "object_id": object_id,
                FORMULATION_DOCUMENT_KEY: payload,
                "authority": "GOVERNANCE_EVIDENCE_ONLY",
            },
            evidence_id=evidence_id,
        )
        self.add_evidence_guarded(record, expected_machine_version=self.snapshot.version, reason=reason)
        return evidence_id

    def register_solver_formulation(
        self,
        formulation: SolverFormulation | Mapping[str, Any],
        certificate: SolverFormulationCertificate | Mapping[str, Any],
        *,
        feature_set: ModelFeatureSet | Mapping[str, Any],
        provider_manifest: ProviderCapabilityManifest | Mapping[str, Any],
        admission_report: ModelAdmissionReport | Mapping[str, Any],
        authority_id: str,
        authority_class: str,
        evidence_ids: Sequence[str] = (),
        reason: str = "solver formulation registered",
    ) -> dict[str, Any]:
        self._require_formulation_authority(authority_id, authority_class)
        item = formulation if isinstance(formulation, SolverFormulation) else SolverFormulation.from_dict(formulation)
        cert = certificate if isinstance(certificate, SolverFormulationCertificate) else _certificate_from_dict(certificate)
        features = feature_set if isinstance(feature_set, ModelFeatureSet) else ModelFeatureSet.from_dict(feature_set)
        manifest = provider_manifest if isinstance(provider_manifest, ProviderCapabilityManifest) else ProviderCapabilityManifest.from_dict(provider_manifest)
        admission = admission_report if isinstance(admission_report, ModelAdmissionReport) else _admission_from_dict(admission_report)
        governance = validate_formulation_governance_chain(
            item,
            cert,
            feature_set=features,
            provider_manifest=manifest,
            admission_report=admission,
        )
        if not governance["valid"]:
            raise ValueError(f"invalid formulation governance chain: {governance['errors']}")
        projection = self._require_valid_formulation_projection()
        prior = projection["formulations"].get(item.formulation_id)
        if prior is not None:
            if prior["formulation"]["fingerprint"] != item.fingerprint or prior["certificate"]["fingerprint"] != cert.fingerprint:
                raise ValueError(f"formulation identity collision: {item.formulation_id}")
            return {**deepcopy(prior), "already_registered": True}
        lineage = self._require_evidence_ids(tuple(evidence_ids))
        document = {
            "formulation": item.to_dict(),
            "certificate": cert.to_dict(),
            "feature_set": features.to_dict(),
            "provider_manifest": manifest.to_dict(),
            "admission_report": admission.to_dict(),
            "authority_id": str(authority_id),
            "authority_class": authority_class,
        }
        evidence_id = self._record_formulation_document(
            record_type=REGISTERED_FORMULATION_RECORD,
            object_id=item.formulation_id,
            document=document,
            source=SOLVER_FORMULATION_CONTRACT_ID,
            derived_from=lineage,
            reason=reason,
        )
        return {
            "formulation": item.to_dict(),
            "certificate": cert.to_dict(),
            "feature_set": features.to_dict(),
            "provider_manifest": manifest.to_dict(),
            "admission_report": admission.to_dict(),
            "authority_id": str(authority_id),
            "authority_class": authority_class,
            "evidence_id": evidence_id,
            "already_registered": False,
        }

    def prepare_registered_formulation_request(
        self,
        request: OptimizationRequest | Mapping[str, Any],
        formulation_id: str,
        *,
        evidence_ids: Sequence[str] = (),
        reason: str = "formulation execution request bound",
    ) -> dict[str, Any]:
        projection = self._require_valid_formulation_projection()
        try:
            registered = projection["formulations"][formulation_id]
        except KeyError:
            raise KeyError(formulation_id) from None
        formulation = SolverFormulation.from_dict(registered["formulation"])
        certificate = _certificate_from_dict(registered["certificate"])
        feature_set = ModelFeatureSet.from_dict(registered["feature_set"])
        manifest = ProviderCapabilityManifest.from_dict(registered["provider_manifest"])
        admission = _admission_from_dict(registered["admission_report"])
        if formulation.problem_revision_id:
            current = self.require_usable_problem_revision(formulation.source_model.model_id if False else formulation.problem_revision_id)
            # The semantic-evolution runtime indexes by problem_id, not revision_id.
            # Resolve the declared revision through the full projection to avoid a side index.
            revision_projection = self._require_valid_semantic_evolution_projection()
            revision_row = revision_projection["revisions"].get(formulation.problem_revision_id)
            if revision_row is None:
                raise ValueError("formulation problem revision is not durable in this machine")
            declared_revision = revision_row["revision"]
            problem_id = declared_revision["problem_id"]
            usable = self.require_usable_problem_revision(problem_id)
            if usable["revision_id"] != formulation.problem_revision_id or usable["fingerprint"] != formulation.problem_revision_fingerprint:
                raise ValueError("formulation is bound to a superseded or mismatched problem revision")
        binding = bind_formulation_execution_request(
            request,
            formulation,
            certificate,
            feature_set=feature_set,
            provider_manifest=manifest,
            admission_report=admission,
        )
        prior = projection["execution_bindings"].get(binding.binding_id)
        if prior is not None:
            return {"binding": deepcopy(prior["binding"]), "evidence_id": prior["evidence_id"], "already_bound": True}
        lineage = self._require_evidence_ids(tuple(sorted(set([
            *map(str, evidence_ids),
            str(registered["evidence_id"]),
        ]))))
        document = {"binding": binding.to_dict()}
        evidence_id = self._record_formulation_document(
            record_type=EXECUTION_BINDING_RECORD,
            object_id=binding.binding_id,
            document=document,
            source=FORMULATION_EXECUTION_BINDING_CONTRACT_ID,
            derived_from=lineage,
            reason=reason,
        )
        return {"binding": binding.to_dict(), "evidence_id": evidence_id, "already_bound": False}

    def formulation_report(self, formulation_id: str | None = None) -> dict[str, Any]:
        projection = self._formulation_projection()
        if formulation_id is None:
            return projection
        try:
            item = projection["formulations"][formulation_id]
        except KeyError:
            raise KeyError(formulation_id) from None
        bindings = {
            binding_id: deepcopy(row)
            for binding_id, row in projection["execution_bindings"].items()
            if row["binding"].get("formulation_id") == formulation_id
        }
        return {
            "runtime_contract": projection["runtime_contract"],
            "valid": projection["valid"],
            "issues": projection["issues"],
            "formulation": deepcopy(item),
            "execution_bindings": bindings,
        }


__all__ = [
    "FORMULATION_RUNTIME_CONTRACT_ID",
    "FORMULATION_RUNTIME_CONTRACT_VERSION",
    "FORMULATION_RUNTIME_STABILITY",
    "FORMULATION_RECORD_TYPE_KEY",
    "FORMULATION_DOCUMENT_KEY",
    "REGISTERED_FORMULATION_RECORD",
    "EXECUTION_BINDING_RECORD",
    "formulation_runtime_contract",
    "project_formulation_evidence",
    "FormulationRuntimeMixin",
]
