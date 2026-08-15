from __future__ import annotations

from ._runtime_v54_effect_resources import EffectResourceSettlementMixin
from .runtime_v54_exchange import AASMEngine as V54ExchangeEngine


class AASMEngine(EffectResourceSettlementMixin, V54ExchangeEngine):
    """Complete experimental v0.54 composition over the released v0.53 runtime."""


__all__ = ["AASMEngine"]
