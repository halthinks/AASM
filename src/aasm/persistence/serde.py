from __future__ import annotations

from dataclasses import asdict
from typing import Any

from ..calculus import default_calculus_state, normalize_calculus_state
from ..model import Event, MachineSnapshot, ProblemSpec


def problem_to_dict(problem: ProblemSpec) -> dict[str, Any]:
    return asdict(problem)


def problem_from_dict(data: dict[str, Any]) -> ProblemSpec:
    return ProblemSpec(**data)


def snapshot_to_dict(snapshot: MachineSnapshot) -> dict[str, Any]:
    return asdict(snapshot)


def snapshot_from_dict(data: dict[str, Any]) -> MachineSnapshot:
    payload = dict(data)
    payload["problem"] = problem_from_dict(payload["problem"])
    payload["calculus"] = normalize_calculus_state(payload.get("calculus") or default_calculus_state())
    return MachineSnapshot(**payload)


def event_to_dict(event: Event) -> dict[str, Any]:
    return asdict(event)


def event_from_dict(data: dict[str, Any]) -> Event:
    return Event(**data)
