from __future__ import annotations

from copy import deepcopy
from typing import Any

from .integrations.conformance import conformance_contract
from .runtime_v29 import AASMEngine as V29Engine, default_profile_registry


class AASMEngine(V29Engine):
    """v0.30 runtime surface: conformance inspection over unchanged authority."""

    def adapter_conformance_contract(self) -> dict[str, Any]:
        return deepcopy(conformance_contract())

    def inspect_machine(self, surface: str = "summary") -> Any:
        if surface == "adapter-conformance":
            return self.adapter_conformance_contract()
        return super().inspect_machine(surface)


__all__ = ["AASMEngine", "default_profile_registry"]
