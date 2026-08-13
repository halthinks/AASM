from __future__ import annotations

from typing import Any

from .runtime_v31 import AASMEngine as V31Engine, default_profile_registry
from .trace_conformance import project_trace, semantic_trace_check, build_trace_corpus


class AASMEngine(V31Engine):
    """v0.32 runtime: production-history trace conformance over the existing event stream."""

    def trace_projection(self) -> dict[str, Any]:
        return project_trace(self.events)

    def semantic_trace_report(self) -> dict[str, Any]:
        return semantic_trace_check(self.events)

    def inspect_machine(self, surface: str = "summary") -> Any:
        if surface == "trace":
            return self.trace_projection()
        if surface == "trace-semantic":
            return self.semantic_trace_report()
        return super().inspect_machine(surface)


__all__ = ["AASMEngine", "default_profile_registry", "build_trace_corpus"]
