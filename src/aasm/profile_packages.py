from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
import hashlib
from importlib import metadata as importlib_metadata
import json
from pathlib import Path
import re
from typing import Any, Iterable


PROFILE_CONTRACT = "0.22"
PROFILE_ENTRY_POINT_GROUP = "aasm.profiles"
PROFILE_ID_RE = re.compile(r"^[a-z0-9](?:[a-z0-9._-]*[a-z0-9])?$")
SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?"
    r"(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$"
)
ADAPTER_ROLES = {
    "decision_backend",
    "obligation_adapter",
    "semantic_validator",
    "conflict_explainer",
    "constraint_certifier",
}
EVOLUTION_MODES = {"FROZEN", "MANUAL", "PROPOSAL_ONLY", "GOVERNED_AUTO_CANDIDATE"}
MIGRATION_COMPATIBILITY = {"BACKWARD_COMPATIBLE", "REQUIRES_MIGRATION", "BREAKING"}
PROPOSAL_STATUSES = {"PROPOSED", "APPROVED", "REJECTED", "APPLIED", "SUPERSEDED"}


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _unique(values: Iterable[str]) -> list[str]:
    return sorted(set(str(value) for value in values))


def _require_semver(value: str, field_name: str) -> None:
    if not SEMVER_RE.fullmatch(value):
        raise ValueError(f"{field_name} must be semantic version text: {value!r}")


def _semver_key(value: str) -> tuple[int, int, int, str]:
    match = SEMVER_RE.fullmatch(value)
    if not match:
        raise ValueError(f"invalid semantic version: {value!r}")
    major, minor, patch, prerelease, _build = match.groups()
    # A stable ordering is sufficient for registry selection. Stable releases
    # sort after prereleases with the same numeric triplet.
    suffix = "~" if prerelease is None else prerelease
    return int(major), int(minor), int(patch), suffix


@dataclass
class AdapterBinding:
    role: str
    target: str
    required: bool = False
    deterministic: bool = True
    capabilities: list[str] = field(default_factory=list)
    config: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.role not in ADAPTER_ROLES:
            raise ValueError(f"unknown adapter role: {self.role}")
        if not self.target or ":" not in self.target or any(ch.isspace() for ch in self.target):
            raise ValueError("adapter target must be an import target in module:attribute form")
        module_name, attribute = self.target.split(":", 1)
        if not module_name or not attribute:
            raise ValueError("adapter target must include both module and attribute")
        self.capabilities = _unique(self.capabilities)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AdapterBinding":
        return cls(**deepcopy(data))


@dataclass
class ProfileEvolutionPolicy:
    mode: str = "MANUAL"
    allow_runtime_proposals: bool = True
    require_explicit_activation: bool = True
    require_conformance: bool = True
    require_migration_for_breaking: bool = True
    minimum_evidence_count: int = 1
    allowed_activation_actors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.mode not in EVOLUTION_MODES:
            raise ValueError(f"invalid profile evolution mode: {self.mode}")
        if self.minimum_evidence_count < 0:
            raise ValueError("minimum_evidence_count must be non-negative")
        self.allowed_activation_actors = _unique(self.allowed_activation_actors)
        if self.mode == "FROZEN":
            self.allow_runtime_proposals = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "ProfileEvolutionPolicy":
        return cls(**deepcopy(data or {}))


@dataclass
class ProfileMigration:
    migration_id: str
    from_version: str
    to_version: str
    compatibility: str = "REQUIRES_MIGRATION"
    operations: list[dict[str, Any]] = field(default_factory=list)
    evidence_ids: list[str] = field(default_factory=list)
    checksum: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.migration_id:
            raise ValueError("migration_id is required")
        _require_semver(self.from_version, "from_version")
        _require_semver(self.to_version, "to_version")
        if self.from_version == self.to_version:
            raise ValueError("profile migration must change the profile version")
        if self.compatibility not in MIGRATION_COMPATIBILITY:
            raise ValueError(f"invalid migration compatibility: {self.compatibility}")
        if self.compatibility in {"REQUIRES_MIGRATION", "BREAKING"} and not self.operations:
            raise ValueError(f"{self.compatibility} migration requires explicit operations")
        self.evidence_ids = _unique(self.evidence_ids)
        if self.checksum is None:
            self.checksum = canonical_hash(
                {
                    "migration_id": self.migration_id,
                    "from_version": self.from_version,
                    "to_version": self.to_version,
                    "compatibility": self.compatibility,
                    "operations": self.operations,
                }
            )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProfileMigration":
        return cls(**deepcopy(data))


