from __future__ import annotations

from typing import Any

from ._runtime_v39_capabilities import TypedCapabilityRuntimeMixin
from .runtime_v32 import AASMEngine as V38Engine, build_trace_corpus, default_profile_registry


class AASMEngine(TypedCapabilityRuntimeMixin, V38Engine):
    """v0.39 runtime: typed protocol/capability ABI plus formal verification workers."""

    def inspect_machine(self, surface: str = "summary") -> Any:
        if surface in {"typed-protocol", "typed-patterns"}:
            return self.typed_pattern_report()
        if surface in {"typed-transitions"}:
            return self.typed_transition_report()
        if surface in {"capabilities", "capability-abi"}:
            return self.capability_report()
        if surface in {"formal-verification", "formal-results"}:
            return self.formal_verification_report()
        if surface in {"formal-statements", "formalization"}:
            return self.formal_statement_report()
        if surface == "formal-blueprint":
            return self.formal_capability_blueprint()
        return super().inspect_machine(surface)


__all__ = ["AASMEngine", "default_profile_registry", "build_trace_corpus"]
