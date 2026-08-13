from __future__ import annotations

from copy import deepcopy
from typing import Any

from ._runtime_v40_privacy import PrincipalBoundMemoryRuntimeMixin
from .runtime_v39 import AASMEngine as V39Engine, build_trace_corpus, default_profile_registry


class AASMEngine(PrincipalBoundMemoryRuntimeMixin, V39Engine):
    """v0.40 runtime: governed hierarchical memory, reasoning frontier, and bounded context projection."""

    def calculus_report(self) -> dict[str, Any]:
        """Retain the ordinary calculus report and expose its authoritative scope projection.

        V31 keeps scope state inside the canonical calculus snapshot while the
        older public calculus report intentionally predates scopes. V40 memory
        consumes both decisions/obligations and scope flow, so the current
        report includes the same normalized scope_state used by V31 itself.
        """
        report = super().calculus_report()
        report["scope_state"] = deepcopy(self._begin_calculus()["scope_state"])
        return report

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
