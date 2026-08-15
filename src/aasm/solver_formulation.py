from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from .model_features import ModelAdmissionReport, ModelFeatureSet, ProviderCapabilityManifest
from .optimization import OptimizationModel
from .runtime_v54 import SolverTranslation, SolverTranslationCertificate
from .semantic_evolution import ExternalReference
from .semantic_result import semantic_fingerprint


SOLVER_FORMULATION_CONTRACT_ID = "aasm.solver.formulation.v1"
SOLVER_FORMULATION_CONTRACT_VERSION = "0.1.0"
SOLVER_FORMULATION_CERTIFICATE_CONTRACT_ID = "aasm.solver.formulation-certificate.v1"
SOLVER_FORMULATION_CERTIFICATE_CONTRACT_VERSION = "0.1.0"
SOLVER_FORMULATION_STABILITY = "FOUNDATION_EXPERIMENTAL"
FORMULATION_OBJECT_KINDS = ("VARIABLE", "CONSTRAINT", "OBJECTIVE")
FORMULATION_MAPPING_KINDS = ("IDENTITY", "EXACT_TRANSFORM", "APPROXIMATE_TRANSFORM")
FORMULATION_FIDELITIES = ("EXACT", "APPROXIMATE")
FORMULATION_CERTIFICATE_STATUSES = ("PASS", "FAIL", "INCONCLUSIVE")
BUILTIN_FORMULATION_CHECKER_ID = "aasm.checker.solver-formulation.identity.v1"
BUILTIN_FORMULATION_CHECKER_VERSION = "0.1.0"
_OBJECTIVE_ID = "objective"


