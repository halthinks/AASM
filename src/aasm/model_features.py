from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from .semantic_result import semantic_fingerprint


MODEL_FEATURE_SET_CONTRACT_ID = "aasm.model.feature-set.v1"
MODEL_FEATURE_SET_CONTRACT_VERSION = "0.1.0"
PROVIDER_CAPABILITY_MANIFEST_CONTRACT_ID = "aasm.provider.capability-manifest.v1"
PROVIDER_CAPABILITY_MANIFEST_CONTRACT_VERSION = "0.1.0"
MODEL_ADMISSION_CONTRACT_ID = "aasm.model.admission.v1"
MODEL_ADMISSION_CONTRACT_VERSION = "0.1.0"
MODEL_FEATURE_STABILITY = "FOUNDATION_EXPERIMENTAL"

BUILTIN_MODEL_FEATURES = (
    "BOOLEAN",
    "BOUNDED_INTEGER",
    "LINEAR_REAL",
    "CARDINALITY",
    "PSEUDO_BOOLEAN",
    "GLOBAL_SCHEDULING",
    "SMT_THEORY",
    "NONLINEAR_CONTINUOUS",
    "CONIC",
    "QUADRATIC",
    "GEOMETRIC_PREDICATE",
    "BLACK_BOX_VERIFIER_CONSTRAINT",
    "TEMPORAL_TRACE_PROPERTY",
    "ROBUST_OR_SCENARIO_CONSTRAINT",
)
FEATURE_REQUIREMENT_LEVELS = (
    "EXACT_ONLY",
    "EXACT_OR_APPROXIMATE",
    "VERIFIER_ONLY_ALLOWED",
)
FEATURE_SUPPORT_LEVELS = (
    "EXACT_NATIVE",
    "EXACT_TRANSLATED",
    "APPROXIMATE_TRANSLATED",
    "VERIFIER_ONLY",
    "UNSUPPORTED",
)
EXACT_SUPPORT_LEVELS = frozenset({"EXACT_NATIVE", "EXACT_TRANSLATED"})