@dataclass
class AASMProfile:
    profile_id: str
    profile_version: str
    description: str
    aasm_contract: str = PROFILE_CONTRACT
    machine_definition: str = "aasm.evolve"
    decision_namespaces: list[str] = field(default_factory=list)
    obligation_kinds: list[str] = field(default_factory=list)
    evidence_kinds: list[str] = field(default_factory=list)
    artifact_kinds: list[str] = field(default_factory=list)
    adapters: dict[str, AdapterBinding] = field(default_factory=dict)
    policies: dict[str, Any] = field(default_factory=dict)
    capabilities: list[str] = field(default_factory=list)
    migrations: list[ProfileMigration] = field(default_factory=list)
    evolution_policy: ProfileEvolutionPolicy = field(default_factory=ProfileEvolutionPolicy)
    metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: int = 1

    def __post_init__(self):
        if not PROFILE_ID_RE.fullmatch(self.profile_id):
            raise ValueError(
                "profile_id must contain lowercase letters, numbers, dots, underscores, or hyphens"
            )
        _require_semver(self.profile_version, "profile_version")
        if self.aasm_contract != PROFILE_CONTRACT:
            raise ValueError(
                f"profile contract {self.aasm_contract!r} is not supported by runtime contract {PROFILE_CONTRACT!r}"
            )
        if not self.description.strip():
            raise ValueError("profile description is required")
        if not self.machine_definition.strip():
            raise ValueError("machine_definition is required")
        if self.schema_version != 1:
            raise ValueError("unsupported profile schema_version")
        self.decision_namespaces = _unique(self.decision_namespaces)
        self.obligation_kinds = _unique(self.obligation_kinds)
        self.evidence_kinds = _unique(self.evidence_kinds)
        self.artifact_kinds = _unique(self.artifact_kinds)
        self.capabilities = _unique(self.capabilities)
        normalized_adapters: dict[str, AdapterBinding] = {}
        for role, binding in self.adapters.items():
            item = binding if isinstance(binding, AdapterBinding) else AdapterBinding.from_dict(binding)
            if role != item.role:
                raise ValueError(f"adapter map key {role!r} does not match binding role {item.role!r}")
            normalized_adapters[role] = item
        self.adapters = normalized_adapters
        self.migrations = [
            item if isinstance(item, ProfileMigration) else ProfileMigration.from_dict(item)
            for item in self.migrations
        ]
        if not isinstance(self.evolution_policy, ProfileEvolutionPolicy):
            self.evolution_policy = ProfileEvolutionPolicy.from_dict(self.evolution_policy)

    def to_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out["adapters"] = {
            role: binding.to_dict()
            for role, binding in sorted(self.adapters.items())
        }
        out["migrations"] = [migration.to_dict() for migration in self.migrations]
        out["evolution_policy"] = self.evolution_policy.to_dict()
        return out

    @property
    def fingerprint(self) -> str:
        return canonical_hash(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AASMProfile":
        payload = deepcopy(data)
        payload["adapters"] = {
            role: AdapterBinding.from_dict(binding)
            for role, binding in (payload.get("adapters") or {}).items()
        }
        payload["migrations"] = [
            ProfileMigration.from_dict(item) for item in payload.get("migrations", [])
        ]
        payload["evolution_policy"] = ProfileEvolutionPolicy.from_dict(
            payload.get("evolution_policy")
        )
        return cls(**payload)

    @classmethod
    def load(cls, path: str | Path) -> "AASMProfile":
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.from_dict(raw)


@dataclass
class AASMPackageManifest:
    package_id: str
    package_version: str
    description: str
    profiles: list[str]
    aasm_contract: str = PROFILE_CONTRACT
    distribution_name: str | None = None
    authors: list[str] = field(default_factory=list)
    license: str = ""
    homepage: str | None = None
    adapter_entry_points: dict[str, str] = field(default_factory=dict)
    migrations: list[ProfileMigration] = field(default_factory=list)
    evolution_policy: ProfileEvolutionPolicy = field(default_factory=ProfileEvolutionPolicy)
    metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: int = 1

    def __post_init__(self):
        if not PROFILE_ID_RE.fullmatch(self.package_id):
            raise ValueError("package_id has invalid characters")
        _require_semver(self.package_version, "package_version")
        if self.aasm_contract != PROFILE_CONTRACT:
            raise ValueError("package targets an unsupported AASM contract")
        if not self.description.strip():
            raise ValueError("package description is required")
        self.profiles = _unique(self.profiles)
        if not self.profiles:
            raise ValueError("package manifest must list at least one profile")
        self.authors = _unique(self.authors)
        unknown_roles = sorted(set(self.adapter_entry_points) - ADAPTER_ROLES)
        if unknown_roles:
            raise ValueError(f"package contains unknown adapter entry-point roles: {unknown_roles}")
        for role, target in self.adapter_entry_points.items():
            AdapterBinding(role, target)
        self.migrations = [
            item if isinstance(item, ProfileMigration) else ProfileMigration.from_dict(item)
            for item in self.migrations
        ]
        if not isinstance(self.evolution_policy, ProfileEvolutionPolicy):
            self.evolution_policy = ProfileEvolutionPolicy.from_dict(self.evolution_policy)

    def to_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out["migrations"] = [migration.to_dict() for migration in self.migrations]
        out["evolution_policy"] = self.evolution_policy.to_dict()
        return out

    @property
    def fingerprint(self) -> str:
        return canonical_hash(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AASMPackageManifest":
        payload = deepcopy(data)
        payload["migrations"] = [
            ProfileMigration.from_dict(item) for item in payload.get("migrations", [])
        ]
        payload["evolution_policy"] = ProfileEvolutionPolicy.from_dict(
            payload.get("evolution_policy")
        )
        return cls(**payload)

    @classmethod
    def load(cls, path: str | Path) -> "AASMPackageManifest":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


@dataclass
class ProfileBinding:
    profile_id: str
    profile_version: str
    aasm_contract: str
    profile_fingerprint: str
    configuration: dict[str, Any] = field(default_factory=dict)
    profile_snapshot: dict[str, Any] = field(default_factory=dict)
    package_id: str | None = None
    package_version: str | None = None
    package_fingerprint: str | None = None
    status: str = "ACTIVE"
    activated_sequence: int = 0
    actor: str = "controller"
    previous_binding: dict[str, Any] | None = None
    evolution_history: list[dict[str, Any]] = field(default_factory=list)
    evolution_proposals: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not PROFILE_ID_RE.fullmatch(self.profile_id):
            raise ValueError("profile binding contains invalid profile_id")
        _require_semver(self.profile_version, "profile_version")
        if self.aasm_contract != PROFILE_CONTRACT:
            raise ValueError("profile binding targets an unsupported AASM contract")
        if self.status not in {"ACTIVE", "INACTIVE", "MIGRATING", "SUPERSEDED"}:
            raise ValueError(f"invalid profile binding status: {self.status}")
        if self.activated_sequence < 0:
            raise ValueError("activated_sequence must be non-negative")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProfileBinding":
        return cls(**deepcopy(data))


@dataclass
class ProfileEvolutionProposal:
    proposal_id: str
    profile_id: str
    from_version: str
    to_version: str
    reason: str
    changes: list[dict[str, Any]]
    evidence_ids: list[str] = field(default_factory=list)
    migration_id: str | None = None
    target_profile_fingerprint: str | None = None
    actor: str = "system"
    status: str = "PROPOSED"
    created_sequence: int = 0
    decision_record_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.proposal_id or not self.reason.strip():
            raise ValueError("profile evolution proposal requires proposal_id and reason")
        if not PROFILE_ID_RE.fullmatch(self.profile_id):
            raise ValueError("profile evolution proposal has invalid profile_id")
        _require_semver(self.from_version, "from_version")
        _require_semver(self.to_version, "to_version")
        if self.from_version == self.to_version:
            raise ValueError("profile evolution proposal must target a new version")
        if not self.changes:
            raise ValueError("profile evolution proposal must describe at least one change")
        if self.status not in PROPOSAL_STATUSES:
            raise ValueError(f"invalid profile evolution proposal status: {self.status}")
        self.evidence_ids = _unique(self.evidence_ids)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProfileEvolutionProposal":
        return cls(**deepcopy(data))


class ProfileRegistry:
    """Versioned registry for built-in and installed AASM profiles.

    Discovery only loads already-installed Python entry points. It never installs
    packages, downloads code, or grants execution authority.
    """

    def __init__(self, *, include_builtins: bool = True):
        self._profiles: dict[tuple[str, str], AASMProfile] = {}
        self._sources: dict[tuple[str, str], str] = {}
        if include_builtins:
            self.register(bare_profile(), source="builtin")
            self.register(evolve_profile(), source="builtin")

    def register(
        self,
        profile: AASMProfile | dict[str, Any],
        *,
        source: str = "runtime",
        replace: bool = False,
    ) -> AASMProfile:
        item = profile if isinstance(profile, AASMProfile) else AASMProfile.from_dict(profile)
        key = (item.profile_id, item.profile_version)
        if key in self._profiles and not replace:
            existing = self._profiles[key]
            if existing.fingerprint != item.fingerprint:
                raise ValueError(
                    f"profile {item.profile_id}@{item.profile_version} already exists with a different fingerprint"
                )
            return existing
        self._profiles[key] = item
        self._sources[key] = source
        return item

    def register_many(
        self,
        values: Iterable[AASMProfile | dict[str, Any]],
        *,
        source: str,
    ) -> list[AASMProfile]:
        return [self.register(value, source=source) for value in values]

    def get(self, profile_id: str, version: str | None = None) -> AASMProfile:
        matches = [
            profile for (candidate_id, _), profile in self._profiles.items()
            if candidate_id == profile_id
        ]
        if not matches:
            raise KeyError(profile_id)
        if version is not None:
            key = (profile_id, version)
            if key not in self._profiles:
                raise KeyError(f"{profile_id}@{version}")
            return self._profiles[key]
        return sorted(matches, key=lambda item: _semver_key(item.profile_version))[-1]

    def resolve(self, value: str | Path | AASMProfile | dict[str, Any]) -> AASMProfile:
        if isinstance(value, AASMProfile):
            return value
        if isinstance(value, dict):
            return AASMProfile.from_dict(value)
        path = Path(value)
        if path.exists():
            return AASMProfile.load(path)
        text = str(value)
        if "@" in text:
            profile_id, version = text.rsplit("@", 1)
            return self.get(profile_id, version)
        return self.get(text)

    def list_profiles(self) -> list[dict[str, Any]]:
        rows = []
        for key in sorted(self._profiles):
            profile = self._profiles[key]
            rows.append(
                {
                    "profile_id": profile.profile_id,
                    "profile_version": profile.profile_version,
                    "aasm_contract": profile.aasm_contract,
                    "description": profile.description,
                    "machine_definition": profile.machine_definition,
                    "source": self._sources[key],
                    "fingerprint": profile.fingerprint,
                }
            )
        return rows

    def discover(self, group: str = PROFILE_ENTRY_POINT_GROUP) -> list[AASMProfile]:
        discovered: list[AASMProfile] = []
        entry_points = importlib_metadata.entry_points()
        selected = entry_points.select(group=group) if hasattr(entry_points, "select") else entry_points.get(group, [])
        for entry_point in sorted(selected, key=lambda item: (item.name, item.value)):
            loaded = entry_point.load()
            value = loaded() if callable(loaded) else loaded
            if isinstance(value, (AASMProfile, dict)):
                values = [value]
            else:
                values = list(value)
            discovered.extend(
                self.register_many(values, source=f"entry-point:{entry_point.name}")
            )
        return discovered


def bare_profile() -> AASMProfile:
    return AASMProfile(
        profile_id="aasm.bare",
        profile_version="1.0.0",
        description="Minimal domain-neutral AASM profile with no required adapters or domain vocabulary.",
        machine_definition="aasm.default",
        decision_namespaces=["*"],
        obligation_kinds=["work"],
        evidence_kinds=["claim", "observation", "contradiction", "assumption"],
        artifact_kinds=["digital", "physical", "record", "reference", "other"],
        capabilities=["domain-neutral", "manual-binding"],
        evolution_policy=ProfileEvolutionPolicy(mode="MANUAL"),
    )


def evolve_profile() -> AASMProfile:
    return AASMProfile(
        profile_id="aasm.evolve",
        profile_version="1.0.0",
        description=(
            "Domain-neutral Evolve profile for goals that require iterative modeling, conditional work, "
            "evidence, conflict learning, repair, investigation, and controlled adaptation."
        ),
        machine_definition="aasm.evolve",
        decision_namespaces=["*"],
        obligation_kinds=["commit", "investigation", "review", "verification", "work"],
        evidence_kinds=[
            "claim",
            "formal_proof",
            "human_attestation",
            "measurement",
            "observation",
            "test",
        ],
        artifact_kinds=["digital", "physical", "record", "reference", "other"],
        policies={
            "validation_classifications": [
                "PASS",
                "LOCAL_DEFECT",
                "INFORMATION_GAP",
                "ASSUMPTION_CONFLICT",
                "EVIDENCE_CONFLICT",
                "POLICY_CONFLICT",
                "FATAL",
            ],
            "hard_constraint_certification": ["PROVEN", "VALIDATED"],
        },
        capabilities=[
            "conditional-obligations",
            "conflict-learning",
            "domain-neutral",
            "fairness",
            "knowledge-preserving-restart",
        ],
        evolution_policy=ProfileEvolutionPolicy(
            mode="PROPOSAL_ONLY",
            allow_runtime_proposals=True,
            require_explicit_activation=True,
            require_conformance=True,
            require_migration_for_breaking=True,
            minimum_evidence_count=1,
        ),
    )
