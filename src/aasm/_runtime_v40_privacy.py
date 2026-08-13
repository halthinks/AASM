from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from ._runtime_v40_memory import HierarchicalMemoryRuntimeMixin
from .hierarchical_memory import ContextProjectionRequest, project_context


class PrincipalBoundMemoryRuntimeMixin(HierarchicalMemoryRuntimeMixin):
    """Principal binding for AGENT/USER memory without changing scope semantics."""

    def propose_memory_operation(self, operation: str, **kwargs):
        privacy = str(kwargs.get("privacy_level", "AGENT"))
        metadata = deepcopy(dict(kwargs.get("metadata") or {}))
        if privacy in {"AGENT", "USER"} and not str(metadata.get("privacy_principal_id") or ""):
            raise ValueError(f"{privacy} memory requires metadata.privacy_principal_id")
        kwargs["metadata"] = metadata
        return super().propose_memory_operation(operation, **kwargs)

    def context_projection(self, request: ContextProjectionRequest | Mapping[str, Any]) -> dict[str, Any]:
        request = request if isinstance(request, ContextProjectionRequest) else ContextProjectionRequest(**deepcopy(dict(request)))
        calculus = self._begin_calculus()
        signals = self._memory_semantic_signals()
        memory = self.hierarchical_memory_report(as_of=request.as_of)
        if not memory["valid"]:
            raise RuntimeError(f"invalid hierarchical memory projection: {memory['issues']}")
        principal_id = str(request.metadata.get("principal_id") or "")
        filtered = deepcopy(memory)
        filtered["memories"] = {
            memory_id: entry
            for memory_id, entry in memory["memories"].items()
            if entry["memory"]["privacy_level"] not in {"AGENT", "USER"}
            or (principal_id and principal_id == str((entry["memory"].get("metadata") or {}).get("privacy_principal_id") or ""))
        }
        return project_context(filtered, self.reasoning_report(), calculus, signals, calculus["scope_state"], request)


__all__ = ["PrincipalBoundMemoryRuntimeMixin"]
