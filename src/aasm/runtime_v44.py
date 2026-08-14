from __future__ import annotations

from copy import deepcopy

from .model import now
from .optimization import OptimizationResult
from .runtime_v41 import AASMEngine as V41Engine
from ._runtime_v44_optimization import OptimizationRuntimeMixin
from .typed_protocol import CapabilityProvider


class OptimizationHardeningMixin:
    """Match native optimization result admission to the v0.39 formal-worker lease boundary."""

    def _optimization_lease(self, lease_id, request):
        lease = next((deepcopy(row) for row in self.list_leases() if row.get("lease_id") == lease_id), None)
        if lease is None:
            raise KeyError(lease_id)
        expected_task = f"{request.request_id}:{request.required_provider}"
        if lease.get("task_id") != expected_task:
            raise ValueError("optimization result lease does not belong to request/provider")
        if lease.get("status") == "COMPLETED":
            return lease
        if lease.get("status") != "ACTIVE":
            raise ValueError(f"optimization result lease is not ACTIVE: {lease.get('status')}")
        if float(lease.get("expires_at", 0)) <= now():
            raise ValueError("optimization result lease expired before result commit")
        newer = [
            row
            for row in self.list_leases()
            if row.get("task_id") == lease.get("task_id")
            and int(row.get("attempt", 0)) > int(lease.get("attempt", 0))
            and row.get("status") == "ACTIVE"
        ]
        if newer:
            raise ValueError("optimization result lease was superseded by a newer attempt")
        return lease

    def commit_optimization_result(self, result, *, lease_id, reason="optimization result committed"):
        parsed = result if isinstance(result, OptimizationResult) else OptimizationResult.from_dict(result)
        provider_row = self.capability_report()["providers"].get(parsed.solver.provider_id)
        if provider_row is None:
            raise KeyError(f"unadmitted optimization provider: {parsed.solver.provider_id}")
        provider = CapabilityProvider.from_dict(provider_row["provider"])
        if parsed.solver.implementation != provider.implementation:
            raise ValueError("optimization result implementation does not match admitted provider")
        return super().commit_optimization_result(parsed, lease_id=lease_id, reason=reason)


class AASMEngine(OptimizationHardeningMixin, OptimizationRuntimeMixin, V41Engine):
    """AASM v0.44 runtime: v0.41 kernel plus native heterogeneous optimization portfolio."""

    pass


__all__ = ["AASMEngine"]
