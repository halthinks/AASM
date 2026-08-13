from __future__ import annotations

from typing import Any

from ._runtime_v40_privacy import PrincipalBoundMemoryRuntimeMixin
from .runtime_v39 import AASMEngine as V39Engine, build_trace_corpus, default_profile_registry


class AASMEngine(PrincipalBoundMemoryRuntimeMixin, V39Engine):
    """v0.40 runtime: governed hierarchical memory, reasoning frontier, and bounded context projection."""

    def inspect_machine(self, surface: str = "summary") -> Any:
        if surface in {"hierarchical-memory", "memory-hierarchy"}:
            return self.hierarchical_memory_report()
        if surface == "reasoning-frontier":
            from .hierarchical_memory import ContextProjectionRequest
            return self.reasoning_frontier(ContextProjectionRequest())
        if surface == "context-projection":
            from .hierarchical_memory import ContextProjectionRequest
            return self.context_projection(ContextProjectionRequest(metadata={"principal_id": "inspect"}))
        if surface in {"hierarchical-memory-contract", "context-projection-contract"}:
            return self.hierarchical_memory_contract_report()
        return super().inspect_machine(surface)


__all__ = ["AASMEngine", "default_profile_registry", "build_trace_corpus"]
