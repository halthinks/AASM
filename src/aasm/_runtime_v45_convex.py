from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence
import json

from .calculus import ObligationRecord
from .convex_optimization import (
    CONVEX_CAPABILITY_ID,
    CONVEX_OPTIMIZATION_CONTRACT_ID,
    ConvexOptimizationModel,
    ConvexOptimizationRequest,
    ConvexOptimizationResult,
    convex_optimization_contract,
    default_convex_capability_contract,
    default_cvxpy_provider,
    solve_convex_request,
    validate_convex_result,
)
from .evidence import EvidenceRecord
from .pulp_adapter import pulp_import_report, pulp_problem_to_optimization_model
from .resources import ResourceRecord, TaskDemand
from .reuse_model import ReuseRequest
from .semantic_result import canonical_semantic_json, semantic_fingerprint
from .typed_protocol import CapabilityProvider
from .workers import LeaseStatus, WorkerRecord


def _rows(snapshot, kind: str):
    evidence = snapshot.evidence if isinstance(snapshot.evidence, dict) else {}
    return [row for row in evidence.get("records", []) if row.get("kind") == kind and row.get("status", "active") == "active"]


def _doc(row):
    return json.loads(str(row.get("statement") or "{}"))


class ConvexOptimizationRuntimeMixin:
    """v0.45 governed CVXPY capability over the existing AASM resource/worker/lease boundary."""

    def convex_optimization_contract_report(self):
        return convex_optimization_contract()

    def install_default_convex_capability_contract(self, *, authority_id: str, authority_class: str):
        return self.register_capability_contract(
            default_convex_capability_contract(),
            authority_id=authority_id,
            authority_class=authority_class,
            reason="v0.45 convex optimization capability admitted",
        )

    def register_default_cvxpy_provider_runtime(
        self,
        *,
        authority_id: str,
        authority_class: str,
        worker_id: str = "worker-cvxpy",
        capacity: float = 1.0,
        reliability: float = 1.0,
    ):
        if authority_class not in {"POLICY", "CONTROLLER"}:
            raise PermissionError("CVXPY provider admission requires POLICY or CONTROLLER authority")
        provider = default_cvxpy_provider()
        capability = self.capability_report(CONVEX_CAPABILITY_ID)["capability"]["contract"]
        if capability.get("capability_type") != "OPERATOR":
            raise ValueError("CVXPY requires an OPERATOR capability")
        required_tokens = {provider.capability_token, provider.provider_token}
        resource = next((row for row in self.list_resources() if row.get("resource_id") == provider.resource_id), None)
        if resource is None:
            resource = self.register_resource(
                ResourceRecord(
                    provider.resource_id,
                    "optimization-solver",
                    sorted(required_tokens),
                    capacity=capacity,
                    reliability=reliability,
                    metadata={"provider_id": "cvxpy", "implementation": "cvxpy", "solver_family": "CONVEX"},
                ),
                reason="CVXPY optimization resource admitted",
            )
        elif resource.get("kind") != "optimization-solver" or not required_tokens.issubset(set(resource.get("capabilities", []))):
            raise ValueError("existing CVXPY resource is incompatible")
        worker = next((row for row in self.list_workers() if row.get("worker_id") == worker_id), None)
        if worker is None:
            worker = self.register_worker(
                WorkerRecord(worker_id, provider.resource_id, metadata={"optimization_provider_id": "cvxpy", "solver_family": "CONVEX"}),
                reason="CVXPY worker admitted",
            )
        elif worker.get("resource_id") != provider.resource_id:
            raise ValueError("existing CVXPY worker bound to different resource")
        admitted = self.register_capability_provider(provider, authority_id=authority_id, authority_class=authority_class, reason="CVXPY provider admitted")
        return {"contract": convex_optimization_contract(), "resource": resource, "worker": worker, "provider": admitted}

    def convex_model_report(self, model_id: str | None = None):
        models = {}
        for row in _rows(self.snapshot, "convex_optimization_model"):
            model = ConvexOptimizationModel.from_dict(_doc(row))
            models[model.model_id] = {"model": model.to_dict(), "evidence_id": row["evidence_id"]}
        if model_id is not None:
            if model_id not in models:
                raise KeyError(model_id)
            return {"contract": convex_optimization_contract(), **deepcopy(models[model_id])}
        return {"contract": convex_optimization_contract(), "models": models}

    def admit_convex_model(self, model: ConvexOptimizationModel | Mapping[str, Any], *, reason="convex model admitted"):
        model = model if isinstance(model, ConvexOptimizationModel) else ConvexOptimizationModel.from_dict(model)
        existing = self.convex_model_report()["models"].get(model.model_id)
        if existing:
            prior = ConvexOptimizationModel.from_dict(existing["model"])
            if prior.fingerprint != model.fingerprint:
                raise ValueError(f"convex model ID collision: {model.model_id}")
            return {"contract": convex_optimization_contract(), **existing, "already_recorded": True}
        stored = self.add_evidence(
            EvidenceRecord(
                "convex_optimization_model",
                canonical_semantic_json(model.to_dict()),
                source=CONVEX_OPTIMIZATION_CONTRACT_ID,
                metadata={"convex_record_type": "MODEL", "model_id": model.model_id, "model_fingerprint": model.fingerprint},
            ),
            reason=reason,
        )
        return {"contract": convex_optimization_contract(), "model": model.to_dict(), "evidence_id": stored.evidence_id, "already_recorded": False}

    def convex_request_report(self, request_id: str | None = None):
        requests = {}
        for row in _rows(self.snapshot, "convex_optimization_request"):
            request = ConvexOptimizationRequest.from_dict(_doc(row))
            requests[request.request_id] = {"request": request.to_dict(), "evidence_id": row["evidence_id"]}
        if request_id is not None:
            if request_id not in requests:
                raise KeyError(request_id)
            return {"contract": convex_optimization_contract(), **deepcopy(requests[request_id])}
        return {"contract": convex_optimization_contract(), "requests": requests}

    def convex_result_report(self, request_id: str | None = None):
        results = {}
        for row in _rows(self.snapshot, "convex_optimization_result"):
            result = ConvexOptimizationResult.from_dict(_doc(row))
            results.setdefault(result.request_id, []).append({"result": result.to_dict(), "evidence_id": row["evidence_id"]})
        for rows in results.values(): rows.sort(key=lambda item: item["result"]["result_id"])
        if request_id is not None:
            return {"contract": convex_optimization_contract(), "request_id": request_id, "results": deepcopy(results.get(request_id, []))}
        return {"contract": convex_optimization_contract(), "results": results}

    def request_convex_optimization(
        self,
        model_id: str,
        *,
        requester_id: str,
        timeout_ms: int = 30_000,
        environment_fingerprint: str = "",
        dependency_fingerprints: Sequence[str] = (),
        priority: int = 0,
    ):
        model_row = self.convex_model_report(model_id)
        model = ConvexOptimizationModel.from_dict(model_row["model"])
        provider_row = self.capability_report()["providers"].get("cvxpy")
        if provider_row is None:
            raise KeyError("CVXPY provider is not admitted")
        provider = CapabilityProvider.from_dict(provider_row["provider"])
        if provider.capability_id != CONVEX_CAPABILITY_ID:
            raise ValueError("admitted CVXPY provider does not implement solver.convex")
        obligation_id = "convex-obligation-" + semantic_fingerprint({
            "model_fingerprint": model.fingerprint,
            "provider": "cvxpy",
            "environment_fingerprint": environment_fingerprint,
            "dependency_fingerprints": sorted(set(map(str, dependency_fingerprints))),
        })[:20]
        request = ConvexOptimizationRequest(
            model,
            CONVEX_CAPABILITY_ID,
            "0.1.0",
            obligation_id,
            timeout_ms=timeout_ms,
            environment_fingerprint=environment_fingerprint,
            dependency_fingerprints=tuple(dependency_fingerprints),
            metadata={"requester_id": requester_id},
        )
        existing = self.convex_request_report()["requests"].get(request.request_id)
        if obligation_id not in self.calculus_report()["obligations"]:
            self.register_obligation(
                ObligationRecord(
                    obligation_id=obligation_id,
                    statement=f"solve convex optimization model {model_id}",
                    status="AVAILABLE",
                    required_evidence_types=["convex_optimization_result"],
                    scope={"scope_id": "root"},
                ),
                reason="convex optimization obligation registered",
            )
        if existing is None:
            stored = self.add_evidence(
                EvidenceRecord(
                    "convex_optimization_request",
                    canonical_semantic_json(request.to_dict()),
                    source=CONVEX_OPTIMIZATION_CONTRACT_ID,
                    derived_from=[model_row["evidence_id"]],
                    metadata={"convex_record_type": "REQUEST", "request_id": request.request_id, "request_fingerprint": request.fingerprint, "obligation_id": obligation_id},
                ),
                reason="convex optimization requested",
            )
            evidence_id = stored.evidence_id
        else:
            prior = ConvexOptimizationRequest.from_dict(existing["request"])
            if prior.fingerprint != request.fingerprint:
                raise ValueError(f"convex request ID collision: {request.request_id}")
            evidence_id = existing["evidence_id"]
        task_id = f"{request.request_id}:cvxpy"
        resources = deepcopy(self.snapshot.resources)
        queue = resources.setdefault("tasks", [])
        task = TaskDemand(
            task_id,
            [request.capability_token, provider.provider_token],
            demand=1.0,
            priority=priority,
            allowed_kinds=["optimization-solver"],
            metadata={"convex_request_id": request.request_id, "convex_request_fingerprint": request.fingerprint, "required_provider": "cvxpy", "obligation_id": obligation_id},
        )
        if not any(row.get("task_id") == task_id for row in queue):
            queue.append(deepcopy(task.__dict__))
            self.patch_snapshot({"resources": resources}, "convex optimization task queued")
        return {"contract": convex_optimization_contract(), "request": request.to_dict(), "request_evidence_id": evidence_id, "task": deepcopy(task.__dict__)}

    def _validate_convex_lease(self, lease_id: str, request: ConvexOptimizationRequest):
        lease = next((deepcopy(row) for row in self.list_leases() if row.get("lease_id") == lease_id), None)
        if lease is None: raise KeyError(lease_id)
        if lease.get("task_id") != f"{request.request_id}:cvxpy": raise ValueError("convex result lease does not belong to request")
        if lease.get("status") == "COMPLETED": return lease
        if lease.get("status") != "ACTIVE": raise ValueError(f"convex result lease is not ACTIVE: {lease.get('status')}")
        from .model import now
        if float(lease.get("expires_at", 0)) <= now(): raise ValueError("convex result lease expired before result commit")
        newer = [row for row in self.list_leases() if row.get("task_id") == lease.get("task_id") and int(row.get("attempt", 0)) > int(lease.get("attempt", 0)) and row.get("status") == "ACTIVE"]
        if newer: raise ValueError("convex result lease was superseded by a newer attempt")
        return lease

    def commit_convex_result(self, result: ConvexOptimizationResult | Mapping[str, Any], *, lease_id: str):
        result = result if isinstance(result, ConvexOptimizationResult) else ConvexOptimizationResult.from_dict(result)
        request_row = self.convex_request_report(result.request_id)
        request = ConvexOptimizationRequest.from_dict(request_row["request"])
        validate_convex_result(request, result)
        lease = self._validate_convex_lease(lease_id, request)
        provider_row = self.capability_report()["providers"].get(result.solver.provider_id)
        if provider_row is None: raise KeyError(f"unadmitted convex provider: {result.solver.provider_id}")
        provider = CapabilityProvider.from_dict(provider_row["provider"])
        if provider.implementation != result.solver.implementation: raise ValueError("convex result implementation does not match admitted provider")
        existing = self.convex_result_report(request.request_id)["results"]
        for row in existing:
            prior = ConvexOptimizationResult.from_dict(row["result"])
            if prior.result_id == result.result_id:
                if prior.fingerprint != result.fingerprint: raise ValueError(f"convex result ID collision: {result.result_id}")
                if lease.get("status") == "ACTIVE":
                    self._finish_lease(lease_id, LeaseStatus.COMPLETED.value, result={"convex_result_id": result.result_id, "already_committed": True}, reason="convex lease completed after exact replay")
                return {"contract": convex_optimization_contract(), "result": prior.to_dict(), "result_evidence_id": row["evidence_id"], "already_committed": True}
        if lease.get("status") == "COMPLETED": raise ValueError("completed convex lease cannot commit a new result")
        stored = self.add_evidence(
            EvidenceRecord(
                "convex_optimization_result",
                canonical_semantic_json(result.to_dict()),
                source=CONVEX_OPTIMIZATION_CONTRACT_ID,
                derived_from=[request_row["evidence_id"]],
                metadata={"convex_record_type": "RESULT", "request_id": request.request_id, "result_id": result.result_id, "status": result.status, "result_authority": "EVIDENCE_ONLY", "obligation_id": request.obligation_id},
            ),
            reason="convex optimization result committed",
        )
        obligation = self.calculus_report()["obligations"][request.obligation_id]
        status = obligation.get("status")
        if status == "AVAILABLE": self.enable_obligation(request.obligation_id, reason="convex obligation enabled"); status = "ENABLED"
        if status == "ENABLED": self.set_obligation_status(request.obligation_id, "IN_PROGRESS", reason="convex worker started"); status = "IN_PROGRESS"
        if status == "IN_PROGRESS": self.set_obligation_status(request.obligation_id, "VERIFYING", reason="convex result validating"); status = "VERIFYING"
        satisfied = result.status == "OPTIMAL"
        if satisfied and status == "VERIFYING": self.set_obligation_status(request.obligation_id, "VERIFIED", evidence_ids=[stored.evidence_id], reason="convex request satisfied")
        elif not satisfied and status == "VERIFYING": self.set_obligation_status(request.obligation_id, "BLOCKED", reason=f"convex result not optimal: {result.status}")
        lease_status = LeaseStatus.FAILED.value if result.status == "ERROR" else LeaseStatus.COMPLETED.value
        self._finish_lease(lease_id, lease_status, result={"convex_result_id": result.result_id, "status": result.status} if lease_status == LeaseStatus.COMPLETED.value else None, error="; ".join(result.diagnostics) if lease_status == LeaseStatus.FAILED.value else None, reason="convex worker result accepted")
        return {"contract": convex_optimization_contract(), "result": result.to_dict(), "result_evidence_id": stored.evidence_id, "obligation": deepcopy(self.calculus_report()["obligations"][request.obligation_id]), "satisfied": satisfied, "already_committed": False}

    def execute_convex_lease(self, lease_id: str):
        lease = next((deepcopy(row) for row in self.list_leases() if row.get("lease_id") == lease_id), None)
        if lease is None: raise KeyError(lease_id)
        request_id = str((lease.get("metadata") or {}).get("convex_request_id") or "")
        if not request_id: raise ValueError("lease is not a convex optimization task")
        request = ConvexOptimizationRequest.from_dict(self.convex_request_report(request_id)["request"])
        return self.commit_convex_result(solve_convex_request(request), lease_id=lease_id)

    def convex_reuse_request(self, request_id: str):
        request = ConvexOptimizationRequest.from_dict(self.convex_request_report(request_id)["request"])
        return ReuseRequest(
            kind="OPTIMIZATION_RESULT",
            semantic_payload={"optimization_subkind": "CONVEX", "request_id": request.request_id, "request_fingerprint": request.fingerprint, "model_fingerprint": request.model.fingerprint},
            environment_fingerprint=request.environment_fingerprint,
            dependency_fingerprints=request.dependency_fingerprints,
            effect_class="PURE",
        )

    def import_pulp_problem(self, problem, *, admit: bool = False):
        report = pulp_import_report(problem)
        if not admit:
            return report
        admitted = self.admit_optimization_model(pulp_problem_to_optimization_model(problem), reason="PuLP model imported and admitted")
        return {**report, "admitted": admitted}


__all__ = ["ConvexOptimizationRuntimeMixin"]
