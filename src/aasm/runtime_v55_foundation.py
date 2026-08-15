from __future__ import annotations

from ._runtime_v55_formulation import FormulationRuntimeMixin
from ._runtime_v55_semantic_evolution import SemanticEvolutionRuntimeMixin
from .runtime_v54_full import AASMEngine as V54Engine


class AASMEngine(FormulationRuntimeMixin, SemanticEvolutionRuntimeMixin, V54Engine):
    """Development-only v0.55 governed semantic-evolution foundation over released v0.54.

    The active package export intentionally remains v0.54 until the complete
    v0.55 release contracts and gates are satisfied. The formulation layer is
    additive: it reuses the existing semantic-evolution, Evidence, optimization,
    provider, and effect/runtime authority paths rather than introducing a
    parallel solver or truth lifecycle.
    """


__all__ = ["AASMEngine"]
