from __future__ import annotations

from typing import Any, Mapping

from .effects import EffectStatus
from .physical_effect_integration_runtime import PhysicalEffectIntegrationRuntimeMixin


class PhysicalEffectIntegrationBoundaryMixin(PhysicalEffectIntegrationRuntimeMixin):
    """PR-3H point-of-use boundary over the existing v0.54 Effect API.

    The parent runtime owns durable physical-effect binding/projection and the
    authorization hook. This specialization preserves v0.54's worker/TaskLease
    dispatch signature exactly while ensuring the physical authority recheck
    happens before a new dispatch request can be created.
    """

    def execute_effect(
        self,
        effect_id,
        executor,
        *,
        workspace_id: str | None = None,
        scope_id: str | None = None,
        actor_principal_id: str | None = None,
        owner_worker_id: str | None = None,
        task_lease_id: str | None = None,
        at_time: float = 0.0,
        dispatch_metadata: Mapping[str, Any] | None = None,
    ):
        record = self.store.load_effect(self.snapshot.machine_id, effect_id)
        if record.status != EffectStatus.SUCCEEDED.value and workspace_id and scope_id:
            validation = self._validate_physical_effect_authority_at_time(
                effect_id,
                workspace_id=workspace_id,
                scope_id=scope_id,
                actor_principal_id=actor_principal_id,
                at_time=at_time,
            )
            if validation is not None:
                self._record_physical_effect_recheck(
                    effect_id,
                    boundary="EXECUTE",
                    validation=validation,
                )

        # PhysicalEffectIntegrationRuntimeMixin also provides an execute_effect
        # compatibility hook, but v0.54 adds owner_worker_id/task_lease_id and
        # dispatch_metadata. Start lookup *after* that parent method so the
        # complete existing v0.54 lifecycle receives those arguments unchanged.
        return super(PhysicalEffectIntegrationRuntimeMixin, self).execute_effect(
            effect_id,
            executor,
            workspace_id=workspace_id,
            scope_id=scope_id,
            actor_principal_id=actor_principal_id,
            owner_worker_id=owner_worker_id,
            task_lease_id=task_lease_id,
            at_time=at_time,
            dispatch_metadata=dispatch_metadata,
        )


__all__ = ["PhysicalEffectIntegrationBoundaryMixin"]
