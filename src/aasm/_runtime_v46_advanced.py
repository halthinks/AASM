from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence
import json

from .advanced_optimization import (
    ADVANCED_CAPABILITIES,
    ADVANCED_OPTIMIZATION_CONTRACT_ID,
    ADVANCED_PROVIDERS,
    AdvancedSolverRequest,
    AdvancedSolverResult,
    advanced_optimization_blueprint,
    advanced_optimization_contract,
    advanced_problem_from_dict,
    advanced_result_satisfies_request,
    default_advanced_capability_contracts,
    default_advanced_providers,
    solve_advanced_request,
    validate_advanced_result,
)
from .calculus import ObligationRecord
from .evidence import EvidenceRecord
from .resources import ResourceRecord, TaskDemand
from .reuse_model import ReuseRequest
from .semantic_result import canonical_semantic_json, semantic_fingerprint
from .typed_protocol import CapabilityContract, CapabilityProvider
from .workers import LeaseStatus, WorkerRecord


def _rows(snapshot, kind: str):
    evidence = snapshot.evidence if isinstance(snapshot.evidence, dict) else {}
    return [row for row in evidence.get("records", []) if row.get("kind") == kind and row.get("status", "active") == "active"]


def _doc(row):
    return json.loads(str(row.get("statement") or "{}"))


