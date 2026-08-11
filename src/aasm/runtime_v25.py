from __future__ import annotations

from copy import deepcopy
from typing import Any

from .observability import (
    causal_graph,
    conflict_timeline,
    decision_graph,
    evidence_graph,
    fairness_debt,
    obligation_graph,
    observability_report,
    package_history,
)
from .research_profile import ResearchProfileRegistry
from .runtime_v24 import AASMEngine as V24Engine


class AASMEngine(V24Engine):
    """v0.25+ runtime: domain-neutral machine observability and inspection."""

    def _refresh_observability_state(self) -> None:
        refresh = getattr(self, "_refresh_canonical_snapshot", None)
        if refresh is not None:
            refresh()

    def observability_report(self) -> dict[str, Any]:
        self._refresh_observability_state()
        return observability_report(self.snapshot, self.events)

    def decision_graph_view(self) -> dict[str, Any]:
        self._refresh_observability_state()
        return decision_graph(self.snapshot).to_dict()

    def obligation_graph_view(self) -> dict[str, Any]:
        self._refresh_observability_state()
        return obligation_graph(self.snapshot).to_dict()

    def evidence_graph_view(self) -> dict[str, Any]:
        self._refresh_observability_state()
        return evidence_graph(self.snapshot).to_dict()

    def causal_graph_view(self) -> dict[str, Any]:
        self._refresh_observability_state()
        return causal_graph(self.snapshot).to_dict()

    def conflict_timeline(self) -> list[dict[str, Any]]:
        self._refresh_observability_state()
        return conflict_timeline(self.snapshot)

    def fairness_debt(self) -> list[dict[str, Any]]:
        self._refresh_observability_state()
        return fairness_debt(self.snapshot)

    def package_history(self) -> dict[str, Any]:
        self._refresh_observability_state()
        return package_history(self.snapshot)

    def inspect_machine(self, surface: str = "summary") -> Any:
        surfaces = {
            "summary": self.observability_report,
            "decisions": self.decision_graph_view,
            "obligations": self.obligation_graph_view,
            "evidence": self.evidence_graph_view,
            "causal": self.causal_graph_view,
            "conflicts": self.conflict_timeline,
            "fairness": self.fairness_debt,
            "packages": self.package_history,
            "candidates": self.backend_report,
            "assurance": self.assurance_report,
            "calculus": self.calculus_report,
            "profile": self.profile_report,
        }
        try:
            return deepcopy(surfaces[surface]())
        except KeyError as exc:
            raise ValueError(
                f"unknown inspection surface: {surface}; choose from {sorted(surfaces)}"
            ) from exc


def default_profile_registry(*, discover: bool = False) -> ResearchProfileRegistry:
    """Return the canonical registry including the adoption-grade hero profile."""

    registry = ResearchProfileRegistry(include_builtins=True)
    if discover:
        registry.discover()
    return registry
