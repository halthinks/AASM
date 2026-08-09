from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from typing import Any

from .domain_adapters import determinism_probe, validate_adapter_object
from .profile_packages import (
    ADAPTER_ROLES,
    AASMPackageManifest,
    AASMProfile,
    PROFILE_CONTRACT,
    ProfileRegistry,
    canonical_json,
)
from .semantic_result import SemanticResultEnvelope, validate_semantic_result


@dataclass
class ConformanceIssue:
    code: str
    severity: str
    message: str
    subject: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.severity not in {"ERROR", "WARNING", "INFO"}:
            raise ValueError(f"invalid conformance severity: {self.severity}")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ConformanceReport:
    profile_id: str
    profile_version: str
    valid: bool
    profile_fingerprint: str
    issues: list[ConformanceIssue] = field(default_factory=list)
    checks: dict[str, bool] = field(default_factory=dict)
    adapter_roles: list[str] = field(default_factory=list)
    package_id: str | None = None
    package_version: str | None = None

    def to_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out["issues"] = [issue.to_dict() for issue in self.issues]
        return out


class ProfileConformanceKit:
    """Domain-neutral conformance checks for profile packages and adapters.

    Static conformance never imports adapter code. Installed adapter execution
    and determinism probes are explicit opt-in operations supplied by the
    caller, which keeps package discovery separate from execution authority.
    """

    def __init__(self, *, supported_contract: str = PROFILE_CONTRACT):
        self.supported_contract = supported_contract

    @staticmethod
    def _issue(
        issues: list[ConformanceIssue],
        code: str,
        severity: str,
        message: str,
        subject: str = "",
        **metadata: Any,
    ) -> None:
        issues.append(ConformanceIssue(code, severity, message, subject, metadata))

    def run(
        self,
        profile: AASMProfile | dict[str, Any],
        *,
        package: AASMPackageManifest | dict[str, Any] | None = None,
        adapter_objects: dict[str, Any] | None = None,
        determinism_fixtures: dict[str, tuple[Any, ...]] | None = None,
        registry: ProfileRegistry | None = None,
    ) -> ConformanceReport:
        issues: list[ConformanceIssue] = []
        checks: dict[str, bool] = {}
        try:
            item = profile if isinstance(profile, AASMProfile) else AASMProfile.from_dict(profile)
            checks["profile_structure"] = True
        except Exception as exc:
            placeholder = profile if isinstance(profile, dict) else {}
            return ConformanceReport(
                profile_id=str(placeholder.get("profile_id", "invalid")),
                profile_version=str(placeholder.get("profile_version", "0.0.0")),
                valid=False,
                profile_fingerprint="",
                issues=[ConformanceIssue("PROFILE_INVALID", "ERROR", str(exc))],
                checks={"profile_structure": False},
            )

        checks["contract"] = item.aasm_contract == self.supported_contract
        if not checks["contract"]:
            self._issue(
                issues,
                "CONTRACT_MISMATCH",
                "ERROR",
                f"profile contract {item.aasm_contract} is not supported by {self.supported_contract}",
                item.profile_id,
            )

        checks["machine_definition"] = bool(item.machine_definition.strip())
        if not checks["machine_definition"]:
            self._issue(
                issues,
                "MACHINE_DEFINITION_MISSING",
                "ERROR",
                "profile must identify a machine definition",
                item.profile_id,
            )

        checks["adapter_roles"] = not (set(item.adapters) - ADAPTER_ROLES)
        for role, binding in sorted(item.adapters.items()):
            if role != binding.role:
                self._issue(
                    issues,
                    "ADAPTER_ROLE_MISMATCH",
                    "ERROR",
                    f"adapter map role {role} differs from binding role {binding.role}",
                    role,
                )
            if binding.required and not binding.target:
                self._issue(
                    issues,
                    "REQUIRED_ADAPTER_TARGET_MISSING",
                    "ERROR",
                    "required adapter does not have an import target",
                    role,
                )

        package_item: AASMPackageManifest | None = None
        if package is not None:
            try:
                package_item = (
                    package
                    if isinstance(package, AASMPackageManifest)
                    else AASMPackageManifest.from_dict(package)
                )
                checks["package_structure"] = True
                if item.profile_id not in package_item.profiles:
                    self._issue(
                        issues,
                        "PROFILE_NOT_DECLARED_BY_PACKAGE",
                        "ERROR",
                        f"package {package_item.package_id} does not list profile {item.profile_id}",
                        item.profile_id,
                    )
                if package_item.aasm_contract != item.aasm_contract:
                    self._issue(
                        issues,
                        "PACKAGE_PROFILE_CONTRACT_MISMATCH",
                        "ERROR",
                        "package and profile target different AASM contracts",
                        package_item.package_id,
                    )
            except Exception as exc:
                checks["package_structure"] = False
                self._issue(issues, "PACKAGE_INVALID", "ERROR", str(exc))

        if registry is not None:
            try:
                existing = registry.get(item.profile_id, item.profile_version)
            except KeyError:
                checks["registry_identity"] = True
            else:
                checks["registry_identity"] = existing.fingerprint == item.fingerprint
                if not checks["registry_identity"]:
                    self._issue(
                        issues,
                        "REGISTRY_FINGERPRINT_CONFLICT",
                        "ERROR",
                        "same profile ID and version already has a different fingerprint",
                        item.profile_id,
                    )

        adapter_objects = adapter_objects or {}
        determinism_fixtures = determinism_fixtures or {}
        for role, adapter in sorted(adapter_objects.items()):
            errors = validate_adapter_object(role, adapter)
            checks[f"adapter:{role}"] = not errors
            for error in errors:
                self._issue(issues, "ADAPTER_PROTOCOL_INVALID", "ERROR", error, role)
            if not errors and role in determinism_fixtures:
                deterministic, detail = determinism_probe(
                    adapter,
                    role,
                    determinism_fixtures[role],
                )
                checks[f"determinism:{role}"] = deterministic
                if not deterministic:
                    self._issue(
                        issues,
                        "ADAPTER_NONDETERMINISTIC",
                        "ERROR",
                        detail or "adapter failed determinism probe",
                        role,
                    )

        # Verify that profile serialization is stable. This catches profiles
        # containing object identity, unordered custom types, or mutable output.
        first = canonical_json(item.to_dict())
        second = canonical_json(AASMProfile.from_dict(item.to_dict()).to_dict())
        checks["profile_roundtrip"] = first == second
        if not checks["profile_roundtrip"]:
            self._issue(
                issues,
                "PROFILE_ROUNDTRIP_UNSTABLE",
                "ERROR",
                "profile changes during serialization round-trip",
                item.profile_id,
            )

        valid = not any(issue.severity == "ERROR" for issue in issues)
        return ConformanceReport(
            profile_id=item.profile_id,
            profile_version=item.profile_version,
            valid=valid,
            profile_fingerprint=item.fingerprint,
            issues=issues,
            checks=checks,
            adapter_roles=sorted(item.adapters),
            package_id=None if package_item is None else package_item.package_id,
            package_version=None if package_item is None else package_item.package_version,
        )

    def semantic_roundtrip(
        self,
        envelope: SemanticResultEnvelope | dict[str, Any],
    ) -> tuple[bool, str | None]:
        try:
            item = validate_semantic_result(envelope)
            restored = SemanticResultEnvelope.from_dict(item.to_dict())
        except Exception as exc:
            return False, str(exc)
        if canonical_json(item.to_dict()) != canonical_json(restored.to_dict()):
            return False, "semantic result changes during serialization round-trip"
        return True, None


def assert_profile_conformant(
    profile: AASMProfile | dict[str, Any],
    *,
    package: AASMPackageManifest | dict[str, Any] | None = None,
) -> ConformanceReport:
    report = ProfileConformanceKit().run(profile, package=package)
    if not report.valid:
        raise ValueError(
            "; ".join(
                f"{issue.code}: {issue.message}"
                for issue in report.issues
                if issue.severity == "ERROR"
            )
        )
    return report
