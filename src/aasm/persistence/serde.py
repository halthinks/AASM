from __future__ import annotations

from dataclasses import asdict
from typing import Any

from ..assurance import normalize_assurance_state
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
    payload.setdefault("profile_binding", {})
    payload.setdefault("semantic_results", [])
    payload.setdefault(
        "candidate_state",
        {
            "schema_version": 1,
            "requests": {},
            "batches": {},
            "candidates": {},
            "selected_candidate_id": None,
            "activated_candidate_id": None,
            "backend_history": [],
        },
    )
    payload["assurance_state"] = normalize_assurance_state(payload.get("assurance_state"))
    return MachineSnapshot(**payload)


def event_to_dict(event: Event) -> dict[str, Any]:
    return asdict(event)


def event_from_dict(data: dict[str, Any]) -> Event:
    return Event(**data)
