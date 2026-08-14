from .runtime_v47 import AASMEngine as V47Engine
from ._runtime_v48_knowledge import CrossRunKnowledgeRuntimeMixin


class AASMEngine(CrossRunKnowledgeRuntimeMixin, V47Engine):
    """AASM v0.48 runtime: v0.47 plus governed cross-run knowledge admission."""

    pass


__all__ = ["AASMEngine"]
