from __future__ import annotations

from copy import deepcopy
from typing import Any, Sequence

from .runtime_v31 import AASMEngine as V31Engine, default_profile_registry
from .trace_conformance import (
    project_trace, semantic_trace_check, build_trace_corpus,
    export_provenance, verify_provenance_export, create_selective_provenance_export,
)
from .workers import LeaseStatus


class AASMEngine(V31Engine):
    """v0.34 runtime: trace/provenance plus certified distributed recovery invariants."""

    def _finish_lease(self, lease_id: str, status: str, *, result=None, error=None, at_time=None, reason="lease finished"):
        """Reject stale worker results before they can change canonical task state.

        Release/expiry remain idempotent operational cleanup. Completion and
        failure, however, are worker results and therefore require the exact
        lease to still own the task at the supplied completion time.
        """
        from .model import now

        ts = now() if at_time is None else float(at_time)
        lease = next((row for row in self.snapshot.resources.get("leases", []) if row.get("lease_id") == lease_id), None)
        if lease is None:
            raise KeyError(lease_id)

        result_statuses = {LeaseStatus.COMPLETED.value, LeaseStatus.FAILED.value}
        if status in result_statuses:
            if lease.get("status") != LeaseStatus.ACTIVE.value:
                raise ValueError(
                    f"Lease {lease_id} cannot accept a worker result from status {lease.get('status')}"
                )
            if float(lease.get("expires_at", 0)) <= ts:
                # Canonically expire the stale ownership before rejecting its result.
                super()._finish_lease(
                    lease_id,
                    LeaseStatus.EXPIRED.value,
                    at_time=ts,
                    reason="stale worker result arrived after lease expiry",
                )
                raise ValueError(f"Lease {lease_id} expired before worker result completion")
            newer = [
                row for row in self.snapshot.resources.get("leases", [])
                if row.get("task_id") == lease.get("task_id")
                and int(row.get("attempt", 0)) > int(lease.get("attempt", 0))
                and row.get("status") == LeaseStatus.ACTIVE.value
            ]
            if newer:
                raise ValueError(
                    f"Lease {lease_id} is stale; task {lease.get('task_id')} is owned by newer attempt(s) "
                    f"{sorted(row.get('lease_id') for row in newer)}"
                )

        return super()._finish_lease(
            lease_id,
            status,
            result=deepcopy(result),
            error=error,
            at_time=ts,
            reason=reason,
        )

    def trace_projection(self) -> dict[str, Any]:
        return project_trace(self.events)

    def semantic_trace_report(self) -> dict[str, Any]:
        return semantic_trace_check(self.events)

    def provenance_export(self, destination: str, *, key: bytes | str, signer_id: str = "local") -> dict[str, Any]:
        return export_provenance(self, destination, key=key, signer_id=signer_id)

    def provenance_verify(self, source: str, *, key: bytes | str, signer_id: str | None = None) -> dict[str, Any]:
        return verify_provenance_export(source, key=key, signer_id=signer_id)

    def provenance_select(self, source: str, destination: str, names: Sequence[str], *, key: bytes | str, signer_id: str = "local") -> dict[str, Any]:
        return create_selective_provenance_export(source, destination, names, key=key, signer_id=signer_id)

    def inspect_machine(self, surface: str = "summary") -> Any:
        if surface == "trace": return self.trace_projection()
        if surface == "trace-semantic": return self.semantic_trace_report()
        if surface == "provenance":
            return {"contract": "aasm.provenance.v1", "exportable": True, "source_trace_sha256": self.trace_projection()["source_trace_sha256"]}
        return super().inspect_machine(surface)


__all__ = ["AASMEngine", "default_profile_registry", "build_trace_corpus"]