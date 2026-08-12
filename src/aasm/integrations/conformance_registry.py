from __future__ import annotations

"""Built-in adapter conformance driver registry."""

from typing import Any, Sequence

from .conformance import AdapterConformanceKit, AdapterConformanceReport
from .langgraph import LANGGRAPH_ADAPTER_ID
from .langgraph_conformance import LangGraphConformanceDriver


BUILTIN_CONFORMANCE_DRIVERS = {
    "langgraph": LangGraphConformanceDriver,
    LANGGRAPH_ADAPTER_ID: LangGraphConformanceDriver,
}


def list_conformance_drivers() -> list[dict[str, Any]]:
    seen: set[type[Any]] = set()
    rows: list[dict[str, Any]] = []
    for key in sorted(BUILTIN_CONFORMANCE_DRIVERS):
        driver_type = BUILTIN_CONFORMANCE_DRIVERS[key]
        if driver_type in seen:
            continue
        seen.add(driver_type)
        declaration = driver_type().capability_declaration()
        rows.append(
            {
                "adapter_id": declaration.adapter_id,
                "adapter_version": declaration.adapter_version,
                "driver_id": declaration.driver_id,
                "driver_version": declaration.driver_version,
                "aliases": sorted(
                    alias
                    for alias, candidate in BUILTIN_CONFORMANCE_DRIVERS.items()
                    if candidate is driver_type
                ),
                "scenarios": dict(declaration.scenarios),
            }
        )
    return rows


def get_conformance_driver(adapter_id: str):
    try:
        return BUILTIN_CONFORMANCE_DRIVERS[str(adapter_id)]()
    except KeyError:
        raise KeyError(
            f"unknown conformance adapter {adapter_id!r}; "
            f"available={sorted(BUILTIN_CONFORMANCE_DRIVERS)}"
        ) from None


def run_adapter_conformance(
    adapter_id: str = "langgraph",
    *,
    scenarios: Sequence[str] | None = None,
    engine_class: type[Any] | None = None,
) -> AdapterConformanceReport:
    kit = AdapterConformanceKit(engine_class=engine_class)
    return kit.run(get_conformance_driver(adapter_id), scenarios=scenarios)


__all__ = [
    "BUILTIN_CONFORMANCE_DRIVERS",
    "list_conformance_drivers",
    "get_conformance_driver",
    "run_adapter_conformance",
]
