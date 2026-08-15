from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Mapping

from .model_features import ModelAdmissionReport, ModelFeatureSet, ProviderCapabilityManifest
from .optimization import OptimizationRequest
from .semantic_result import semantic_fingerprint
from .solver_formulation import SolverFormulation, SolverFormulationCertificate


FORMULATION_EXECUTION_BINDING_CONTRACT_ID = "aasm.solver.formulation-execution.v1"
FORMULATION_EXECUTION_BINDING_CONTRACT_VERSION = "0.1.0"
FORMULATION_EXECUTION_STABILITY = "FOUNDATION_EXPERIMENTAL"


def _required(value: str, name: str) -> str:
    normalized = str(value).strip()
    if not normalized:
        raise ValueError(f"{name} is required")
    return normalized


def _jsonable(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        return _jsonable(value.to_dict())
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))}
    if isinstance(value, (tuple, list, set)):
        return [_jsonable(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    raise TypeError(f"formulation execution value is not JSON serializable: {type(value)!r}")


def _admission(value: ModelAdmissionReport | Mapping[str, Any]) -> ModelAdmissionReport:
    if isinstance(value, ModelAdmissionReport):
        return value
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


@dataclass(frozen=True)
class FormulationExecutionBinding:
    request_id: str
    request_fingerprint: str
    target_model_fingerprint: str
    target_provider_id: str
    formulation_id: str
    formulation_fingerprint: str
    formulation_certificate_id: str
    formulation_certificate_fingerprint: str
    provider_manifest_id: str
    provider_manifest_fingerprint: str
    feature_set_id: str
    feature_set_fingerprint: str
    admission_report_id: str
    admission_report_fingerprint: str
    problem_revision_id: str = ""
    problem_revision_fingerprint: str = ""
    environment_fingerprint: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)
    binding_id: str = ""
    contract_id: str = FORMULATION_EXECUTION_BINDING_CONTRACT_ID
    contract_version: str = FORMULATION_EXECUTION_BINDING_CONTRACT_VERSION

    def __post_init__(self) -> None:
        for name in (
            "request_id",
            "request_fingerprint",
            "target_model_fingerprint",
            "target_provider_id",
            "formulation_id",
            "formulation_fingerprint",
            "formulation_certificate_id",
            "formulation_certificate_fingerprint",
            "provider_manifest_id",
            "provider_manifest_fingerprint",
            "feature_set_id",
            "feature_set_fingerprint",
            "admission_report_id",
            "admission_report_fingerprint",
        ):
            object.__setattr__(self, name, _required(getattr(self, name), name))
        if self.contract_id != FORMULATION_EXECUTION_BINDING_CONTRACT_ID or self.contract_version != FORMULATION_EXECUTION_BINDING_CONTRACT_VERSION:
            raise ValueError("unsupported formulation execution binding contract")
        object.__setattr__(self, "problem_revision_id", str(self.problem_revision_id).strip())
        object.__setattr__(self, "problem_revision_fingerprint", str(self.problem_revision_fingerprint).strip())
        if bool(self.problem_revision_id) != bool(self.problem_revision_fingerprint):
            raise ValueError("problem revision ID and fingerprint must be supplied together")
        object.__setattr__(self, "environment_fingerprint", str(self.environment_fingerprint).strip())
        object.__setattr__(self, "metadata", _jsonable(dict(self.metadata)))
        if not self.binding_id:
            object.__setattr__(self, "binding_id", f"formulation-execution-{semantic_fingerprint(self.identity_payload())[:24]}")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "request_id": self.request_id,
            "request_fingerprint": self.request_fingerprint,
            "target_model_fingerprint": self.target_model_fingerprint,
            "target_provider_id": self.target_provider_id,
            "formulation_id": self.formulation_id,
            "formulation_fingerprint": self.formulation_fingerprint,
            "formulation_certificate_id": self.formulation_certificate_id,
            "formulation_certificate_fingerprint": self.formulation_certificate_fingerprint,
            "provider_manifest_id": self.provider_manifest_id,
            "provider_manifest_fingerprint": self.provider_manifest_fingerprint,
            "feature_set_id": self.feature_set_id,
            "feature_set_fingerprint": self.feature_set_fingerprint,
            "admission_report_id": self.admission_report_id,
            "admission_report_fingerprint": self.admission_report_fingerprint,
            "problem_revision_id": self.problem_revision_id,
            "problem_revision_fingerprint": self.problem_revision_fingerprint,
            "environment_fingerprint": self.environment_fingerprint,
            "metadata": _jsonable(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"binding_id": self.binding_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"binding_id": self.binding_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "FormulationExecutionBinding":
        payload = deepcopy(dict(value))
        payload.pop("fingerprint", None)
        return cls(**payload)


def validate_formulation_governance_chain(
    formulation: SolverFormulation | Mapping[str, Any],
    certificate: SolverFormulationCertificate | Mapping[str, Any],
    *,
    feature_set: ModelFeatureSet | Mapping[str, Any],
    provider_manifest: ProviderCapabilityManifest | Mapping[str, Any],
    admission_report: ModelAdmissionReport | Mapping[str, Any],
) -> dict[str, Any]:
    item = formulation if isinstance(formulation, SolverFormulation) else SolverFormulation.from_dict(formulation)
    cert = certificate if isinstance(certificate, SolverFormulationCertificate) else SolverFormulationCertificate(**{
        **{k: v for k, v in dict(certificate).items() if k != "fingerprint"},
        "diagnostics": tuple(dict(certificate).get("diagnostics") or ()),
    })
    features = feature_set if isinstance(feature_set, ModelFeatureSet) else ModelFeatureSet.from_dict(feature_set)
    manifest = provider_manifest if isinstance(provider_manifest, ProviderCapabilityManifest) else ProviderCapabilityManifest.from_dict(provider_manifest)
    admission = _admission(admission_report)
    errors: list[str] = []

    if cert.status != "PASS" or cert.verified_fidelity != "EXACT":
        errors.append("FORMULATION_CERTIFICATE_NOT_EXACT_PASS")
    if cert.formulation_id != item.formulation_id or cert.formulation_fingerprint != item.fingerprint:
        errors.append("FORMULATION_CERTIFICATE_BINDING_MISMATCH")
    if cert.source_model_fingerprint != item.source_model.fingerprint or cert.target_model_fingerprint != item.target_model.fingerprint:
        errors.append("FORMULATION_CERTIFICATE_MODEL_MISMATCH")
    if item.provider_manifest_id != manifest.manifest_id or item.provider_manifest_fingerprint != manifest.fingerprint:
        errors.append("PROVIDER_MANIFEST_BINDING_MISMATCH")
    if item.feature_set_id != features.feature_set_id or item.feature_set_fingerprint != features.fingerprint:
        errors.append("FEATURE_SET_BINDING_MISMATCH")
    if item.admission_report_id != admission.report_id or item.admission_report_fingerprint != admission.fingerprint:
        errors.append("ADMISSION_REPORT_BINDING_MISMATCH")
    if admission.feature_set_id != features.feature_set_id or admission.feature_set_fingerprint != features.fingerprint:
        errors.append("ADMISSION_FEATURE_SET_MISMATCH")
    if admission.provider_manifest_id != manifest.manifest_id or admission.provider_manifest_fingerprint != manifest.fingerprint:
        errors.append("ADMISSION_PROVIDER_MANIFEST_MISMATCH")
    if not admission.admitted or not admission.exact:
        errors.append("ADMISSION_NOT_EXACT_PASS")
    if features.model_fingerprint != item.source_model.fingerprint:
        errors.append("FEATURE_SET_SOURCE_MODEL_MISMATCH")
    if manifest.provider_id != item.target_provider_id:
        errors.append("MANIFEST_TARGET_PROVIDER_MISMATCH")
    if manifest.solver_families and item.target_model.solver_family not in manifest.solver_families:
        errors.append("MANIFEST_TARGET_FAMILY_MISMATCH")
    if features.problem_revision_id:
        if features.problem_revision_id != item.problem_revision_id or features.problem_revision_fingerprint != item.problem_revision_fingerprint:
            errors.append("FEATURE_SET_PROBLEM_REVISION_MISMATCH")
    if cert.provider_manifest_fingerprint != manifest.fingerprint:
        errors.append("CERTIFICATE_PROVIDER_MANIFEST_MISMATCH")
    if cert.feature_set_fingerprint != features.fingerprint:
        errors.append("CERTIFICATE_FEATURE_SET_MISMATCH")
    if cert.admission_report_fingerprint != admission.fingerprint:
        errors.append("CERTIFICATE_ADMISSION_REPORT_MISMATCH")

    return {
        "valid": not errors,
        "errors": sorted(set(errors)),
        "formulation_id": item.formulation_id,
        "certificate_id": cert.certificate_id,
        "provider_manifest_id": manifest.manifest_id,
        "feature_set_id": features.feature_set_id,
        "admission_report_id": admission.report_id,
    }


def bind_formulation_execution_request(
    request: OptimizationRequest | Mapping[str, Any],
    formulation: SolverFormulation | Mapping[str, Any],
    certificate: SolverFormulationCertificate | Mapping[str, Any],
    *,
    feature_set: ModelFeatureSet | Mapping[str, Any],
    provider_manifest: ProviderCapabilityManifest | Mapping[str, Any],
    admission_report: ModelAdmissionReport | Mapping[str, Any],
) -> FormulationExecutionBinding:
    req = request if isinstance(request, OptimizationRequest) else OptimizationRequest.from_dict(request)
    item = formulation if isinstance(formulation, SolverFormulation) else SolverFormulation.from_dict(formulation)
    cert = certificate if isinstance(certificate, SolverFormulationCertificate) else SolverFormulationCertificate(**{
        **{k: v for k, v in dict(certificate).items() if k != "fingerprint"},
        "diagnostics": tuple(dict(certificate).get("diagnostics") or ()),
    })
    features = feature_set if isinstance(feature_set, ModelFeatureSet) else ModelFeatureSet.from_dict(feature_set)
    manifest = provider_manifest if isinstance(provider_manifest, ProviderCapabilityManifest) else ProviderCapabilityManifest.from_dict(provider_manifest)
    admission = _admission(admission_report)

    governance = validate_formulation_governance_chain(
        item,
        cert,
        feature_set=features,
        provider_manifest=manifest,
        admission_report=admission,
    )
    if not governance["valid"]:
        raise ValueError(f"invalid formulation governance chain: {governance['errors']}")
    if req.model.fingerprint != item.target_model.fingerprint:
        raise ValueError("optimization request does not bind the certified target formulation model")
    if not req.required_provider:
        raise ValueError("formulation-backed optimization request must require the exact target provider")
    if req.required_provider != item.target_provider_id:
        raise ValueError("optimization request required_provider does not match the certified formulation provider")
    if manifest.environment_fingerprint:
        if not req.environment_fingerprint:
            raise ValueError("provider manifest is environment-bound but optimization request has no environment fingerprint")
        if req.environment_fingerprint != manifest.environment_fingerprint:
            raise ValueError("optimization request environment does not match the provider capability manifest")

    return FormulationExecutionBinding(
        req.request_id,
        req.fingerprint,
        req.model.fingerprint,
        item.target_provider_id,
        item.formulation_id,
        item.fingerprint,
        cert.certificate_id,
        cert.fingerprint,
        manifest.manifest_id,
        manifest.fingerprint,
        features.feature_set_id,
        features.fingerprint,
        admission.report_id,
        admission.fingerprint,
        item.problem_revision_id,
        item.problem_revision_fingerprint,
        req.environment_fingerprint,
        metadata={
            "capability_id": req.capability_id,
            "capability_version": req.capability_version,
            "obligation_id": req.obligation_id,
            "semantic_fidelity": item.semantic_fidelity,
        },
    )


def formulation_execution_contract() -> dict[str, Any]:
    return {
        "contract_id": FORMULATION_EXECUTION_BINDING_CONTRACT_ID,
        "contract_version": FORMULATION_EXECUTION_BINDING_CONTRACT_VERSION,
        "stability": FORMULATION_EXECUTION_STABILITY,
        "required_certificate": "PASS_EXACT",
        "provider_binding": "EXACT_REQUIRED_PROVIDER",
        "model_binding": "EXACT_CERTIFIED_TARGET_MODEL_FINGERPRINT",
        "governance_binding": "FORMULATION_CERTIFICATE_PROVIDER_MANIFEST_FEATURE_SET_ADMISSION_REPORT_ALL_EXACT",
        "problem_revision_binding": "PRESERVED_WHEN_DECLARED",
        "environment_binding": "REQUIRED_WHEN_PROVIDER_MANIFEST_IS_ENVIRONMENT_BOUND",
        "execution_authority": "NONE_GRANTED_BY_BINDING",
        "provider_execution": "EXISTING_AASM_OPTIMIZATION_PROVIDER_PATH_ONLY",
        "result_authority": "NONE",
        "truth_authority": "NONE",
    }


__all__ = [
    "FORMULATION_EXECUTION_BINDING_CONTRACT_ID",
    "FORMULATION_EXECUTION_BINDING_CONTRACT_VERSION",
    "FORMULATION_EXECUTION_STABILITY",
    "FormulationExecutionBinding",
    "validate_formulation_governance_chain",
    "bind_formulation_execution_request",
    "formulation_execution_contract",
]
