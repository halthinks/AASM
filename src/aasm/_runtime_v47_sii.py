from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence

from .advanced_optimization import AdvancedSolverRequest, advanced_problem_from_dict
from .sii import StructuredProposal
from .sii_governance import (
    GovernedResourceLease,
    SIIPrincipalBinding,
    SIIScoringPolicy,
    create_governed_sii,
    enforce_advanced_problem_budget,
    governed_sii_contract,
)


class SIIGovernanceRuntimeMixin:
    """v0.47 SII governance over the existing v0.46 runtime.

    This mixin never claims leases itself and never creates a parallel scheduler.
    It compiles governed SII resource policy into fields consumed by the existing
    context projection, TaskDemand priority, TaskLease, formal verification, and
    advanced native solver implementations.
    """

    def _governed_sii(self):
        return create_governed_sii(self)

    def sii_governed_contract_report(self):
        return governed_sii_contract()

    def sii_governance_report(self):
        return self._governed_sii().projection()

    def bind_sii_principal(self, binding: SIIPrincipalBinding | Mapping[str, Any], *, authority_id: str, authority_class: str):
        return self._governed_sii().bind_principal(binding, authority_id=authority_id, authority_class=authority_class)

    def admit_sii_scoring_policy(self, policy: SIIScoringPolicy | Mapping[str, Any], *, authority_id: str, authority_class: str):
        return self._governed_sii().admit_scoring_policy(policy, authority_id=authority_id, authority_class=authority_class)

    def activate_sii_scoring_policy(self, policy_id: str, *, authority_id: str, authority_class: str):
        return self._governed_sii().activate_scoring_policy(policy_id, authority_id=authority_id, authority_class=authority_class)

    def install_default_sii_scoring_policy(self, *, authority_id: str, authority_class: str):
        return self._governed_sii().install_default_policy(authority_id=authority_id, authority_class=authority_class)

    def register_sii_proposer(self, **kwargs):
        return self._governed_sii().register_proposer(**kwargs)

    def submit_sii_proposal(self, proposal: StructuredProposal | Mapping[str, Any], *, phase: str = "normal"):
        return self._governed_sii().submit(proposal, phase=phase)

    def measure_sii_outcome(self, proposal_id: str, *, measured_by_principal_id: str, **kwargs):
        return self._governed_sii().measure_proposal_outcome(proposal_id, measured_by_principal_id=measured_by_principal_id, **kwargs).to_dict()

    def sii_performance(self, proposer_id: str, *, window: int | None = None):
        return self._governed_sii().performance(proposer_id, window=window).to_dict()

    def sii_resource_lease(self, proposer_id: str, *, phase: str = "normal", formal_goal: bool = False, persist: bool = False):
        return self._governed_sii().resource_lease(proposer_id, phase=phase, formal_goal=formal_goal, persist=persist)

    def sii_context(self, proposer_id: str, *, scope_id: str, query: str = "", phase: str = "normal", formal_goal: bool = False, allowed_privacy_levels: Sequence[str] = ("AGENT", "USER", "SHARED", "PUBLIC"), memory_kinds: Sequence[str] = (), objective_node_ids: Sequence[str] = (), max_memory_items: int = 20, max_frontier_items: int = 20):
        return self._governed_sii().context_for(proposer_id, scope_id=scope_id, query=query, phase=phase, formal_goal=formal_goal, allowed_privacy_levels=allowed_privacy_levels, memory_kinds=memory_kinds, objective_node_ids=objective_node_ids, max_memory_items=max_memory_items, max_frontier_items=max_frontier_items)

    def _annotate_sii_task(self, task_id: str, lease: GovernedResourceLease, enforcement_evidence_id: str, *, discretionary: bool = True):
        resources = deepcopy(self.snapshot.resources)
        queue = resources.setdefault("tasks", [])
        found = False
        for row in queue:
            if row.get("task_id") != task_id:
                continue
            metadata = row.setdefault("metadata", {})
            metadata.update({
                "sii_contract_version": "0.3.0",
                "sii_proposer_id": lease.proposer_id,
                "sii_principal_id": lease.principal_id,
                "sii_resource_lease_id": lease.lease_id,
                "sii_policy_id": lease.policy_id,
                "sii_resource_tier": lease.resource_tier,
                "sii_enforcement_evidence_id": enforcement_evidence_id,
                "sii_discretionary": bool(discretionary),
                "authority_reward": "NEVER",
            })
            found = True
        if not found:
            raise KeyError(f"SII enforcement target task is not queued: {task_id}")
        self.patch_snapshot({"resources": resources}, "governed SII task metadata attached")

    def request_sii_advanced_optimization(
        self,
        proposer_id: str,
        problem,
        *,
        timeout_ms: int | None = None,
        environment_fingerprint: str = "",
        dependency_fingerprints: Sequence[str] = (),
        phase: str = "normal",
        formal_goal: bool = False,
    ):
        sii = self._governed_sii()
        issued = sii.resource_lease(proposer_id, phase=phase, formal_goal=formal_goal, persist=True)
        lease = GovernedResourceLease.from_dict(issued["lease"])
        if sii.outstanding_discretionary_tasks(proposer_id) >= lease.budget.max_parallel_candidates:
            raise PermissionError("SII max_parallel_candidates budget exhausted")
        governed_problem = enforce_advanced_problem_budget(problem, lease)
        base = getattr(governed_problem, "model", None)
        if base is not None:
            try:
                self.optimization_model_report(base.model_id)
            except KeyError:
                self.admit_optimization_model(base)
        kind = governed_problem.to_dict()["kind"]
        requested_timeout = int(timeout_ms or (lease.budget.convex_timeout_ms if kind == "CONVEX_ADVANCED" else lease.budget.solver_timeout_ms))
        max_timeout = lease.budget.convex_timeout_ms if kind == "CONVEX_ADVANCED" else lease.budget.solver_timeout_ms
        effective_timeout = min(requested_timeout, max_timeout)
        requested = super().request_advanced_optimization(
            governed_problem,
            requester_id=proposer_id,
            timeout_ms=effective_timeout,
            environment_fingerprint=environment_fingerprint,
            dependency_fingerprints=dependency_fingerprints,
            priority=lease.budget.scheduler_priority,
        )
        request = AdvancedSolverRequest.from_dict(requested["request"])
        enforcement = sii.record_enforcement(
            lease,
            target_kind="ADVANCED_OPTIMIZATION_REQUEST",
            target_id=request.request_id,
            request_evidence_ids=(requested["request_evidence_id"],),
            detail={
                "advanced_kind": kind,
                "timeout_ms": effective_timeout,
                "scheduler_priority": lease.budget.scheduler_priority,
                "native_problem_budget": governed_problem.to_dict(),
            },
        )
        self._annotate_sii_task(requested["task"]["task_id"], lease, enforcement["evidence_id"], discretionary=True)
        return {
            **requested,
            "contract": governed_sii_contract(),
            "resource_lease": lease.to_dict(),
            "resource_lease_evidence_id": issued["evidence_id"],
            "enforcement_evidence_id": enforcement["evidence_id"],
            "effective_problem": governed_problem.to_dict(),
        }

    def request_sii_formal_verification(
        self,
        proposer_id: str,
        formal_statement_id: str,
        capability_id: str,
        *,
        linked_artifact_id: str | None = None,
        capability_version: str | None = None,
        timeout_ms: int | None = None,
        required_providers: Sequence[str] = (),
        policy=None,
        phase: str = "normal",
        reason: str = "SII discretionary formal verification requested",
    ):
        """Request *discretionary* formal work within an SII lease.

        Policy-required verification must continue to use the ordinary formal
        verification path.  SII is intentionally unable to cap, remove, or
        replace verification that AASM already requires for epistemic admission.
        """
        sii = self._governed_sii(); issued = sii.resource_lease(proposer_id, phase=phase, formal_goal=True, persist=True); lease = GovernedResourceLease.from_dict(issued["lease"])
        providers = tuple(sorted(set(map(str, required_providers))))
        if len(providers) > lease.budget.portfolio_width:
            raise PermissionError("discretionary SII formal provider width exceeds resource lease; policy-required verification must use the ordinary formal path")
        requested_timeout = int(timeout_ms or lease.budget.formal_timeout_ms)
        effective_timeout = min(requested_timeout, lease.budget.formal_timeout_ms)
        requested = super().request_formal_verification(
            formal_statement_id,
            capability_id,
            requester_id=proposer_id,
            linked_artifact_id=linked_artifact_id,
            capability_version=capability_version,
            timeout_ms=effective_timeout,
            required_providers=providers,
            policy=policy,
            priority=lease.budget.scheduler_priority,
            reason=reason,
        )
        request_id = requested["request"]["request_id"]
        enforcement = sii.record_enforcement(
            lease,
            target_kind="DISCRETIONARY_FORMAL_REQUEST",
            target_id=request_id,
            request_evidence_ids=(requested["request_evidence_id"],),
            detail={"timeout_ms": effective_timeout, "provider_width": len(providers) or 1, "scheduler_priority": lease.budget.scheduler_priority},
        )
        for task in requested["tasks"]:
            self._annotate_sii_task(task["task_id"], lease, enforcement["evidence_id"], discretionary=True)
        return {**requested, "contract": governed_sii_contract(), "resource_lease": lease.to_dict(), "resource_lease_evidence_id": issued["evidence_id"], "enforcement_evidence_id": enforcement["evidence_id"], "mandatory_verification_note": "Required verification remains outside SII caps and is never reduced."}


__all__ = ["SIIGovernanceRuntimeMixin"]
