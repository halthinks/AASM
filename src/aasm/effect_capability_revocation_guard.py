from __future__ import annotations

from copy import deepcopy

from .effect_capability import EffectCapability


class EffectCapabilityRevocationGuardMixin:
    """Make revocation generation effective at revoked_at, including historical replay queries."""

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
