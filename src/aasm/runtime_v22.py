from __future__ import annotations

from copy import deepcopy
from typing import Any

from .calculus import (
    FairnessPolicy,
    audit_fairness,
    candidate_exposes_overdue,
    condition_holds,
    decision_values,
    violated_hard_constraints,
)
from .domain_adapters import (
    CandidateModel,
    CandidateValidationReport,
    DecisionRequest,
    DomainContext,
)
from .profile_conformance import ProfileConformanceKit
from .profile_packages import (
    AASMPackageManifest,
    AASMProfile,
    ProfileBinding,
    ProfileEvolutionPolicy,
    ProfileEvolutionProposal,
    ProfileMigration,
    ProfileRegistry,
)
from .runtime_v21 import AASMEngine as V21Engine
from .semantic_result import SemanticResultEnvelope, validate_semantic_result


class AASMEngine(V21Engine):
    """v0.22 runtime: domain-neutral profile packages and adapter contracts.

    A profile supplies vocabulary, policies, and adapter bindings. It does not
    receive authority to mutate the machine. Profile binding and evolution are
    explicit durable state changes on the existing event/reducer path.
    """

    def _profile_binding(self) -> dict[str, Any]:
        return deepcopy(getattr(self.snapshot, "profile_binding", {}) or {})

    def profile_report(self) -> dict[str, Any]:
        binding = self._profile_binding()
        return {
            "configured": bool(binding),
            "binding": binding,
            "semantic_result_count": len(getattr(self.snapshot, "semantic_results", []) or []),
            "latest_semantic_result": deepcopy((getattr(self.snapshot, "semantic_results", []) or [])[-1])
            if getattr(self.snapshot, "semantic_results", [])
            else None,
        }

    def _profile_policy(self, binding: dict[str, Any] | None = None) -> ProfileEvolutionPolicy:
        selected = binding if binding is not None else self._profile_binding()
        snapshot = selected.get("profile_snapshot") or {}
        return ProfileEvolutionPolicy.from_dict(snapshot.get("evolution_policy"))

    @staticmethod
    def _binding_without_recursive_history(binding: dict[str, Any]) -> dict[str, Any]:
        if not binding:
            return {}
        out = deepcopy(binding)
        out["previous_binding"] = None
        # The current binding already carries the authoritative history. Avoid
        # recursive geometric growth when one version supersedes another.
        out["evolution_history"] = []
        out["evolution_proposals"] = []
        return out

    def _validate_binding_actor(self, policy: ProfileEvolutionPolicy, actor: str) -> None:
        if not actor.strip():
            raise ValueError("profile activation actor is required")
        if policy.allowed_activation_actors and actor not in policy.allowed_activation_actors:
            raise PermissionError(
                f"actor {actor!r} is not permitted to activate this profile package"
            )

    def bind_profile(
        self,
        profile: AASMProfile | dict[str, Any],
        *,
        package: AASMPackageManifest | dict[str, Any] | None = None,
        configuration: dict[str, Any] | None = None,
        actor: str = "controller",
        migration: ProfileMigration | dict[str, Any] | None = None,
        reason: str = "domain-neutral profile bound",
    ) -> dict[str, Any]:
        item = profile if isinstance(profile, AASMProfile) else AASMProfile.from_dict(profile)
        package_item = None
        if package is not None:
            package_item = (
                package
                if isinstance(package, AASMPackageManifest)
                else AASMPackageManifest.from_dict(package)
            )
        report = ProfileConformanceKit().run(item, package=package_item)
        if not report.valid:
            raise ValueError(
                "; ".join(
                    f"{issue.code}: {issue.message}"
                    for issue in report.issues
                    if issue.severity == "ERROR"
                )
            )

        refresh = getattr(self, "_refresh_canonical_snapshot", None)
        if refresh is not None:
            refresh()
        current = self._profile_binding()
        target_policy = item.evolution_policy
        self._validate_binding_actor(target_policy, actor)
        migration_item = None
        if current:
            current_identity = (
                current.get("profile_id"),
                current.get("profile_version"),
                current.get("profile_fingerprint"),
            )
            target_identity = (item.profile_id, item.profile_version, item.fingerprint)
            if current_identity == target_identity:
                target_configuration = deepcopy(configuration or {})
                if target_configuration == current.get("configuration", {}):
                    return current
                updated = deepcopy(current)
                updated.setdefault("metadata", {}).setdefault("configuration_history", []).append({
                    "configuration": deepcopy(current.get("configuration", {})),
                    "actor": actor,
                    "sequence": self._sequence() + 1,
                })
                updated["configuration"] = target_configuration
                updated["actor"] = actor
                updated["activated_sequence"] = self._sequence() + 1
                self.patch_snapshot({"profile_binding": updated}, "profile instance configuration updated")
                return deepcopy(updated)
            migration_item = (
                migration
                if isinstance(migration, ProfileMigration)
                else ProfileMigration.from_dict(migration)
                if migration is not None
                else None
            )
            if migration_item is None:
                raise ValueError(
                    "replacing a bound profile requires an explicit versioned ProfileMigration"
                )
            if migration_item.from_version != current.get("profile_version"):
                raise ValueError("migration from_version does not match the active profile")
            if migration_item.to_version != item.profile_version:
                raise ValueError("migration to_version does not match the target profile")
            current_policy = self._profile_policy(current)
            if current_policy.mode == "FROZEN":
                raise PermissionError("the active profile package is frozen")
            self._validate_binding_actor(current_policy, actor)
            if (
                migration_item.compatibility == "BREAKING"
                and current_policy.require_migration_for_breaking
                and not migration_item.operations
            ):
                raise ValueError("breaking profile evolution requires migration operations")

        history = list(current.get("evolution_history", []) if current else [])
        if current:
            history.append(
                {
                    "from": self._binding_without_recursive_history(current),
                    "to_profile_id": item.profile_id,
                    "to_profile_version": item.profile_version,
                    "migration": None if migration_item is None else migration_item.to_dict(),
                    "actor": actor,
                    "sequence": self._sequence() + 1,
                }
            )
        binding = ProfileBinding(
            profile_id=item.profile_id,
            profile_version=item.profile_version,
            aasm_contract=item.aasm_contract,
            profile_fingerprint=item.fingerprint,
            configuration=deepcopy(configuration or {}),
            profile_snapshot=item.to_dict(),
            package_id=None if package_item is None else package_item.package_id,
            package_version=None if package_item is None else package_item.package_version,
            package_fingerprint=None if package_item is None else package_item.fingerprint,
            activated_sequence=self._sequence() + 1,
            actor=actor,
            previous_binding=self._binding_without_recursive_history(current) if current else None,
            evolution_history=history,
            evolution_proposals=list(current.get("evolution_proposals", []) if current else []),
            metadata={"conformance": report.to_dict()},
        ).to_dict()
        self.patch_snapshot({"profile_binding": binding}, reason)
        return deepcopy(binding)

    def propose_profile_evolution(
        self,
        proposal: ProfileEvolutionProposal | dict[str, Any],
        *,
        reason: str = "profile evolution proposed",
    ) -> dict[str, Any]:
        item = (
            proposal
            if isinstance(proposal, ProfileEvolutionProposal)
            else ProfileEvolutionProposal.from_dict(proposal)
        )
        refresh = getattr(self, "_refresh_canonical_snapshot", None)
        if refresh is not None:
            refresh()
        binding = self._profile_binding()
        if not binding:
            raise RuntimeError("no profile package is bound")
        policy = self._profile_policy(binding)
        if not policy.allow_runtime_proposals:
            raise PermissionError("the active profile does not permit runtime evolution proposals")
        if item.profile_id != binding.get("profile_id") or item.from_version != binding.get("profile_version"):
            raise ValueError("evolution proposal does not start from the active profile binding")
        missing = sorted(set(item.evidence_ids) - self._evidence_ids(self.snapshot))
        if missing:
            raise KeyError(f"unknown evidence IDs: {missing}")
        if len(item.evidence_ids) < policy.minimum_evidence_count:
            raise ValueError(
                f"evolution proposal requires at least {policy.minimum_evidence_count} evidence records"
            )
        proposals = list(binding.get("evolution_proposals", []))
        if any(row.get("proposal_id") == item.proposal_id for row in proposals):
            raise ValueError(f"profile evolution proposal already exists: {item.proposal_id}")
        item.created_sequence = self._sequence() + 1
        proposals.append(item.to_dict())
        binding["evolution_proposals"] = proposals
        self.patch_snapshot({"profile_binding": binding}, reason)
        return deepcopy(proposals[-1])

    def activate_profile_evolution(
        self,
        proposal_id: str,
        target_profile: AASMProfile | dict[str, Any],
        migration: ProfileMigration | dict[str, Any],
        *,
        package: AASMPackageManifest | dict[str, Any] | None = None,
        configuration: dict[str, Any] | None = None,
        actor: str = "controller",
        reason: str = "profile evolution explicitly activated",
    ) -> dict[str, Any]:
        refresh = getattr(self, "_refresh_canonical_snapshot", None)
        if refresh is not None:
            refresh()
        binding = self._profile_binding()
        if not binding:
            raise RuntimeError("no profile package is bound")
        proposals = list(binding.get("evolution_proposals", []))
        proposal = next((row for row in proposals if row.get("proposal_id") == proposal_id), None)
        if proposal is None:
            raise KeyError(proposal_id)
        if proposal.get("status") not in {"PROPOSED", "APPROVED"}:
            raise ValueError(f"proposal {proposal_id} cannot activate from {proposal.get('status')}")
        target = (
            target_profile
            if isinstance(target_profile, AASMProfile)
            else AASMProfile.from_dict(target_profile)
        )
        migration_item = (
            migration
            if isinstance(migration, ProfileMigration)
            else ProfileMigration.from_dict(migration)
        )
        if target.profile_id != proposal.get("profile_id") or target.profile_version != proposal.get("to_version"):
            raise ValueError("target profile does not match the approved evolution proposal")
        expected_fingerprint = proposal.get("target_profile_fingerprint")
        if expected_fingerprint and expected_fingerprint != target.fingerprint:
            raise ValueError("target profile fingerprint differs from the evolution proposal")
        if proposal.get("migration_id") and proposal["migration_id"] != migration_item.migration_id:
            raise ValueError("migration does not match the evolution proposal")
        for row in proposals:
            if row.get("proposal_id") == proposal_id:
                row["status"] = "APPLIED"
                row["applied_sequence"] = self._sequence() + 1
                row["applied_by"] = actor
        binding["evolution_proposals"] = proposals
        # Persist the proposal status before the explicit version migration so
        # its provenance remains visible in the new binding's history.
        self.patch_snapshot({"profile_binding": binding}, "profile evolution proposal approved for activation")
        return self.bind_profile(
            target,
            package=package,
            configuration=configuration,
            actor=actor,
            migration=migration_item,
            reason=reason,
        )

    def validate_candidate_model(
        self,
        candidate: CandidateModel | dict[str, Any],
    ) -> CandidateValidationReport:
        item = candidate if isinstance(candidate, CandidateModel) else CandidateModel.from_dict(candidate)
        state, fairness = audit_fairness(self._begin_calculus())
        decisions = state.get("decisions", {})
        errors: list[str] = []
        warnings: list[str] = []
        assignments = deepcopy(item.assignments)
        values: dict[str, Any] = {}

        binding = self._profile_binding()
        namespaces = set((binding.get("profile_snapshot") or {}).get("decision_namespaces", []))
        for subject, decision_id in sorted(assignments.items()):
            decision = decisions.get(decision_id)
            if decision is None:
                errors.append(f"unknown decision {decision_id} for subject {subject}")
                continue
            if decision.get("subject") != subject:
                errors.append(
                    f"candidate subject {subject} does not match decision {decision_id} subject {decision.get('subject')}"
                )
                continue
            if decision.get("status") in {"INVALIDATED", "REJECTED", "HISTORICAL"}:
                errors.append(f"decision {decision_id} is not selectable from status {decision.get('status')}")
                continue
            namespace = subject.split(".", 1)[0].split(":", 1)[0]
            if namespaces and "*" not in namespaces and namespace not in namespaces:
                errors.append(f"decision subject {subject} is outside profile namespaces {sorted(namespaces)}")
            values[subject] = decision.get("value")

        for subject, active_id in state.get("active_model", {}).items():
            active = decisions.get(active_id, {})
            if active.get("pinned") and assignments.get(subject, active_id) != active_id:
                errors.append(f"candidate attempts to replace pinned decision {active_id}")
            if subject not in assignments and active.get("pinned"):
                assignments[subject] = active_id
                values[subject] = active.get("value")

        for subject, decision_id in sorted(assignments.items()):
            decision = decisions.get(decision_id)
            if decision is None:
                continue
            inactive_parents = [
                parent_id
                for parent_id in decision.get("parent_ids", [])
                if parent_id not in assignments.values()
                and state.get("decisions", {}).get(parent_id, {}).get("status") != "ACTIVE"
            ]
            if inactive_parents:
                errors.append(f"decision {decision_id} has inactive parents {sorted(inactive_parents)}")

        violations = violated_hard_constraints(state, values)
        if violations:
            errors.append(f"candidate violates hard constraints {violations}")
        policy = FairnessPolicy(**deepcopy(state["fairness"]["policy"]))
        if fairness["overdue"] and policy.enforcement == "BLOCK_PLANNING":
            if not candidate_exposes_overdue(
                state,
                values,
                previous_values=decision_values(state),
            ):
                errors.append(
                    f"candidate does not expose overdue obligations {fairness['overdue']}"
                )
        for constraint_id, constraint in state.get("constraints", {}).items():
            if constraint.get("status") == "SOFT" and condition_holds(
                constraint.get("guard"), values
            ) and all(
                condition_holds({"decision": literal}, values)
                for literal in constraint.get("body", [])
            ):
                warnings.append(f"candidate matches soft learned constraint {constraint_id}")

        return CandidateValidationReport(
            candidate_id=item.candidate_id,
            valid=not errors,
            errors=errors,
            warnings=warnings,
            violated_constraint_ids=violations,
            overdue_obligation_ids=fairness["overdue"],
            normalized_assignments=assignments,
        )

    def decision_request(self) -> DecisionRequest:
        state, fairness = audit_fairness(self._begin_calculus())
        binding = self._profile_binding()
        return DecisionRequest(
            machine_id=self.snapshot.machine_id,
            profile_binding=binding,
            active_model=deepcopy(state["active_model"]),
            available_decisions=[
                deepcopy(decision)
                for decision in state["decisions"].values()
                if decision.get("status") in {"PROPOSED", "ACTIVE", "SUSPENDED"}
            ],
            hard_constraints=[
                deepcopy(row)
                for row in state["constraints"].values()
                if row.get("status") == "ACTIVE" and row.get("strength") == "HARD"
            ],
            soft_constraints=[
                deepcopy(row)
                for row in state["constraints"].values()
                if row.get("status") == "SOFT" or row.get("strength") == "SOFT"
            ],
            overdue_obligation_ids=fairness["overdue"],
            context={"problem": deepcopy(self.snapshot.problem.__dict__)},
            strategy_state=deepcopy(state.get("search_local", {})),
        )

    def domain_context(self) -> DomainContext:
        binding = self._profile_binding()
        return DomainContext(
            machine_id=self.snapshot.machine_id,
            profile_binding=binding,
            configuration=deepcopy(binding.get("configuration", {})),
            state_view={
                "machine_state": self.state_value,
                "machine_version": self.snapshot.version,
                "calculus": self.calculus_report(),
                "graph": deepcopy(self.snapshot.graph),
            },
        )

    def record_semantic_result(
        self,
        result: SemanticResultEnvelope | dict[str, Any],
        *,
        reason: str = "domain semantic result recorded",
    ) -> dict[str, Any]:
        item = validate_semantic_result(result)
        binding = self._profile_binding()
        allowed = set(
            (binding.get("profile_snapshot") or {})
            .get("policies", {})
            .get("validation_classifications", [])
        )
        if allowed and item.classification not in allowed:
            raise ValueError(
                f"semantic result classification {item.classification} is not enabled by the bound profile"
            )
        rows = deepcopy(getattr(self.snapshot, "semantic_results", []) or [])
        if any(row.get("result_id") == item.result_id for row in rows):
            raise ValueError(f"semantic result already exists: {item.result_id}")
        raw = item.to_dict()
        raw["fingerprint"] = item.fingerprint
        raw["recorded_sequence"] = self._sequence() + 1
        raw["profile_id"] = binding.get("profile_id")
        raw["profile_version"] = binding.get("profile_version")
        rows.append(raw)
        self.patch_snapshot({"semantic_results": rows}, reason)
        return deepcopy(raw)

    def semantic_results_report(
        self,
        *,
        classification: str | None = None,
        subject_id: str | None = None,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        if limit < 1 or limit > 5000:
            raise ValueError("limit must be between 1 and 5000")
        rows = deepcopy(getattr(self.snapshot, "semantic_results", []) or [])
        if classification is not None:
            rows = [row for row in rows if row.get("classification") == classification]
        if subject_id is not None:
            rows = [row for row in rows if subject_id in row.get("subject_ids", [])]
        return rows[-limit:]

    def dashboard(self):
        out = super().dashboard()
        out["profile"] = self.profile_report()
        out["semantic_results"] = {
            "count": len(getattr(self.snapshot, "semantic_results", []) or []),
            "latest": deepcopy((getattr(self.snapshot, "semantic_results", []) or [])[-1])
            if getattr(self.snapshot, "semantic_results", [])
            else None,
        }
        return out


def default_profile_registry(*, discover: bool = False) -> ProfileRegistry:
    registry = ProfileRegistry(include_builtins=True)
    if discover:
        registry.discover()
    return registry