def _jsonable(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        return _jsonable(value.to_dict())
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))}
    if isinstance(value, (tuple, list, set)):
        return [_jsonable(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    raise TypeError(f"solver formulation value is not JSON serializable: {type(value)!r}")


def _uniq(values: Sequence[str]) -> tuple[str, ...]:
    return tuple(sorted(set(map(str, values))))


def _required(value: str, name: str) -> str:
    normalized = str(value).strip()
    if not normalized:
        raise ValueError(f"{name} is required")
    return normalized


def _semantic_model_payload(model: OptimizationModel) -> dict[str, Any]:
    return {
        "variables": [row.to_dict() for row in model.variables],
        "constraints": [row.to_dict() for row in model.constraints],
        "objective": None if model.objective is None else model.objective.to_dict(),
    }


def semantic_model_fingerprint(model: OptimizationModel | Mapping[str, Any]) -> str:
    parsed = model if isinstance(model, OptimizationModel) else OptimizationModel.from_dict(model)
    return semantic_fingerprint(_semantic_model_payload(parsed))


def _source_ids(model: OptimizationModel, kind: str) -> set[str]:
    if kind == "VARIABLE":
        return {row.variable_id for row in model.variables}
    if kind == "CONSTRAINT":
        return {row.constraint_id for row in model.constraints}
    if kind == "OBJECTIVE":
        return {_OBJECTIVE_ID} if model.objective is not None else set()
    raise ValueError(f"unsupported formulation object kind: {kind}")


def _target_ids(model: OptimizationModel, kind: str) -> set[str]:
    return _source_ids(model, kind)


@dataclass(frozen=True)
class FormulationObjectMapping:
    object_kind: str
    source_id: str
    target_ids: tuple[str, ...]
    mapping_kind: str = "IDENTITY"
    transformation_id: str = ""
    tolerance_policy_id: str = ""
    external_reference_fingerprints: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.object_kind not in FORMULATION_OBJECT_KINDS:
            raise ValueError(f"invalid formulation object kind: {self.object_kind}")
        object.__setattr__(self, "source_id", _required(self.source_id, "source_id"))
        target_ids = _uniq(self.target_ids)
        if not target_ids:
            raise ValueError("formulation mapping requires target_ids")
        object.__setattr__(self, "target_ids", target_ids)
        if self.mapping_kind not in FORMULATION_MAPPING_KINDS:
            raise ValueError(f"invalid formulation mapping kind: {self.mapping_kind}")
        object.__setattr__(self, "transformation_id", str(self.transformation_id).strip())
        object.__setattr__(self, "tolerance_policy_id", str(self.tolerance_policy_id).strip())
        object.__setattr__(self, "external_reference_fingerprints", _uniq(self.external_reference_fingerprints))
        object.__setattr__(self, "metadata", _jsonable(dict(self.metadata)))
        if self.mapping_kind == "IDENTITY":
            if self.target_ids != (self.source_id,):
                raise ValueError("IDENTITY mapping requires exactly the same source and target ID")
            if self.transformation_id or self.tolerance_policy_id:
                raise ValueError("IDENTITY mapping cannot declare transformation or tolerance policy")
        elif self.mapping_kind == "EXACT_TRANSFORM":
            if not self.transformation_id:
                raise ValueError("EXACT_TRANSFORM requires transformation_id")
            if self.tolerance_policy_id:
                raise ValueError("EXACT_TRANSFORM cannot declare approximation tolerance policy")
        else:
            if not self.transformation_id or not self.tolerance_policy_id:
                raise ValueError("APPROXIMATE_TRANSFORM requires transformation_id and tolerance_policy_id")

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(self.to_dict(include_fingerprint=False))

    def to_dict(self, *, include_fingerprint: bool = True) -> dict[str, Any]:
        out = {
            "object_kind": self.object_kind,
            "source_id": self.source_id,
            "target_ids": list(self.target_ids),
            "mapping_kind": self.mapping_kind,
            "transformation_id": self.transformation_id,
            "tolerance_policy_id": self.tolerance_policy_id,
            "external_reference_fingerprints": list(self.external_reference_fingerprints),
            "metadata": _jsonable(self.metadata),
        }
        if include_fingerprint:
            out["fingerprint"] = semantic_fingerprint(out)
        return out

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "FormulationObjectMapping":
        payload = deepcopy(dict(value)); payload.pop("fingerprint", None)
        payload["target_ids"] = tuple(payload.get("target_ids") or ())
        payload["external_reference_fingerprints"] = tuple(payload.get("external_reference_fingerprints") or ())
        return cls(**payload)


@dataclass(frozen=True)
class GeneratedFormulationObject:
    object_kind: str
    target_id: str
    transformation_id: str
    external_reference_fingerprints: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.object_kind not in FORMULATION_OBJECT_KINDS:
            raise ValueError(f"invalid generated formulation object kind: {self.object_kind}")
        object.__setattr__(self, "target_id", _required(self.target_id, "target_id"))
        object.__setattr__(self, "transformation_id", _required(self.transformation_id, "transformation_id"))
        object.__setattr__(self, "external_reference_fingerprints", _uniq(self.external_reference_fingerprints))
        object.__setattr__(self, "metadata", _jsonable(dict(self.metadata)))

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(self.to_dict(include_fingerprint=False))

    def to_dict(self, *, include_fingerprint: bool = True) -> dict[str, Any]:
        out = {
            "object_kind": self.object_kind,
            "target_id": self.target_id,
            "transformation_id": self.transformation_id,
            "external_reference_fingerprints": list(self.external_reference_fingerprints),
            "metadata": _jsonable(self.metadata),
        }
        if include_fingerprint:
            out["fingerprint"] = semantic_fingerprint(out)
        return out

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "GeneratedFormulationObject":
        payload = deepcopy(dict(value)); payload.pop("fingerprint", None)
        payload["external_reference_fingerprints"] = tuple(payload.get("external_reference_fingerprints") or ())
        return cls(**payload)


@dataclass(frozen=True)
class FormulationExternalReferenceBinding:
    reference: ExternalReference | Mapping[str, Any]
    source_object_kind: str
    source_object_id: str
    target_object_kind: str
    target_object_ids: tuple[str, ...]
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        reference = self.reference if isinstance(self.reference, ExternalReference) else ExternalReference.from_dict(self.reference)
        object.__setattr__(self, "reference", reference)
        if self.source_object_kind not in FORMULATION_OBJECT_KINDS or self.target_object_kind not in FORMULATION_OBJECT_KINDS:
            raise ValueError("external reference binding requires known source/target object kinds")
        object.__setattr__(self, "source_object_id", _required(self.source_object_id, "source_object_id"))
        targets = _uniq(self.target_object_ids)
        if not targets:
            raise ValueError("external reference binding requires target object IDs")
        object.__setattr__(self, "target_object_ids", targets)
        object.__setattr__(self, "metadata", _jsonable(dict(self.metadata)))

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(self.to_dict(include_fingerprint=False))

    def to_dict(self, *, include_fingerprint: bool = True) -> dict[str, Any]:
        out = {
            "reference": self.reference.to_dict(),
            "source_object_kind": self.source_object_kind,
            "source_object_id": self.source_object_id,
            "target_object_kind": self.target_object_kind,
            "target_object_ids": list(self.target_object_ids),
            "metadata": _jsonable(self.metadata),
        }
        if include_fingerprint:
            out["fingerprint"] = semantic_fingerprint(out)
        return out

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "FormulationExternalReferenceBinding":
        payload = deepcopy(dict(value)); payload.pop("fingerprint", None)
        payload["target_object_ids"] = tuple(payload.get("target_object_ids") or ())
        return cls(**payload)


@dataclass(frozen=True)
class SolverFormulation:
    source_model: OptimizationModel | Mapping[str, Any]
    target_model: OptimizationModel | Mapping[str, Any]
    target_provider_id: str
    provider_manifest_id: str
    provider_manifest_fingerprint: str
    feature_set_id: str
    feature_set_fingerprint: str
    admission_report_id: str
    admission_report_fingerprint: str
    semantic_fidelity: str
    object_mappings: tuple[FormulationObjectMapping | Mapping[str, Any], ...]
    generated_target_objects: tuple[GeneratedFormulationObject | Mapping[str, Any], ...] = ()
    external_reference_bindings: tuple[FormulationExternalReferenceBinding | Mapping[str, Any], ...] = ()
    problem_revision_id: str = ""
    problem_revision_fingerprint: str = ""
    predecessor_translation_id: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)
    formulation_id: str = ""
    contract_id: str = SOLVER_FORMULATION_CONTRACT_ID
    contract_version: str = SOLVER_FORMULATION_CONTRACT_VERSION

    def __post_init__(self) -> None:
        source = self.source_model if isinstance(self.source_model, OptimizationModel) else OptimizationModel.from_dict(self.source_model)
        target = self.target_model if isinstance(self.target_model, OptimizationModel) else OptimizationModel.from_dict(self.target_model)
        object.__setattr__(self, "source_model", source)
        object.__setattr__(self, "target_model", target)
        for name in (
            "target_provider_id", "provider_manifest_id", "provider_manifest_fingerprint",
            "feature_set_id", "feature_set_fingerprint", "admission_report_id", "admission_report_fingerprint",
        ):
            object.__setattr__(self, name, _required(getattr(self, name), name))
        if self.contract_id != SOLVER_FORMULATION_CONTRACT_ID or self.contract_version != SOLVER_FORMULATION_CONTRACT_VERSION:
            raise ValueError("unsupported solver formulation contract")
        if self.semantic_fidelity not in FORMULATION_FIDELITIES:
            raise ValueError(f"invalid formulation fidelity: {self.semantic_fidelity}")
        mappings = tuple(row if isinstance(row, FormulationObjectMapping) else FormulationObjectMapping.from_dict(row) for row in self.object_mappings)
        generated = tuple(row if isinstance(row, GeneratedFormulationObject) else GeneratedFormulationObject.from_dict(row) for row in self.generated_target_objects)
        bindings = tuple(row if isinstance(row, FormulationExternalReferenceBinding) else FormulationExternalReferenceBinding.from_dict(row) for row in self.external_reference_bindings)
        map_keys = [(row.object_kind, row.source_id) for row in mappings]
        if len(map_keys) != len(set(map_keys)):
            raise ValueError("solver formulation may map each source object only once")
        generated_keys = [(row.object_kind, row.target_id) for row in generated]
        if len(generated_keys) != len(set(generated_keys)):
            raise ValueError("duplicate generated target formulation object")
        if len({row.fingerprint for row in bindings}) != len(bindings):
            raise ValueError("duplicate external reference formulation binding")
        object.__setattr__(self, "object_mappings", tuple(sorted(mappings, key=lambda row: (row.object_kind, row.source_id))))
        object.__setattr__(self, "generated_target_objects", tuple(sorted(generated, key=lambda row: (row.object_kind, row.target_id))))
        object.__setattr__(self, "external_reference_bindings", tuple(sorted(bindings, key=lambda row: (row.reference.key, row.source_object_kind, row.source_object_id))))
        object.__setattr__(self, "problem_revision_id", str(self.problem_revision_id).strip())
        object.__setattr__(self, "problem_revision_fingerprint", str(self.problem_revision_fingerprint).strip())
        if bool(self.problem_revision_id) != bool(self.problem_revision_fingerprint):
            raise ValueError("problem revision ID and fingerprint must be supplied together")
        object.__setattr__(self, "predecessor_translation_id", str(self.predecessor_translation_id).strip())
        object.__setattr__(self, "metadata", _jsonable(dict(self.metadata)))
        if self.semantic_fidelity == "EXACT" and any(row.mapping_kind == "APPROXIMATE_TRANSFORM" for row in mappings):
            raise ValueError("EXACT formulation cannot contain approximate object mappings")
        if self.semantic_fidelity == "APPROXIMATE" and not any(row.mapping_kind == "APPROXIMATE_TRANSFORM" for row in mappings):
            raise ValueError("APPROXIMATE formulation must identify at least one approximate mapping")
        if not self.formulation_id:
            object.__setattr__(self, "formulation_id", f"solver-formulation-{semantic_fingerprint(self.identity_payload())[:24]}")

    @property
    def source_semantic_fingerprint(self) -> str:
        return semantic_model_fingerprint(self.source_model)

    @property
    def target_semantic_fingerprint(self) -> str:
        return semantic_model_fingerprint(self.target_model)

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "source_model": self.source_model.to_dict(),
            "source_semantic_fingerprint": self.source_semantic_fingerprint,
            "target_model": self.target_model.to_dict(),
            "target_semantic_fingerprint": self.target_semantic_fingerprint,
            "target_provider_id": self.target_provider_id,
            "target_family": self.target_model.solver_family,
            "provider_manifest_id": self.provider_manifest_id,
            "provider_manifest_fingerprint": self.provider_manifest_fingerprint,
            "feature_set_id": self.feature_set_id,
            "feature_set_fingerprint": self.feature_set_fingerprint,
            "admission_report_id": self.admission_report_id,
            "admission_report_fingerprint": self.admission_report_fingerprint,
            "semantic_fidelity": self.semantic_fidelity,
            "object_mappings": [row.to_dict() for row in self.object_mappings],
            "generated_target_objects": [row.to_dict() for row in self.generated_target_objects],
            "external_reference_bindings": [row.to_dict() for row in self.external_reference_bindings],
            "problem_revision_id": self.problem_revision_id,
            "problem_revision_fingerprint": self.problem_revision_fingerprint,
            "predecessor_translation_id": self.predecessor_translation_id,
            "metadata": _jsonable(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"formulation_id": self.formulation_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"formulation_id": self.formulation_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SolverFormulation":
        payload = deepcopy(dict(value))
        for key in ("fingerprint", "source_semantic_fingerprint", "target_semantic_fingerprint", "target_family"):
            payload.pop(key, None)
        payload["object_mappings"] = tuple(payload.get("object_mappings") or ())
        payload["generated_target_objects"] = tuple(payload.get("generated_target_objects") or ())
        payload["external_reference_bindings"] = tuple(payload.get("external_reference_bindings") or ())
        return cls(**payload)


@dataclass(frozen=True)
class SolverFormulationCertificate:
    formulation_id: str
    formulation_fingerprint: str
    source_model_fingerprint: str
    target_model_fingerprint: str
    provider_manifest_fingerprint: str
    feature_set_fingerprint: str
    admission_report_fingerprint: str
    requested_fidelity: str
    verified_fidelity: str
    mapping_complete: bool
    external_references_resolved: bool
    status: str
    diagnostics: tuple[str, ...] = ()
    checker_id: str = BUILTIN_FORMULATION_CHECKER_ID
    checker_version: str = BUILTIN_FORMULATION_CHECKER_VERSION
    certificate_id: str = ""
    contract_id: str = SOLVER_FORMULATION_CERTIFICATE_CONTRACT_ID
    contract_version: str = SOLVER_FORMULATION_CERTIFICATE_CONTRACT_VERSION

    def __post_init__(self) -> None:
        for name in (
            "formulation_id", "formulation_fingerprint", "source_model_fingerprint", "target_model_fingerprint",
            "provider_manifest_fingerprint", "feature_set_fingerprint", "admission_report_fingerprint", "checker_id", "checker_version",
        ):
            object.__setattr__(self, name, _required(getattr(self, name), name))
        if self.contract_id != SOLVER_FORMULATION_CERTIFICATE_CONTRACT_ID or self.contract_version != SOLVER_FORMULATION_CERTIFICATE_CONTRACT_VERSION:
            raise ValueError("unsupported solver formulation certificate contract")
        if self.requested_fidelity not in FORMULATION_FIDELITIES:
            raise ValueError("invalid requested formulation fidelity")
        if self.verified_fidelity not in {"EXACT", "APPROXIMATE", "NONE"}:
            raise ValueError("invalid verified formulation fidelity")
        if self.status not in FORMULATION_CERTIFICATE_STATUSES:
            raise ValueError("invalid formulation certificate status")
        object.__setattr__(self, "diagnostics", _uniq(self.diagnostics))
        if self.status == "PASS":
            if not self.mapping_complete or not self.external_references_resolved:
                raise ValueError("passing formulation certificate requires complete mappings and resolved external references")
            if self.verified_fidelity != self.requested_fidelity:
                raise ValueError("passing formulation certificate must verify the requested fidelity")
        if not self.certificate_id:
            object.__setattr__(self, "certificate_id", f"solver-formulation-certificate-{semantic_fingerprint(self.identity_payload())[:24]}")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "formulation_id": self.formulation_id,
            "formulation_fingerprint": self.formulation_fingerprint,
            "source_model_fingerprint": self.source_model_fingerprint,
            "target_model_fingerprint": self.target_model_fingerprint,
            "provider_manifest_fingerprint": self.provider_manifest_fingerprint,
            "feature_set_fingerprint": self.feature_set_fingerprint,
            "admission_report_fingerprint": self.admission_report_fingerprint,
            "requested_fidelity": self.requested_fidelity,
            "verified_fidelity": self.verified_fidelity,
            "mapping_complete": bool(self.mapping_complete),
            "external_references_resolved": bool(self.external_references_resolved),
            "status": self.status,
            "diagnostics": list(self.diagnostics),
            "checker_id": self.checker_id,
            "checker_version": self.checker_version,
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"certificate_id": self.certificate_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"certificate_id": self.certificate_id, **self.identity_payload(), "fingerprint": self.fingerprint}


def _check_mapping_completeness(formulation: SolverFormulation, diagnostics: list[str]) -> bool:
    complete = True
    mapped_target: dict[str, set[str]] = {kind: set() for kind in FORMULATION_OBJECT_KINDS}
    generated_target: dict[str, set[str]] = {kind: set() for kind in FORMULATION_OBJECT_KINDS}
    for mapping in formulation.object_mappings:
        if mapping.source_id not in _source_ids(formulation.source_model, mapping.object_kind):
            diagnostics.append(f"UNKNOWN_SOURCE_{mapping.object_kind}:{mapping.source_id}")
            complete = False
        allowed_targets = _target_ids(formulation.target_model, mapping.object_kind)
        for target_id in mapping.target_ids:
            if target_id not in allowed_targets:
                diagnostics.append(f"UNKNOWN_TARGET_{mapping.object_kind}:{target_id}")
                complete = False
            if target_id in mapped_target[mapping.object_kind]:
                diagnostics.append(f"DUPLICATE_TARGET_MAPPING_{mapping.object_kind}:{target_id}")
                complete = False
            mapped_target[mapping.object_kind].add(target_id)
    for generated in formulation.generated_target_objects:
        if generated.target_id not in _target_ids(formulation.target_model, generated.object_kind):
            diagnostics.append(f"UNKNOWN_GENERATED_TARGET_{generated.object_kind}:{generated.target_id}")
            complete = False
        if generated.target_id in generated_target[generated.object_kind] or generated.target_id in mapped_target[generated.object_kind]:
            diagnostics.append(f"DUPLICATE_GENERATED_TARGET_{generated.object_kind}:{generated.target_id}")
            complete = False
        generated_target[generated.object_kind].add(generated.target_id)
    for kind in FORMULATION_OBJECT_KINDS:
        sources = _source_ids(formulation.source_model, kind)
        mapped_sources = {row.source_id for row in formulation.object_mappings if row.object_kind == kind}
        missing_sources = sorted(sources - mapped_sources)
        if missing_sources:
            diagnostics.append(f"UNMAPPED_SOURCE_{kind}:{','.join(missing_sources)}")
            complete = False
        targets = _target_ids(formulation.target_model, kind)
        missing_targets = sorted(targets - mapped_target[kind] - generated_target[kind])
        if missing_targets:
            diagnostics.append(f"UNACCOUNTED_TARGET_{kind}:{','.join(missing_targets)}")
            complete = False
    return complete


def _check_external_reference_bindings(formulation: SolverFormulation, diagnostics: list[str]) -> bool:
    resolved = True
    declared_refs = {row.reference.fingerprint for row in formulation.external_reference_bindings}
    for mapping in formulation.object_mappings:
        missing = sorted(set(mapping.external_reference_fingerprints) - declared_refs)
        if missing:
            diagnostics.append(f"MAPPING_EXTERNAL_REFERENCE_NOT_BOUND:{mapping.object_kind}:{mapping.source_id}:{','.join(missing)}")
            resolved = False
    for generated in formulation.generated_target_objects:
        missing = sorted(set(generated.external_reference_fingerprints) - declared_refs)
        if missing:
            diagnostics.append(f"GENERATED_EXTERNAL_REFERENCE_NOT_BOUND:{generated.object_kind}:{generated.target_id}:{','.join(missing)}")
            resolved = False
    for binding in formulation.external_reference_bindings:
        if binding.source_object_id not in _source_ids(formulation.source_model, binding.source_object_kind):
            diagnostics.append(f"REFERENCE_UNKNOWN_SOURCE:{binding.reference.key}:{binding.source_object_kind}:{binding.source_object_id}")
            resolved = False
        target_ids = _target_ids(formulation.target_model, binding.target_object_kind)
        missing_targets = sorted(set(binding.target_object_ids) - target_ids)
        if missing_targets:
            diagnostics.append(f"REFERENCE_UNKNOWN_TARGET:{binding.reference.key}:{','.join(missing_targets)}")
            resolved = False
    return resolved


def verify_solver_formulation_identity(formulation: SolverFormulation | Mapping[str, Any]) -> SolverFormulationCertificate:
    item = formulation if isinstance(formulation, SolverFormulation) else SolverFormulation.from_dict(formulation)
    diagnostics: list[str] = []
    mapping_complete = _check_mapping_completeness(item, diagnostics)
    refs_resolved = _check_external_reference_bindings(item, diagnostics)
    identity_only = all(row.mapping_kind == "IDENTITY" for row in item.object_mappings) and not item.generated_target_objects
    if not identity_only:
        diagnostics.append("BUILTIN_CHECKER_SUPPORTS_IDENTITY_ONLY")
    if item.source_semantic_fingerprint != item.target_semantic_fingerprint:
        diagnostics.append("SEMANTIC_PROJECTION_MISMATCH")
    if item.semantic_fidelity != "EXACT":
        diagnostics.append("BUILTIN_CHECKER_DOES_NOT_CERTIFY_APPROXIMATE_FIDELITY")
    if diagnostics:
        status = "FAIL" if any(
            text.startswith(("UNKNOWN_", "DUPLICATE_", "UNMAPPED_", "UNACCOUNTED_", "MAPPING_", "GENERATED_", "REFERENCE_", "SEMANTIC_"))
            for text in diagnostics
        ) else "INCONCLUSIVE"
        verified = "NONE"
    else:
        status = "PASS"
        verified = "EXACT"
    return SolverFormulationCertificate(
        item.formulation_id,
        item.fingerprint,
        item.source_model.fingerprint,
        item.target_model.fingerprint,
        item.provider_manifest_fingerprint,
        item.feature_set_fingerprint,
        item.admission_report_fingerprint,
        item.semantic_fidelity,
        verified,
        mapping_complete,
        refs_resolved,
        status,
        tuple(diagnostics),
    )


def identity_object_mappings(source: OptimizationModel | Mapping[str, Any]) -> tuple[FormulationObjectMapping, ...]:
    model = source if isinstance(source, OptimizationModel) else OptimizationModel.from_dict(source)
    out = [FormulationObjectMapping("VARIABLE", row.variable_id, (row.variable_id,)) for row in model.variables]
    out.extend(FormulationObjectMapping("CONSTRAINT", row.constraint_id, (row.constraint_id,)) for row in model.constraints)
    if model.objective is not None:
        out.append(FormulationObjectMapping("OBJECTIVE", _OBJECTIVE_ID, (_OBJECTIVE_ID,)))
    return tuple(out)


def formulation_from_v54_translation(
    source_model: OptimizationModel | Mapping[str, Any],
    translation: SolverTranslation | Mapping[str, Any],
    translation_certificate: SolverTranslationCertificate | Mapping[str, Any],
    *,
    feature_set: ModelFeatureSet | Mapping[str, Any],
    provider_manifest: ProviderCapabilityManifest | Mapping[str, Any],
    admission_report: ModelAdmissionReport | Mapping[str, Any],
    external_reference_bindings: Sequence[FormulationExternalReferenceBinding | Mapping[str, Any]] = (),
    problem_revision_id: str = "",
    problem_revision_fingerprint: str = "",
) -> tuple[SolverFormulation, SolverFormulationCertificate]:
    source = source_model if isinstance(source_model, OptimizationModel) else OptimizationModel.from_dict(source_model)
    translated = translation if isinstance(translation, SolverTranslation) else SolverTranslation.from_dict(translation)
    cert = translation_certificate if isinstance(translation_certificate, SolverTranslationCertificate) else SolverTranslationCertificate.from_dict(translation_certificate)
    features = feature_set if isinstance(feature_set, ModelFeatureSet) else ModelFeatureSet.from_dict(feature_set)
    manifest = provider_manifest if isinstance(provider_manifest, ProviderCapabilityManifest) else ProviderCapabilityManifest.from_dict(provider_manifest)
    if isinstance(admission_report, ModelAdmissionReport):
        admission = admission_report
    else:
        payload = deepcopy(dict(admission_report)); payload.pop("fingerprint", None)
        admission = ModelAdmissionReport(**payload)

    if cert.status != "PASS" or not cert.exact_semantic_match:
        raise ValueError("v0.54 translation bridge requires a passing exact translation certificate")
    if translated.translation_id != cert.translation_id or translated.fingerprint != cert.translation_fingerprint:
        raise ValueError("translation certificate does not bind the supplied v0.54 translation")
    if translated.source_model_fingerprint != source.fingerprint:
        raise ValueError("v0.54 translation source model mismatch")
    if translated.target_provider_id != manifest.provider_id:
        raise ValueError("provider manifest does not match v0.54 target provider")
    if manifest.solver_families and translated.target_family not in manifest.solver_families:
        raise ValueError("provider manifest does not declare the translated target solver family")
    if features.model_fingerprint != source.fingerprint:
        raise ValueError("model feature set does not bind the source optimization model")
    if admission.feature_set_id != features.feature_set_id or admission.feature_set_fingerprint != features.fingerprint:
        raise ValueError("model admission report does not bind the supplied feature set")
    if admission.provider_manifest_id != manifest.manifest_id or admission.provider_manifest_fingerprint != manifest.fingerprint:
        raise ValueError("model admission report does not bind the supplied provider manifest")
    if not admission.admitted or not admission.exact:
        raise ValueError("v0.54 exact formulation bridge requires exact provider admission")
    if bool(problem_revision_id) != bool(problem_revision_fingerprint):
        raise ValueError("problem revision ID and fingerprint must be supplied together")
    if features.problem_revision_id:
        if features.problem_revision_id != problem_revision_id or features.problem_revision_fingerprint != problem_revision_fingerprint:
            raise ValueError("problem revision binding does not match the feature-set revision")

    formulation = SolverFormulation(
        source,
        translated.target_model,
        translated.target_provider_id,
        manifest.manifest_id,
        manifest.fingerprint,
        features.feature_set_id,
        features.fingerprint,
        admission.report_id,
        admission.fingerprint,
        "EXACT",
        identity_object_mappings(source),
        external_reference_bindings=tuple(external_reference_bindings),
        problem_revision_id=problem_revision_id,
        problem_revision_fingerprint=problem_revision_fingerprint,
        predecessor_translation_id=translated.translation_id,
        metadata={
            "v54_translation_fingerprint": translated.fingerprint,
            "v54_translation_certificate_id": cert.certificate_id,
            "v54_translation_certificate_fingerprint": cert.fingerprint,
        },
    )
    return formulation, verify_solver_formulation_identity(formulation)


def solver_formulation_contract() -> dict[str, Any]:
    return {
        "formulation_contract_id": SOLVER_FORMULATION_CONTRACT_ID,
        "formulation_contract_version": SOLVER_FORMULATION_CONTRACT_VERSION,
        "certificate_contract_id": SOLVER_FORMULATION_CERTIFICATE_CONTRACT_ID,
        "certificate_contract_version": SOLVER_FORMULATION_CERTIFICATE_CONTRACT_VERSION,
        "stability": SOLVER_FORMULATION_STABILITY,
        "object_kinds": list(FORMULATION_OBJECT_KINDS),
        "mapping_kinds": list(FORMULATION_MAPPING_KINDS),
        "fidelities": list(FORMULATION_FIDELITIES),
        "source_object_policy": "EVERY_SOURCE_OBJECT_MAPPED_EXACTLY_ONCE",
        "target_object_policy": "EVERY_TARGET_OBJECT_MAPPED_OR_EXPLICITLY_GENERATED",
        "external_reference_policy": "REFERENCES_BIND_TO_EXPLICIT_SOURCE_AND_TARGET_OBJECTS",
        "nontrivial_translation_policy": "NO_PASS_WITHOUT_AN_INDEPENDENT_CHECKER_FOR_THE_REQUESTED_FIDELITY",
        "builtin_checker": BUILTIN_FORMULATION_CHECKER_ID,
        "builtin_checker_scope": "EXACT_IDENTITY_ONLY",
        "v54_translation": "REUSED_AS_FIRST_EXACT_IDENTITY_FORMULATION",
        "provider_capability_manifest": "MANDATORY_BINDING",
        "model_admission": "MANDATORY_BINDING",
        "result_authority": "EVIDENCE_ONLY",
        "truth_authority": "NONE",
    }


__all__ = [
    "SOLVER_FORMULATION_CONTRACT_ID",
    "SOLVER_FORMULATION_CONTRACT_VERSION",
    "SOLVER_FORMULATION_CERTIFICATE_CONTRACT_ID",
    "SOLVER_FORMULATION_CERTIFICATE_CONTRACT_VERSION",
    "SOLVER_FORMULATION_STABILITY",
    "FORMULATION_OBJECT_KINDS",
    "FORMULATION_MAPPING_KINDS",
    "FORMULATION_FIDELITIES",
    "FORMULATION_CERTIFICATE_STATUSES",
    "BUILTIN_FORMULATION_CHECKER_ID",
    "BUILTIN_FORMULATION_CHECKER_VERSION",
    "FormulationObjectMapping",
    "GeneratedFormulationObject",
    "FormulationExternalReferenceBinding",
    "SolverFormulation",
    "SolverFormulationCertificate",
    "semantic_model_fingerprint",
    "verify_solver_formulation_identity",
    "identity_object_mappings",
    "formulation_from_v54_translation",
    "solver_formulation_contract",
]
