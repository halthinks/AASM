from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence

from .calculus import ObligationRecord
from .evidence import EvidenceRecord
from .optimization import (
    OPTIMIZATION_CAPABILITIES,
    OPTIMIZATION_CONTRACT_ID,
    OptimizationModel,
    OptimizationRequest,
    OptimizationResult,
    default_optimization_capability_contracts,
    default_optimization_providers,
    optimization_blueprint,
    optimization_contract,
    optimization_result_satisfies_request,
    solve_optimization_request,
    validate_optimization_result,
)
from .resources import ResourceRecord, TaskDemand
from .reuse_model import ReuseRequest
from .semantic_result import canonical_semantic_json, semantic_fingerprint
from .typed_protocol import CapabilityContract, CapabilityProvider
from .workers import LeaseStatus, WorkerRecord


def _evidence_rows(snapshot, kind: str) -> list[dict[str, Any]]:
    evidence = snapshot.evidence if isinstance(snapshot.evidence, dict) else {}
    return [row for row in evidence.get("records", []) if row.get("kind") == kind and row.get("status", "active") == "active"]


def _document(row: Mapping[str, Any]) -> dict[str, Any]:
    import json
    return json.loads(str(row.get("statement") or "{}"))


class OptimizationRuntimeMixin:
    """v0.44 SAT/CP-SAT/MILP portfolio over the existing AASM scheduler and lease ABI."""

    def optimization_contract_report(self) -> dict[str, Any]:
        return optimization_contract()

    def optimization_blueprint(self) -> dict[str, Any]:
        value = optimization_blueprint()
        formal = self.formal_capability_blueprint()
        value["formal_providers"] = deepcopy(formal.get("providers", []))
        value["portfolio_provider_ids"] = sorted(
            [row["provider_id"] for row in value["providers"]]
            + [row["provider_id"] for row in value["formal_providers"]]
        )
        return value

    def install_default_optimization_capability_contracts(
        self,
        *,
        authority_id: str,
        authority_class: str,
        reason: str = "default optimization capability contracts admitted",
    ) -> dict[str, Any]:
        return {
            "contract": optimization_contract(),
            "installed": [
                self.register_capability_contract(
                    contract,
                    authority_id=authority_id,
                    authority_class=authority_class,
                    reason=reason,
                )
                for contract in default_optimization_capability_contracts()
            ],
        }

    def register_optimization_provider_runtime(
        self,
        provider: CapabilityProvider | Mapping[str, Any],
        *,
        authority_id: str,
        authority_class: str,
        worker_id: str | None = None,
        capacity: float = 1.0,
        reliability: float = 1.0,
        heartbeat_timeout: float = 60.0,
        reason: str = "optimization provider runtime admitted",
    ) -> dict[str, Any]:
        if authority_class not in {"POLICY", "CONTROLLER"}:
            raise PermissionError("optimization provider runtime admission requires POLICY or CONTROLLER authority")
        provider = provider if isinstance(provider, CapabilityProvider) else CapabilityProvider.from_dict(provider)
        contract_row = self.capability_report(provider.capability_id)["capability"]["contract"]
        contract = CapabilityContract.from_dict(contract_row)
        if contract.capability_type != "OPERATOR":
            raise ValueError("optimization provider requires an OPERATOR capability")
        if provider.capability_version != contract.version:
            raise ValueError("optimization provider version does not match capability contract")
        family = str(contract.metadata.get("solver_family") or "")
        if family not in OPTIMIZATION_CAPABILITIES or OPTIMIZATION_CAPABILITIES[family] != provider.capability_id:
            raise ValueError("optimization provider capability lacks a valid solver family")
        required_tokens = {provider.capability_token, provider.provider_token}
        resource = next((row for row in self.list_resources() if row.get("resource_id") == provider.resource_id), None)
        if resource is None:
            resource = self.register_resource(
                ResourceRecord(
                    resource_id=provider.resource_id,
                    kind="optimization-solver",
                    capabilities=sorted(required_tokens),
                    capacity=capacity,
                    reliability=reliability,
                    metadata={"provider_id": provider.provider_id, "implementation": provider.implementation, "solver_family": family},
                ),
                reason=reason,
            )
        else:
            if resource.get("kind") != "optimization-solver" or not required_tokens.issubset(set(resource.get("capabilities", []))):
                raise ValueError("existing resource is incompatible with optimization provider")
        worker_identity = worker_id or f"worker-{provider.provider_id}"
        worker = next((row for row in self.list_workers() if row.get("worker_id") == worker_identity), None)
        if worker is None:
            worker = self.register_worker(
                WorkerRecord(
                    worker_id=worker_identity,
                    resource_id=provider.resource_id,
                    heartbeat_timeout=heartbeat_timeout,
                    metadata={"optimization_provider_id": provider.provider_id, "solver_family": family},
                ),
                reason=reason,
            )
        elif worker.get("resource_id") != provider.resource_id:
            raise ValueError("existing optimization worker is bound to a different resource")
        admitted = self.register_capability_provider(
            provider,
            authority_id=authority_id,
            authority_class=authority_class,
            reason=reason,
        )
        return {"contract": optimization_contract(), "resource": resource, "worker": worker, "provider": admitted}

    def optimization_model_report(self, model_id: str | None = None) -> dict[str, Any]:
        models: dict[str, Any] = {}
        for row in _evidence_rows(self.snapshot, "optimization_model"):
            model = OptimizationModel.from_dict(_document(row))
            models[model.model_id] = {"model": model.to_dict(), "evidence_id": row["evidence_id"]}
        if model_id is not None:
            if model_id not in models:
                raise KeyError(model_id)
            return {"contract": optimization_contract(), **deepcopy(models[model_id])}
        return {"contract": optimization_contract(), "models": models}

    def admit_optimization_model(
        self,
        model: OptimizationModel | Mapping[str, Any],
        *,
        reason: str = "optimization model admitted",
    ) -> dict[str, Any]:
        model = model if isinstance(model, OptimizationModel) else OptimizationModel.from_dict(model)
        existing = self.optimization_model_report()["models"].get(model.model_id)
        if existing:
            prior = OptimizationModel.from_dict(existing["model"])
            if prior.fingerprint != model.fingerprint:
                raise ValueError(f"optimization model ID collision: {model.model_id}")
            return {"contract": optimization_contract(), **existing, "already_recorded": True}
        stored = self.add_evidence(
            EvidenceRecord(
                kind="optimization_model",
                statement=canonical_semantic_json(model.to_dict()),
                source=OPTIMIZATION_CONTRACT_ID,
                metadata={
                    "optimization_record_type": "MODEL",
                    "optimization_contract_id": OPTIMIZATION_CONTRACT_ID,
                    "model_id": model.model_id,
                    "model_fingerprint": model.fingerprint,
                    "solver_family": model.solver_family,
                },
            ),
            reason=reason,
        )
        return {"contract": optimization_contract(), "model": model.to_dict(), "evidence_id": stored.evidence_id, "already_recorded": False}

    def optimization_request_report(self, request_id: str | None = None) -> dict[str, Any]:
        requests: dict[str, Any] = {}
        for row in _evidence_rows(self.snapshot, "optimization_request"):
            request = OptimizationRequest.from_dict(_document(row))
            requests[request.request_id] = {"request": request.to_dict(), "evidence_id": row["evidence_id"]}
        if request_id is not None:
            if request_id not in requests:
                raise KeyError(request_id)
            return {"contract": optimization_contract(), **deepcopy(requests[request_id])}
        return {"contract": optimization_contract(), "requests": requests}

    def optimization_result_report(self, request_id: str | None = None) -> dict[str, Any]:
        rows: dict[str, list[dict[str, Any]]] = {}
        for row in _evidence_rows(self.snapshot, "optimization_result"):
            result = OptimizationResult.from_dict(_document(row))
            rows.setdefault(result.request_id, []).append({"result": result.to_dict(), "evidence_id": row["evidence_id"]})
        for values in rows.values():
            values.sort(key=lambda item: item["result"]["result_id"])
        if request_id is not None:
            return {"contract": optimization_contract(), "request_id": request_id, "results": deepcopy(rows.get(request_id, []))}
        return {"contract": optimization_contract(), "results": rows}

    def request_optimization(
        self,
        model_id: str,
        *,
        requester_id: str,
        required_provider: str,
        timeout_ms: int = 30_000,
        accept_feasible: bool = False,
        environment_fingerprint: str = "",
        dependency_fingerprints: Sequence[str] = (),
        priority: int = 0,
        reason: str = "optimization requested",
    ) -> dict[str, Any]:
        model_row = self.optimization_model_report(model_id)
        model = OptimizationModel.from_dict(model_row["model"])
        capability_id = OPTIMIZATION_CAPABILITIES[model.solver_family]
        capability = CapabilityContract.from_dict(self.capability_report(capability_id)["capability"]["contract"])
        providers = self.capability_report()["providers"]
        if required_provider not in providers:
            raise KeyError(f"unknown optimization provider: {required_provider}")
        provider = CapabilityProvider.from_dict(providers[required_provider]["provider"])
        if provider.capability_id != capability_id or provider.capability_version != capability.version:
            raise ValueError("required optimization provider does not implement model capability")
        obligation_id = "optimization-obligation-" + semantic_fingerprint({
            "model_fingerprint": model.fingerprint,
            "capability_id": capability_id,
            "provider": required_provider,
            "environment_fingerprint": environment_fingerprint,
            "dependency_fingerprints": sorted(set(map(str, dependency_fingerprints))),
        })[:20]
        request = OptimizationRequest(
            model,
            capability_id,
            capability.version,
            obligation_id,
            timeout_ms=timeout_ms,
            required_provider=required_provider,
            accept_feasible=accept_feasible,
            environment_fingerprint=environment_fingerprint,
            dependency_fingerprints=tuple(dependency_fingerprints),
            metadata={"requester_id": requester_id},
        )
        existing = self.optimization_request_report()["requests"].get(request.request_id)
        if obligation_id not in self.calculus_report()["obligations"]:
            self.register_obligation(
                ObligationRecord(
                    obligation_id=obligation_id,
                    statement=f"solve optimization model {model_id}",
                    status="AVAILABLE",
                    required_evidence_types=["optimization_result"],
                    scope={"scope_id": "root"},
                ),
                reason="optimization obligation registered",
            )
        if existing is None:
            stored = self.add_evidence(
                EvidenceRecord(
                    kind="optimization_request",
                    statement=canonical_semantic_json(request.to_dict()),
                    source=OPTIMIZATION_CONTRACT_ID,
                    derived_from=[model_row["evidence_id"]],
                    metadata={
                        "optimization_record_type": "REQUEST",
                        "optimization_contract_id": OPTIMIZATION_CONTRACT_ID,
                        "request_id": request.request_id,
                        "request_fingerprint": request.fingerprint,
                        "model_id": model.model_id,
                        "model_fingerprint": model.fingerprint,
                        "solver_family": model.solver_family,
                        "capability_id": capability_id,
                        "required_provider": required_provider,
                        "obligation_id": obligation_id,
                    },
                ),
                reason=reason,
            )
            request_evidence_id = stored.evidence_id
        else:
            prior = OptimizationRequest.from_dict(existing["request"])
            if prior.fingerprint != request.fingerprint:
                raise ValueError(f"optimization request ID collision: {request.request_id}")
            request_evidence_id = existing["evidence_id"]
        task_id = f"{request.request_id}:{required_provider}"
        resources = deepcopy(self.snapshot.resources)
        queue = resources.setdefault("tasks", [])
        task = TaskDemand(
            task_id=task_id,
            required_capabilities=[request.capability_token, provider.provider_token],
            demand=1.0,
            priority=priority,
            allowed_kinds=["optimization-solver"],
            metadata={
                "optimization_request_id": request.request_id,
                "optimization_request_fingerprint": request.fingerprint,
                "model_fingerprint": model.fingerprint,
                "obligation_id": obligation_id,
                "required_provider": required_provider,
            },
        )
        if not any(row.get("task_id") == task_id for row in queue):
            queue.append(deepcopy(task.__dict__))
            self.patch_snapshot({"resources": resources}, "optimization task queued")
        return {
            "contract": optimization_contract(),
            "request": request.to_dict(),
            "request_evidence_id": request_evidence_id,
            "task": deepcopy(task.__dict__),
            "obligation": deepcopy(self.calculus_report()["obligations"][obligation_id]),
        }

    def _optimization_lease(self, lease_id: str, request: OptimizationRequest) -> dict[str, Any]:
        lease = next((deepcopy(row) for row in self.list_leases() if row.get("lease_id") == lease_id), None)
        if lease is None:
            raise KeyError(lease_id)
        expected_task = f"{request.request_id}:{request.required_provider}"
        if lease.get("task_id") != expected_task:
            raise ValueError("optimization result lease does not belong to request/provider")
        if lease.get("status") not in {"ACTIVE", "COMPLETED"}:
            raise ValueError(f"optimization result lease is not ACTIVE: {lease.get('status')}")
        return lease

    def commit_optimization_result(
        self,
        result: OptimizationResult | Mapping[str, Any],
        *,
        lease_id: str,
        reason: str = "optimization result committed",
    ) -> dict[str, Any]:
        result = result if isinstance(result, OptimizationResult) else OptimizationResult.from_dict(result)
        request_row = self.optimization_request_report(result.request_id)
        request = OptimizationRequest.from_dict(request_row["request"])
        validate_optimization_result(request, result)
        lease = self._optimization_lease(lease_id, request)
        if result.solver.provider_id != request.required_provider:
            raise ValueError("optimization result provider does not match required provider")
        provider_row = self.capability_report()["providers"].get(result.solver.provider_id)
        if provider_row is None:
            raise KeyError(f"unadmitted optimization provider: {result.solver.provider_id}")
        provider = CapabilityProvider.from_dict(provider_row["provider"])
        if provider.capability_id != request.capability_id:
            raise ValueError("optimization result provider does not implement request capability")
        existing = self.optimization_result_report(request.request_id)["results"]
        for row in existing:
            prior = OptimizationResult.from_dict(row["result"])
            if prior.result_id == result.result_id:
                if prior.fingerprint != result.fingerprint:
                    raise ValueError(f"optimization result ID collision: {result.result_id}")
                if lease.get("status") == "ACTIVE":
                    self._finish_lease(lease_id, LeaseStatus.COMPLETED.value, result={"optimization_result_id": result.result_id, "already_committed": True}, reason="optimization lease completed after idempotent replay")
                return {"contract": optimization_contract(), "result": prior.to_dict(), "result_evidence_id": row["evidence_id"], "already_committed": True}
        if lease.get("status") == "COMPLETED":
            raise ValueError("completed optimization lease cannot commit a new result")
        stored = self.add_evidence(
            EvidenceRecord(
                kind="optimization_result",
                statement=canonical_semantic_json(result.to_dict()),
                source=OPTIMIZATION_CONTRACT_ID,
                derived_from=[request_row["evidence_id"]],
                metadata={
                    "optimization_record_type": "RESULT",
                    "optimization_contract_id": OPTIMIZATION_CONTRACT_ID,
                    "request_id": request.request_id,
                    "result_id": result.result_id,
                    "result_fingerprint": result.fingerprint,
                    "model_fingerprint": result.model_fingerprint,
                    "provider_id": result.solver.provider_id,
                    "solver_fingerprint": result.solver.fingerprint,
                    "status": result.status,
                    "evidence_type": "optimization_result",
                    "result_authority": "EVIDENCE_ONLY",
                    "obligation_id": request.obligation_id,
                },
            ),
            reason=reason,
        )
        obligation = self.calculus_report()["obligations"][request.obligation_id]
        status = obligation.get("status")
        if status == "AVAILABLE":
            self.enable_obligation(request.obligation_id, reason="optimization obligation enabled")
            status = "ENABLED"
        if status == "ENABLED":
            self.set_obligation_status(request.obligation_id, "IN_PROGRESS", reason="optimization worker started")
            status = "IN_PROGRESS"
        if status == "IN_PROGRESS":
            self.set_obligation_status(request.obligation_id, "VERIFYING", reason="optimization result validating")
            status = "VERIFYING"
        satisfied = optimization_result_satisfies_request(request, result)
        if satisfied and status == "VERIFYING":
            self.set_obligation_status(request.obligation_id, "VERIFIED", evidence_ids=[stored.evidence_id], reason="optimization request satisfied")
        elif not satisfied and status == "VERIFYING":
            self.set_obligation_status(request.obligation_id, "BLOCKED", reason=f"optimization result not terminally satisfactory: {result.status}")
        lease_status = LeaseStatus.FAILED.value if result.status == "ERROR" else LeaseStatus.COMPLETED.value
        self._finish_lease(
            lease_id,
            lease_status,
            result={"optimization_result_id": result.result_id, "status": result.status} if lease_status == LeaseStatus.COMPLETED.value else None,
            error="; ".join(result.diagnostics) or "optimization worker error" if lease_status == LeaseStatus.FAILED.value else None,
            reason="optimization worker result accepted",
        )
        return {
            "contract": optimization_contract(),
            "result": result.to_dict(),
            "result_evidence_id": stored.evidence_id,
            "obligation": deepcopy(self.calculus_report()["obligations"][request.obligation_id]),
            "satisfied": satisfied,
            "already_committed": False,
        }

    def execute_optimization_lease(self, lease_id: str) -> dict[str, Any]:
        lease = next((deepcopy(row) for row in self.list_leases() if row.get("lease_id") == lease_id), None)
        if lease is None:
            raise KeyError(lease_id)
        request_id = str((lease.get("metadata") or {}).get("optimization_request_id") or "")
        if not request_id:
            raise ValueError("lease is not an optimization task")
        request = OptimizationRequest.from_dict(self.optimization_request_report(request_id)["request"])
        result = solve_optimization_request(request)
        return self.commit_optimization_result(result, lease_id=lease_id)

    def optimization_reuse_request(self, request_id: str) -> ReuseRequest:
        request = OptimizationRequest.from_dict(self.optimization_request_report(request_id)["request"])
        return ReuseRequest(
            kind="OPTIMIZATION_RESULT",
            semantic_payload={
                "optimization_request_id": request.request_id,
                "optimization_request_fingerprint": request.fingerprint,
                "model_fingerprint": request.model.fingerprint,
                "solver_family": request.model.solver_family,
            },
            environment_fingerprint=request.environment_fingerprint,
            dependency_fingerprints=request.dependency_fingerprints,
            effect_class="PURE",
        )


__all__ = ["OptimizationRuntimeMixin"]
