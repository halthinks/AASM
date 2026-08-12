from __future__ import annotations

from copy import deepcopy
from typing import Any

from .integrations.langgraph import LANGGRAPH_ADAPTER_ID, LangGraphAdapter
from .runtime_v25 import AASMEngine as V25Engine, default_profile_registry


class AASMEngine(V25Engine):
    """v0.29 runtime: framework integration inspection over the same authority path."""

    def langgraph_report(self) -> dict[str, Any]:
        adapter = LangGraphAdapter(
            store=self.store,
            engine_class=type(self),
            namespace="inspection",
        )
        return adapter.integration_report(self)

    def integration_report(self) -> dict[str, Any]:
        event_types = {event.event_type for event in self.store.load_events(self.snapshot.machine_id)}
        integrations: dict[str, Any] = {}
        if "langgraph_run_bound" in event_types:
            integrations[LANGGRAPH_ADAPTER_ID] = self.langgraph_report()
        return {
            "schema_version": 1,
            "machine_id": self.snapshot.machine_id,
            "authority": "AASM_EVENT_HISTORY",
            "integrations": integrations,
            "integration_count": len(integrations),
        }

    def inspect_machine(self, surface: str = "summary") -> Any:
        if surface == "integrations":
            return deepcopy(self.integration_report())
        if surface == "langgraph":
            return deepcopy(self.langgraph_report())
        return super().inspect_machine(surface)


__all__ = ["AASMEngine", "default_profile_registry"]
