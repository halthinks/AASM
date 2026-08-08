from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
import tomllib
from typing import Any, Iterable

from .model import MachineState


@dataclass(frozen=True)
class MachineDefinition:
    """Declarative state-machine definition compiled into AASM runtime semantics."""

    name: str
    start_state: str
    terminal_states: frozenset[str]
    transitions: dict[str, frozenset[str]]
    description: str = ""
    metadata: dict[str, Any] = field(default_factory=dict, compare=False)
    schema_version: int = 1

    def allowed(self, state: str) -> frozenset[str]:
        return self.transitions.get(state, frozenset())

    @property
    def states(self) -> frozenset[str]:
        values = set(self.transitions)
        for targets in self.transitions.values():
            values.update(targets)
        values.add(self.start_state)
        values.update(self.terminal_states)
        return frozenset(values)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "name": self.name,
            "description": self.description,
            "start_state": self.start_state,
            "terminal_states": sorted(self.terminal_states),
            "transitions": {key: sorted(value) for key, value in sorted(self.transitions.items())},
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MachineDefinition":
        transitions = data.get("transitions", {})
        if not isinstance(transitions, dict):
            raise ValueError("transitions must be an object mapping states to target-state arrays")
        normalized: dict[str, frozenset[str]] = {}
        for state, targets in transitions.items():
            if not isinstance(state, str) or not state:
                raise ValueError("state names must be non-empty strings")
            if not isinstance(targets, (list, tuple, set, frozenset)):
                raise ValueError(f"transition targets for {state} must be an array")
            normalized[state] = frozenset(str(target) for target in targets)
        return cls(
            name=str(data.get("name") or "unnamed-machine"),
            description=str(data.get("description") or ""),
            start_state=str(data.get("start_state") or "INGEST"),
            terminal_states=frozenset(str(x) for x in data.get("terminal_states", ["COMPLETE", "FAIL"])),
            transitions=normalized,
            metadata=dict(data.get("metadata") or {}),
            schema_version=int(data.get("schema_version", 1)),
        )

    @classmethod
    def load(cls, path: str | Path) -> "MachineDefinition":
        path = Path(path)
        suffix = path.suffix.lower()
        raw = path.read_bytes()
        if suffix == ".json":
            return cls.from_dict(json.loads(raw.decode("utf-8")))
        if suffix in {".toml", ".tml"}:
            return cls.from_dict(tomllib.loads(raw.decode("utf-8")))
        if suffix in {".yaml", ".yml"}:
            try:
                import yaml  # type: ignore
            except ImportError as exc:
                raise RuntimeError("YAML loading is optional; install PyYAML or use JSON/TOML") from exc
            return cls.from_dict(yaml.safe_load(raw.decode("utf-8")))
        raise ValueError(f"Unsupported machine definition format: {suffix}; use .json, .toml, or optional .yaml")


def default_machine_definition() -> MachineDefinition:
    t = {
        MachineState.INGEST.value: {MachineState.FORMALIZE.value, MachineState.PAUSE.value, MachineState.FAIL.value},
        MachineState.FORMALIZE.value: {MachineState.CLASSIFY.value, MachineState.INVESTIGATE.value, MachineState.FAIL.value},
        MachineState.CLASSIFY.value: {MachineState.DECOMPOSE.value, MachineState.PLAN.value, MachineState.FAIL.value},
        MachineState.DECOMPOSE.value: {MachineState.PLAN.value, MachineState.INVESTIGATE.value},
        MachineState.PLAN.value: {MachineState.SELECT.value, MachineState.INVESTIGATE.value, MachineState.PAUSE.value},
        MachineState.SELECT.value: {MachineState.EXECUTE.value, MachineState.PAUSE.value},
        MachineState.EXECUTE.value: {MachineState.OBSERVE.value, MachineState.FAIL.value},
        MachineState.OBSERVE.value: {MachineState.VERIFY.value, MachineState.INVESTIGATE.value},
        MachineState.VERIFY.value: {MachineState.COMMIT.value, MachineState.REPAIR.value, MachineState.BACKTRACK.value, MachineState.INVESTIGATE.value, MachineState.COMPLETE.value, MachineState.FAIL.value},
        MachineState.REPAIR.value: {MachineState.EXECUTE.value, MachineState.VERIFY.value, MachineState.BACKTRACK.value},
        MachineState.BACKTRACK.value: {MachineState.SELECT.value, MachineState.PLAN.value, MachineState.INVESTIGATE.value},
        MachineState.INVESTIGATE.value: {MachineState.FORMALIZE.value, MachineState.PLAN.value, MachineState.SELECT.value, MachineState.VERIFY.value, MachineState.PAUSE.value},
        MachineState.COMMIT.value: {MachineState.SELECT.value, MachineState.PLAN.value, MachineState.COMPLETE.value},
        MachineState.PAUSE.value: {MachineState.PLAN.value, MachineState.SELECT.value, MachineState.FAIL.value},
        MachineState.COMPLETE.value: set(),
        MachineState.FAIL.value: set(),
    }
    return MachineDefinition(
        name="aasm-default",
        description="Default AASM orchestration lifecycle",
        start_state=MachineState.INGEST.value,
        terminal_states=frozenset({MachineState.COMPLETE.value, MachineState.FAIL.value}),
        transitions={k: frozenset(v) for k, v in t.items()},
    )