class AdvancedOptimizationRuntimeMixin:
    """v0.46 advanced search controls over the existing AASM capability/resource/worker/lease path."""

    def advanced_optimization_contract_report(self):
        return advanced_optimization_contract()

    def advanced_optimization_blueprint(self):
        return advanced_optimization_blueprint()

    def install_default_advanced_optimization_capabilities(self, *, authority_id: str, authority_class: str):
        return {
            "contract": advanced_optimization_contract(),
            "installed": [self.register_capability_contract(row, authority_id=authority_id, authority_class=authority_class, reason="v0.46 advanced solver capability admitted") for row in default_advanced_capability_contracts()],
        }

    def register_advanced_optimization_provider_runtime(
        self,
        provider: CapabilityProvider | Mapping[str, Any],
        *,
        authority_id: str,
        authority_class: str,
        worker_id: str | None = None,
        capacity: float = 1.0,
        reliability: float = 1.0,
    ):
        if authority_class not in {"POLICY", "CONTROLLER"}:
            raise PermissionError("advanced solver provider admission requires POLICY or CONTROLLER authority")
        provider = provider if isinstance(provider, CapabilityProvider) else CapabilityProvider.from_dict(provider)
        capability_row = self.capability_report(provider.capability_id)["capability"]["contract"]
        capability = CapabilityContract.from_dict(capability_row)
        if capability.capability_type != "OPERATOR" or provider.capability_version != capability.version:
            raise ValueError("advanced solver provider requires matching OPERATOR capability")
        kind = str(capability.metadata.get("advanced_kind") or "")
        if ADVANCED_CAPABILITIES.get(kind) != provider.capability_id or ADVANCED_PROVIDERS.get(kind) != provider.provider_id:
            raise ValueError("advanced solver provider does not match canonical advanced kind")
        tokens = {provider.capability_token, provider.provider_token}
        resource = next((row for row in self.list_resources() if row.get("resource_id") == provider.resource_id), None)
        if resource is None:
            resource = self.register_resource(
                ResourceRecord(provider.resource_id, "optimization-solver", sorted(tokens), capacity=capacity, reliability=reliability, metadata={"provider_id": provider.provider_id, "implementation": provider.implementation, "advanced_kind": kind}),
                reason="advanced optimization resource admitted",
            )
        elif resource.get("kind") != "optimization-solver" or not tokens.issubset(set(resource.get("capabilities", []))):
            raise ValueError("existing advanced solver resource is incompatible")
        worker_id = worker_id or f"worker-{provider.provider_id}"
        worker = next((row for row in self.list_workers() if row.get("worker_id") == worker_id), None)
        if worker is None:
            worker = self.register_worker(WorkerRecord(worker_id, provider.resource_id, metadata={"advanced_provider_id": provider.provider_id, "advanced_kind": kind}), reason="advanced optimization worker admitted")
        elif worker.get("resource_id") != provider.resource_id:
            raise ValueError("existing advanced solver worker bound to another resource")
        admitted = self.register_capability_provider(provider, authority_id=authority_id, authority_class=authority_class, reason="advanced optimization provider admitted")
        return {"contract": advanced_optimization_contract(), "resource": resource, "worker": worker, "provider": admitted}

    def install_default_advanced_optimization_providers(self, *, authority_id: str, authority_class: str):
        return {"contract": advanced_optimization_contract(), "installed": [self.register_advanced_optimization_provider_runtime(row, authority_id=authority_id, authority_class=authority_class) for row in default_advanced_providers()]}

    def advanced_problem_report(self, problem_fingerprint: str | None = None):
        problems = {}
        for row in _rows(self.snapshot, "advanced_optimization_problem"):
            problem = advanced_problem_from_dict(_doc(row))
            problems[problem.fingerprint] = {"problem": problem.to_dict(), "evidence_id": row["evidence_id"]}
        if problem_fingerprint is not None:
            if problem_fingerprint not in problems: raise KeyError(problem_fingerprint)
            return {"contract": advanced_optimization_contract(), **deepcopy(problems[problem_fingerprint])}
        return {"contract": advanced_optimization_contract(), "problems": problems}

    def admit_advanced_problem(self, problem, *, reason: str = "advanced optimization problem admitted"):
        if isinstance(problem, Mapping): problem = advanced_problem_from_dict(problem)
        existing = self.advanced_problem_report()["problems"].get(problem.fingerprint)
        if existing: return {"contract": advanced_optimization_contract(), **existing, "already_recorded": True}
        derived_from = []
        base_model = getattr(problem, "model", None)
        if base_model is not None:
            base = self.optimization_model_report(base_model.model_id)
            if base["model"]["fingerprint"] != base_model.fingerprint:
                raise ValueError("advanced problem base model fingerprint does not match admitted optimization model")
            derived_from.append(base["evidence_id"])
        stored = self.add_evidence(EvidenceRecord("advanced_optimization_problem", canonical_semantic_json(problem.to_dict()), source=ADVANCED_OPTIMIZATION_CONTRACT_ID, derived_from=derived_from, metadata={"advanced_record_type": "PROBLEM", "problem_fingerprint": problem.fingerprint, "advanced_kind": problem.to_dict()["kind"]}), reason=reason)
        return {"contract": advanced_optimization_contract(), "problem": problem.to_dict(), "evidence_id": stored.evidence_id, "already_recorded": False}

    def advanced_request_report(self, request_id: str | None = None):
        requests = {}
        for row in _rows(self.snapshot, "advanced_optimization_request"):
            request = AdvancedSolverRequest.from_dict(_doc(row)); requests[request.request_id] = {"request": request.to_dict(), "evidence_id": row["evidence_id"]}
        if request_id is not None:
            if request_id not in requests: raise KeyError(request_id)
            return {"contract": advanced_optimization_contract(), **deepcopy(requests[request_id])}
        return {"contract": advanced_optimization_contract(), "requests": requests}

    def advanced_result_report(self, request_id: str | None = None):
        results = {}
        for row in _rows(self.snapshot, "advanced_optimization_result"):
            result = AdvancedSolverResult.from_dict(_doc(row)); results.setdefault(result.request_id, []).append({"result": result.to_dict(), "evidence_id": row["evidence_id"]})
        for rows in results.values(): rows.sort(key=lambda item: item["result"]["result_id"])
        if request_id is not None: return {"contract": advanced_optimization_contract(), "request_id": request_id, "results": deepcopy(results.get(request_id, []))}
        return {"contract": advanced_optimization_contract(), "results": results}

    def request_advanced_optimization(
        self,
        problem,
        *,
        requester_id: str,
        timeout_ms: int = 30_000,
        environment_fingerprint: str = "",
        dependency_fingerprints: Sequence[str] = (),
        priority: int = 0,
    ):
        if isinstance(problem, Mapping): problem = advanced_problem_from_dict(problem)
        problem_row = self.admit_advanced_problem(problem)
        kind = problem.to_dict()["kind"]; capability_id = ADVANCED_CAPABILITIES[kind]; provider_id = ADVANCED_PROVIDERS[kind]
        capability = CapabilityContract.from_dict(self.capability_report(capability_id)["capability"]["contract"])
        provider_row = self.capability_report()["providers"].get(provider_id)
        if provider_row is None: raise KeyError(f"advanced provider is not admitted: {provider_id}")
        provider = CapabilityProvider.from_dict(provider_row["provider"])
        if provider.capability_id != capability_id: raise ValueError("advanced provider capability mismatch")
        obligation_id = "advanced-obligation-" + semantic_fingerprint({"problem": problem.fingerprint, "kind": kind, "provider": provider_id, "environment": environment_fingerprint, "dependencies": sorted(set(map(str, dependency_fingerprints)))})[:20]
        request = AdvancedSolverRequest(problem, capability_id, capability.version, obligation_id, provider_id, timeout_ms=timeout_ms, environment_fingerprint=environment_fingerprint, dependency_fingerprints=tuple(dependency_fingerprints), metadata={"requester_id": requester_id})
        if obligation_id not in self.calculus_report()["obligations"]:
            self.register_obligation(ObligationRecord(obligation_id=obligation_id, statement=f"solve advanced optimization problem {problem.fingerprint}", status="AVAILABLE", required_evidence_types=["advanced_optimization_result"], scope={"scope_id": "root"}), reason="advanced optimization obligation registered")
        existing = self.advanced_request_report()["requests"].get(request.request_id)
        if existing is None:
            stored = self.add_evidence(EvidenceRecord("advanced_optimization_request", canonical_semantic_json(request.to_dict()), source=ADVANCED_OPTIMIZATION_CONTRACT_ID, derived_from=[problem_row["evidence_id"]], metadata={"advanced_record_type": "REQUEST", "request_id": request.request_id, "request_fingerprint": request.fingerprint, "advanced_kind": kind, "required_provider": provider_id, "obligation_id": obligation_id}), reason="advanced optimization requested")
            evidence_id = stored.evidence_id
        else:
            prior = AdvancedSolverRequest.from_dict(existing["request"])
            if prior.fingerprint != request.fingerprint: raise ValueError(f"advanced request ID collision: {request.request_id}")
            evidence_id = existing["evidence_id"]
        task_id = f"{request.request_id}:{provider_id}"
        resources = deepcopy(self.snapshot.resources); queue = resources.setdefault("tasks", [])
        task = TaskDemand(task_id, [request.capability_token, provider.provider_token], demand=1.0, priority=priority, allowed_kinds=["optimization-solver"], metadata={"advanced_request_id": request.request_id, "advanced_kind": kind, "required_provider": provider_id, "obligation_id": obligation_id})
        if not any(row.get("task_id") == task_id for row in queue):
            queue.append(deepcopy(task.__dict__)); self.patch_snapshot({"resources": resources}, "advanced optimization task queued")
        return {"contract": advanced_optimization_contract(), "request": request.to_dict(), "request_evidence_id": evidence_id, "task": deepcopy(task.__dict__)}

    def _advanced_lease(self, lease_id: str, request: AdvancedSolverRequest):
        lease = next((deepcopy(row) for row in self.list_leases() if row.get("lease_id") == lease_id), None)
        if lease is None: raise KeyError(lease_id)
        if lease.get("task_id") != f"{request.request_id}:{request.required_provider}": raise ValueError("advanced result lease does not belong to request/provider")
        if lease.get("status") == "COMPLETED": return lease
        if lease.get("status") != "ACTIVE": raise ValueError(f"advanced result lease is not ACTIVE: {lease.get('status')}")
        from .model import now
        if float(lease.get("expires_at", 0)) <= now(): raise ValueError("advanced result lease expired before result commit")
        newer = [row for row in self.list_leases() if row.get("task_id") == lease.get("task_id") and int(row.get("attempt", 0)) > int(lease.get("attempt", 0)) and row.get("status") == "ACTIVE"]
        if newer: raise ValueError("advanced result lease was superseded by a newer attempt")
        return lease

    def commit_advanced_optimization_result(self, result: AdvancedSolverResult | Mapping[str, Any], *, lease_id: str):
        result = result if isinstance(result, AdvancedSolverResult) else AdvancedSolverResult.from_dict(result)
        request_row = self.advanced_request_report(result.request_id); request = AdvancedSolverRequest.from_dict(request_row["request"])
        validate_advanced_result(request, result); lease = self._advanced_lease(lease_id, request)
        provider_row = self.capability_report()["providers"].get(result.solver.provider_id)
        if provider_row is None: raise KeyError(f"unadmitted advanced provider: {result.solver.provider_id}")
        provider = CapabilityProvider.from_dict(provider_row["provider"])
        if provider.implementation != result.solver.implementation: raise ValueError("advanced result implementation does not match admitted provider")
        existing = self.advanced_result_report(request.request_id)["results"]
        for row in existing:
            prior = AdvancedSolverResult.from_dict(row["result"])
            if prior.result_id == result.result_id:
                if prior.fingerprint != result.fingerprint: raise ValueError(f"advanced result ID collision: {result.result_id}")
                if lease.get("status") == "ACTIVE": self._finish_lease(lease_id, LeaseStatus.COMPLETED.value, result={"advanced_result_id": result.result_id, "already_committed": True}, reason="advanced lease completed after exact replay")
                return {"contract": advanced_optimization_contract(), "result": prior.to_dict(), "result_evidence_id": row["evidence_id"], "already_committed": True}
        if lease.get("status") == "COMPLETED": raise ValueError("completed advanced optimization lease cannot commit a new result")
        stored = self.add_evidence(EvidenceRecord("advanced_optimization_result", canonical_semantic_json(result.to_dict()), source=ADVANCED_OPTIMIZATION_CONTRACT_ID, derived_from=[request_row["evidence_id"]], metadata={"advanced_record_type": "RESULT", "request_id": request.request_id, "result_id": result.result_id, "advanced_kind": request.kind, "status": result.status, "result_authority": "EVIDENCE_ONLY", "obligation_id": request.obligation_id}), reason="advanced optimization result committed")
        obligation = self.calculus_report()["obligations"][request.obligation_id]; status = obligation.get("status")
        if status == "AVAILABLE": self.enable_obligation(request.obligation_id, reason="advanced obligation enabled"); status = "ENABLED"
        if status == "ENABLED": self.set_obligation_status(request.obligation_id, "IN_PROGRESS", reason="advanced solver started"); status = "IN_PROGRESS"
        if status == "IN_PROGRESS": self.set_obligation_status(request.obligation_id, "VERIFYING", reason="advanced result validating"); status = "VERIFYING"
        satisfied = advanced_result_satisfies_request(request, result)
        if satisfied and status == "VERIFYING": self.set_obligation_status(request.obligation_id, "VERIFIED", evidence_ids=[stored.evidence_id], reason="advanced request satisfied")
        elif not satisfied and status == "VERIFYING": self.set_obligation_status(request.obligation_id, "BLOCKED", reason=f"advanced result not definitive: {result.status}")
        lease_status = LeaseStatus.FAILED.value if result.status == "ERROR" else LeaseStatus.COMPLETED.value
        self._finish_lease(lease_id, lease_status, result={"advanced_result_id": result.result_id, "status": result.status} if lease_status == LeaseStatus.COMPLETED.value else None, error="; ".join(result.diagnostics) if lease_status == LeaseStatus.FAILED.value else None, reason="advanced solver result accepted")
        return {"contract": advanced_optimization_contract(), "result": result.to_dict(), "result_evidence_id": stored.evidence_id, "obligation": deepcopy(self.calculus_report()["obligations"][request.obligation_id]), "satisfied": satisfied, "already_committed": False}

    def execute_advanced_optimization_lease(self, lease_id: str):
        lease = next((deepcopy(row) for row in self.list_leases() if row.get("lease_id") == lease_id), None)
        if lease is None: raise KeyError(lease_id)
        request_id = str((lease.get("metadata") or {}).get("advanced_request_id") or "")
        if not request_id: raise ValueError("lease is not an advanced optimization task")
        request = AdvancedSolverRequest.from_dict(self.advanced_request_report(request_id)["request"])
        result = solve_advanced_request(request)
        return self.commit_advanced_optimization_result(result, lease_id=lease_id)

    def advanced_optimization_reuse_request(self, request_id: str):
        request = AdvancedSolverRequest.from_dict(self.advanced_request_report(request_id)["request"])
        return ReuseRequest(
            kind="OPTIMIZATION_RESULT",
            semantic_payload={"contract_id": ADVANCED_OPTIMIZATION_CONTRACT_ID, "request_fingerprint": request.fingerprint, "problem_fingerprint": request.problem.fingerprint, "advanced_kind": request.kind, "required_provider": request.required_provider},
            scope_id="root",
            required_strength="SOLVER_VERDICT",
            environment_fingerprint=request.environment_fingerprint,
            dependency_fingerprints=request.dependency_fingerprints,
            effect_class="PURE",
            metadata={"advanced_request_id": request.request_id},
        )


__all__ = ["AdvancedOptimizationRuntimeMixin"]
