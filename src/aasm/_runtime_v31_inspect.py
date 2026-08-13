from __future__ import annotations

from copy import deepcopy
from typing import Any


class ScopeInspectionMixin:
    def inspect_machine(self, surface: str = "summary") -> Any:
        if surface in {"scopes", "scope-hierarchy"}:
            return deepcopy(self.scope_report())
        return super().inspect_machine(surface)


__all__ = ["ScopeInspectionMixin"]