def _jsonable(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        return _jsonable(value.to_dict())
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))}
    if isinstance(value, (tuple, list, set)):
        return [_jsonable(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    raise TypeError(f"model feature value is not JSON serializable: {type(value)!r}")


def _uniq(values: Sequence[str]) -> tuple[str, ...]:
    return tuple(sorted(set(map(str, values))))


def _required(value: str, name: str) -> str:
    normalized = str(value).strip()
    if not normalized:
        raise ValueError(f"{name} is required")
    return normalized


@dataclass(frozen=True)
class ModelFeatureRequirement:
    feature_id: str
    requirement_level: str = "EXACT_ONLY"
    parameters: Mapping[str, Any] = field(default_factory=dict)
    source_reference_fingerprints: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "feature_id", _required(self.feature_id, "feature_id"))
        if self.requirement_level not in FEATURE_REQUIREMENT_LEVELS:
            raise ValueError(f"invalid feature requirement level: {self.requirement_level}")
        object.__setattr__(self, "parameters", _jsonable(dict(self.parameters)))
        object.__setattr__(self, "source_reference_fingerprints", _uniq(self.source_reference_fingerprints))
        object.__setattr__(self, "metadata", _jsonable(dict(self.metadata)))

    def identity_payload(self) -> dict[str, Any]:
        return {
            "feature_id": self.feature_id,
            "requirement_level": self.requirement_level,
            "parameters": _jsonable(self.parameters),
            "source_reference_fingerprints": list(self.source_reference_fingerprints),
            "metadata": _jsonable(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(self.identity_payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ModelFeatureRequirement":
        payload = deepcopy(dict(value))
        payload.pop("fingerprint", None)
        payload["source_reference_fingerprints"] = tuple(payload.get("source_reference_fingerprints") or ())
        return cls(**payload)


@dataclass(frozen=True)
class ModelFeatureSet:
    model_fingerprint: str
    features: tuple[ModelFeatureRequirement | Mapping[str, Any], ...]
    problem_revision_id: str = ""
    problem_revision_fingerprint: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)
    feature_set_id: str = ""
    contract_id: str = MODEL_FEATURE_SET_CONTRACT_ID
    contract_version: str = MODEL_FEATURE_SET_CONTRACT_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "model_fingerprint", _required(self.model_fingerprint, "model_fingerprint"))
        if self.contract_id != MODEL_FEATURE_SET_CONTRACT_ID or self.contract_version != MODEL_FEATURE_SET_CONTRACT_VERSION:
            raise ValueError("unsupported model feature-set contract")
        features = tuple(
            row if isinstance(row, ModelFeatureRequirement) else ModelFeatureRequirement.from_dict(row)
            for row in self.features
        )
        if not features:
            raise ValueError("model feature set requires at least one feature")
        feature_ids = [row.feature_id for row in features]
        if len(feature_ids) != len(set(feature_ids)):
            raise ValueError("model feature set cannot declare the same feature twice")
        object.__setattr__(self, "features", tuple(sorted(features, key=lambda row: row.feature_id)))
        object.__setattr__(self, "problem_revision_id", str(self.problem_revision_id).strip())
        object.__setattr__(self, "problem_revision_fingerprint", str(self.problem_revision_fingerprint).strip())
        if bool(self.problem_revision_id) != bool(self.problem_revision_fingerprint):
            raise ValueError("problem revision ID and fingerprint must be supplied together")
        object.__setattr__(self, "metadata", _jsonable(dict(self.metadata)))
        if not self.feature_set_id:
            object.__setattr__(self, "feature_set_id", f"model-feature-set-{semantic_fingerprint(self.identity_payload())[:24]}")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "model_fingerprint": self.model_fingerprint,
            "features": [row.to_dict() for row in self.features],
            "problem_revision_id": self.problem_revision_id,
            "problem_revision_fingerprint": self.problem_revision_fingerprint,
            "metadata": _jsonable(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"feature_set_id": self.feature_set_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"feature_set_id": self.feature_set_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ModelFeatureSet":
        payload = deepcopy(dict(value))
        payload.pop("fingerprint", None)
        payload["features"] = tuple(payload.get("features") or ())
        return cls(**payload)


@dataclass(frozen=True)
class ProviderFeatureSupport:
    feature_id: str
    support_level: str
    transformation_id: str = ""
    tolerance_policy_id: str = ""
    limitations: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "feature_id", _required(self.feature_id, "feature_id"))
        if self.support_level not in FEATURE_SUPPORT_LEVELS:
            raise ValueError(f"invalid feature support level: {self.support_level}")
        object.__setattr__(self, "transformation_id", str(self.transformation_id).strip())
        object.__setattr__(self, "tolerance_policy_id", str(self.tolerance_policy_id).strip())
        object.__setattr__(self, "limitations", _uniq(self.limitations))
        object.__setattr__(self, "metadata", _jsonable(dict(self.metadata)))
        if self.support_level in {"EXACT_TRANSLATED", "APPROXIMATE_TRANSLATED"} and not self.transformation_id:
            raise ValueError("translated feature support requires transformation_id")
        if self.support_level == "APPROXIMATE_TRANSLATED" and not self.tolerance_policy_id:
            raise ValueError("approximate translated support requires tolerance_policy_id")
        if self.support_level in {"EXACT_NATIVE", "VERIFIER_ONLY", "UNSUPPORTED"} and self.transformation_id:
            raise ValueError(f"{self.support_level} support cannot declare transformation_id")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "feature_id": self.feature_id,
            "support_level": self.support_level,
            "transformation_id": self.transformation_id,
            "tolerance_policy_id": self.tolerance_policy_id,
            "limitations": list(self.limitations),
            "metadata": _jsonable(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(self.identity_payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ProviderFeatureSupport":
        payload = deepcopy(dict(value))
        payload.pop("fingerprint", None)
        payload["limitations"] = tuple(payload.get("limitations") or ())
        return cls(**payload)


@dataclass(frozen=True)
class ProviderCapabilityManifest:
    provider_id: str
    provider_version: str
    adapter_id: str
    adapter_version: str
    feature_support: tuple[ProviderFeatureSupport | Mapping[str, Any], ...]
    solver_families: tuple[str, ...] = ()
    deterministic_profiles: tuple[str, ...] = ()
    proof_capabilities: tuple[str, ...] = ()
    solution_pool_capabilities: tuple[str, ...] = ()
    incremental_capabilities: tuple[str, ...] = ()
    status_capabilities: tuple[str, ...] = ()
    environment_fingerprint: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)
    manifest_id: str = ""
    contract_id: str = PROVIDER_CAPABILITY_MANIFEST_CONTRACT_ID
    contract_version: str = PROVIDER_CAPABILITY_MANIFEST_CONTRACT_VERSION

    def __post_init__(self) -> None:
        for name in ("provider_id", "provider_version", "adapter_id", "adapter_version"):
            object.__setattr__(self, name, _required(getattr(self, name), name))
        if self.contract_id != PROVIDER_CAPABILITY_MANIFEST_CONTRACT_ID or self.contract_version != PROVIDER_CAPABILITY_MANIFEST_CONTRACT_VERSION:
            raise ValueError("unsupported provider capability-manifest contract")
        support = tuple(
            row if isinstance(row, ProviderFeatureSupport) else ProviderFeatureSupport.from_dict(row)
            for row in self.feature_support
        )
        ids = [row.feature_id for row in support]
        if len(ids) != len(set(ids)):
            raise ValueError("provider capability manifest cannot declare the same feature twice")
        object.__setattr__(self, "feature_support", tuple(sorted(support, key=lambda row: row.feature_id)))
        for name in (
            "solver_families",
            "deterministic_profiles",
            "proof_capabilities",
            "solution_pool_capabilities",
            "incremental_capabilities",
            "status_capabilities",
        ):
            object.__setattr__(self, name, _uniq(getattr(self, name)))
        object.__setattr__(self, "environment_fingerprint", str(self.environment_fingerprint).strip())
        object.__setattr__(self, "metadata", _jsonable(dict(self.metadata)))
        if not self.manifest_id:
            object.__setattr__(self, "manifest_id", f"provider-capability-{semantic_fingerprint(self.identity_payload())[:24]}")

    @property
    def support_by_feature(self) -> dict[str, ProviderFeatureSupport]:
        return {row.feature_id: row for row in self.feature_support}

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "provider_id": self.provider_id,
            "provider_version": self.provider_version,
            "adapter_id": self.adapter_id,
            "adapter_version": self.adapter_version,
            "feature_support": [row.to_dict() for row in self.feature_support],
            "solver_families": list(self.solver_families),
            "deterministic_profiles": list(self.deterministic_profiles),
            "proof_capabilities": list(self.proof_capabilities),
            "solution_pool_capabilities": list(self.solution_pool_capabilities),
            "incremental_capabilities": list(self.incremental_capabilities),
            "status_capabilities": list(self.status_capabilities),
            "environment_fingerprint": self.environment_fingerprint,
            "metadata": _jsonable(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"manifest_id": self.manifest_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"manifest_id": self.manifest_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ProviderCapabilityManifest":
        payload = deepcopy(dict(value))
        payload.pop("fingerprint", None)
        payload["feature_support"] = tuple(payload.get("feature_support") or ())
        for name in (
            "solver_families",
            "deterministic_profiles",
            "proof_capabilities",
            "solution_pool_capabilities",
            "incremental_capabilities",
            "status_capabilities",
        ):
            payload[name] = tuple(payload.get(name) or ())
        return cls(**payload)


@dataclass(frozen=True)
class ModelAdmissionReport:
    feature_set_id: str
    feature_set_fingerprint: str
    provider_manifest_id: str
    provider_manifest_fingerprint: str
    admitted: bool
    exact: bool
    exact_features: tuple[str, ...] = ()
    approximate_features: tuple[str, ...] = ()
    verifier_only_features: tuple[str, ...] = ()
    unsupported_features: tuple[str, ...] = ()
    reasons: tuple[str, ...] = ()
    report_id: str = ""
    contract_id: str = MODEL_ADMISSION_CONTRACT_ID
    contract_version: str = MODEL_ADMISSION_CONTRACT_VERSION

    def __post_init__(self) -> None:
        for name in ("feature_set_id", "feature_set_fingerprint", "provider_manifest_id", "provider_manifest_fingerprint"):
            object.__setattr__(self, name, _required(getattr(self, name), name))
        if self.contract_id != MODEL_ADMISSION_CONTRACT_ID or self.contract_version != MODEL_ADMISSION_CONTRACT_VERSION:
            raise ValueError("unsupported model admission contract")
        for name in ("exact_features", "approximate_features", "verifier_only_features", "unsupported_features", "reasons"):
            object.__setattr__(self, name, _uniq(getattr(self, name)))
        accepted_categories = set(self.exact_features) | set(self.approximate_features) | set(self.verifier_only_features)
        if set(self.unsupported_features) & accepted_categories:
            raise ValueError("admission report cannot both accept and reject a feature")
        if self.admitted and self.unsupported_features:
            raise ValueError("admitted model cannot contain unsupported features")
        if bool(self.exact) != (bool(self.admitted) and not self.approximate_features and not self.verifier_only_features):
            raise ValueError("exact flag must reflect admitted all-exact support")
        if not self.report_id:
            object.__setattr__(self, "report_id", f"model-admission-{semantic_fingerprint(self.identity_payload())[:24]}")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "feature_set_id": self.feature_set_id,
            "feature_set_fingerprint": self.feature_set_fingerprint,
            "provider_manifest_id": self.provider_manifest_id,
            "provider_manifest_fingerprint": self.provider_manifest_fingerprint,
            "admitted": bool(self.admitted),
            "exact": bool(self.exact),
            "exact_features": list(self.exact_features),
            "approximate_features": list(self.approximate_features),
            "verifier_only_features": list(self.verifier_only_features),
            "unsupported_features": list(self.unsupported_features),
            "reasons": list(self.reasons),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"report_id": self.report_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"report_id": self.report_id, **self.identity_payload(), "fingerprint": self.fingerprint}


def evaluate_model_admission(
    feature_set: ModelFeatureSet | Mapping[str, Any],
    provider_manifest: ProviderCapabilityManifest | Mapping[str, Any],
) -> ModelAdmissionReport:
    required = feature_set if isinstance(feature_set, ModelFeatureSet) else ModelFeatureSet.from_dict(feature_set)
    manifest = provider_manifest if isinstance(provider_manifest, ProviderCapabilityManifest) else ProviderCapabilityManifest.from_dict(provider_manifest)
    support = manifest.support_by_feature

    exact: list[str] = []
    approximate: list[str] = []
    verifier_only: list[str] = []
    unsupported: list[str] = []
    reasons: list[str] = []

    for requirement in required.features:
        available = support.get(requirement.feature_id)
        level = "UNSUPPORTED" if available is None else available.support_level
        if level in EXACT_SUPPORT_LEVELS:
            exact.append(requirement.feature_id)
            continue
        if level == "APPROXIMATE_TRANSLATED":
            if requirement.requirement_level in {"EXACT_OR_APPROXIMATE", "VERIFIER_ONLY_ALLOWED"}:
                approximate.append(requirement.feature_id)
            else:
                unsupported.append(requirement.feature_id)
                reasons.append(f"{requirement.feature_id}:APPROXIMATION_FORBIDDEN")
            continue
        if level == "VERIFIER_ONLY":
            if requirement.requirement_level == "VERIFIER_ONLY_ALLOWED":
                verifier_only.append(requirement.feature_id)
            else:
                unsupported.append(requirement.feature_id)
                reasons.append(f"{requirement.feature_id}:VERIFIER_ONLY_NOT_ALLOWED")
            continue
        unsupported.append(requirement.feature_id)
        reasons.append(f"{requirement.feature_id}:UNSUPPORTED")

    admitted = not unsupported
    return ModelAdmissionReport(
        required.feature_set_id,
        required.fingerprint,
        manifest.manifest_id,
        manifest.fingerprint,
        admitted,
        admitted and not approximate and not verifier_only,
        tuple(exact),
        tuple(approximate),
        tuple(verifier_only),
        tuple(unsupported),
        tuple(reasons),
    )


def model_feature_contract() -> dict[str, Any]:
    return {
        "feature_set_contract_id": MODEL_FEATURE_SET_CONTRACT_ID,
        "feature_set_contract_version": MODEL_FEATURE_SET_CONTRACT_VERSION,
        "provider_manifest_contract_id": PROVIDER_CAPABILITY_MANIFEST_CONTRACT_ID,
        "provider_manifest_contract_version": PROVIDER_CAPABILITY_MANIFEST_CONTRACT_VERSION,
        "admission_contract_id": MODEL_ADMISSION_CONTRACT_ID,
        "admission_contract_version": MODEL_ADMISSION_CONTRACT_VERSION,
        "stability": MODEL_FEATURE_STABILITY,
        "builtin_features": list(BUILTIN_MODEL_FEATURES),
        "requirement_levels": list(FEATURE_REQUIREMENT_LEVELS),
        "support_levels": list(FEATURE_SUPPORT_LEVELS),
        "unsupported_feature_policy": "FAIL_CLOSED_BEFORE_PROVIDER_EXECUTION",
        "approximation_policy": "EXPLICIT_REQUIREMENT_AND_TOLERANCE_POLICY_REQUIRED",
        "verifier_only_policy": "EXPLICIT_REQUIREMENT_REQUIRED",
        "provider_manifest_authority": "CAPABILITY_EVIDENCE_ONLY",
        "truth_authority": "NONE",
    }


__all__ = [
    "MODEL_FEATURE_SET_CONTRACT_ID",
    "MODEL_FEATURE_SET_CONTRACT_VERSION",
    "PROVIDER_CAPABILITY_MANIFEST_CONTRACT_ID",
    "PROVIDER_CAPABILITY_MANIFEST_CONTRACT_VERSION",
    "MODEL_ADMISSION_CONTRACT_ID",
    "MODEL_ADMISSION_CONTRACT_VERSION",
    "MODEL_FEATURE_STABILITY",
    "BUILTIN_MODEL_FEATURES",
    "FEATURE_REQUIREMENT_LEVELS",
    "FEATURE_SUPPORT_LEVELS",
    "ModelFeatureRequirement",
    "ModelFeatureSet",
    "ProviderFeatureSupport",
    "ProviderCapabilityManifest",
    "ModelAdmissionReport",
    "evaluate_model_admission",
    "model_feature_contract",
]
