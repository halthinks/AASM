from copy import deepcopy

from .runtime_v45 import AASMEngine as V45Engine
from ._runtime_v46_advanced import AdvancedOptimizationRuntimeMixin
from .advanced_execution import solve_advanced_request
from .advanced_optimization import AdvancedSolverRequest


class AASMEngine(AdvancedOptimizationRuntimeMixin, V45Engine):
    """AASM v0.46 runtime: v0.45 plus advanced native solver control/search artifacts."""

    def execute_advanced_optimization_lease(self, lease_id: str):
        """Execute an advanced lease through the corrected backend adapter layer."""
        lease = next((deepcopy(row) for row in self.list_leases() if row.get("lease_id") == lease_id), None)
        if lease is None:
            raise KeyError(lease_id)
        request_id = str((lease.get("metadata") or {}).get("advanced_request_id") or "")
        if not request_id:
            raise ValueError("lease is not an advanced optimization task")
        request = AdvancedSolverRequest.from_dict(self.advanced_request_report(request_id)["request"])
        result = solve_advanced_request(request)
        return self.commit_advanced_optimization_result(result, lease_id=lease_id)


__all__ = ["AASMEngine"]
