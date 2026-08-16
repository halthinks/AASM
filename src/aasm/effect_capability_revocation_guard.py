from __future__ import annotations

from copy import deepcopy

from .effect_capability import EffectCapability
from .effect_capability_runtime import EFFECT_CAPABILITY_CAPABILITIES


class EffectCapabilityRevocationGuardMixin:
    """Boundary guards for time-correct revocation and fail-closed root issuance."""

    def issue_effect_capability(
        self,
        capability,
        *,
        actor_principal_id: str,
        at_time: float,
        evidence_ids=(),
        reason: str = "bounded effect capability issued",
    ):
        item = capability if isinstance(capability, EffectCapability) else EffectCapability.from_dict(capability)
        if actor_principal_id != item.issuer_principal_id:
            self._authorize_effect_capability_action(
                actor_principal_id=actor_principal_id,
                workspace_id=item.workspace_id,
                scope_id=item.scope_id,
                capability=EFFECT_CAPABILITY_CAPABILITIES["issue"],
                at_time=at_time,
                metadata={"capability_id": item.capability_id, "nonissuer_attempt": True},
                derived_from=tuple(evidence_ids),
            )
            raise PermissionError("effect capability actor must equal issuer_principal_id")
        return super().issue_effect_capability(
            item,
            actor_principal_id=actor_principal_id,
            at_time=at_time,
            evidence_ids=evidence_ids,
            reason=reason,
        )

    def effect_capability_report(self, capability_id: str, *, at_time: float, _seen=frozenset()):
        result = super().effect_capability_report(capability_id, at_time=at_time, _seen=_seen)
        item = EffectCapability.from_dict(result["capability"])
        revocation_row = result.get("revocation")
        effective_generation = item.revocation_generation
        if revocation_row is not None:
            revocation = deepcopy(revocation_row["revocation"])
            if float(at_time) >= float(revocation["revoked_at"]):
                effective_generation = int(revocation["revocation_generation"])
        result["effective_revocation_generation"] = effective_generation
        return result


__all__ = ["EffectCapabilityRevocationGuardMixin"]
