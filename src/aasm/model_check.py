from __future__ import annotations

from dataclasses import dataclass, field, asdict
from collections import deque
from typing import Any

from .definitions import MachineDefinition


@dataclass
class ModelCheckIssue:
    code: str
    severity: str
    message: str
    states: list[str] = field(default_factory=list)


@dataclass
class ModelCheckReport:
    machine: str
    valid: bool
    states: list[str]
    reachable_states: list[str]
    unreachable_states: list[str]
    dead_end_states: list[str]
    trapped_states: list[str]
    issues: list[ModelCheckIssue]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def check_machine(definition: MachineDefinition) -> ModelCheckReport:
    issues: list[ModelCheckIssue] = []
    declared = set(definition.transitions)
    targets = {target for values in definition.transitions.values() for target in values}
    states = set(definition.states)

    if definition.start_state not in states:
        issues.append(ModelCheckIssue("missing_start_state", "error", f"Start state {definition.start_state} is not declared", [definition.start_state]))

    missing_targets = sorted(targets - declared - set(definition.terminal_states))
    if missing_targets:
        issues.append(ModelCheckIssue("undefined_transition_target", "error", "Transitions target undefined states", missing_targets))

    terminal_with_edges = sorted(state for state in definition.terminal_states if definition.allowed(state))
    if terminal_with_edges:
        issues.append(ModelCheckIssue("terminal_has_outgoing", "error", "Terminal states must not have outgoing transitions", terminal_with_edges))

    reachable: set[str] = set()
    if definition.start_state in states:
        queue = deque([definition.start_state])
        while queue:
            state = queue.popleft()
            if state in reachable:
                continue
            reachable.add(state)
            for target in definition.allowed(state):
                if target in states and target not in reachable:
                    queue.append(target)

    unreachable = sorted(states - reachable)
    if unreachable:
        issues.append(ModelCheckIssue("unreachable_state", "warning", "States cannot be reached from the start state", unreachable))

    dead_ends = sorted(state for state in reachable if state not in definition.terminal_states and not definition.allowed(state))
    if dead_ends:
        issues.append(ModelCheckIssue("nonterminal_dead_end", "error", "Reachable non-terminal states have no outgoing transition", dead_ends))

    reverse: dict[str, set[str]] = {state: set() for state in states}
    for source, next_states in definition.transitions.items():
        for target in next_states:
            if target in states:
                reverse.setdefault(target, set()).add(source)
    can_terminate: set[str] = set()
    queue = deque(state for state in definition.terminal_states if state in states)
    while queue:
        state = queue.popleft()
        if state in can_terminate:
            continue
        can_terminate.add(state)
        queue.extend(reverse.get(state, set()) - can_terminate)

    trapped = sorted(reachable - can_terminate)
    if trapped:
        issues.append(ModelCheckIssue("cannot_reach_terminal", "error", "Reachable states have no path to any terminal state", trapped))

    if not (reachable & set(definition.terminal_states)):
        issues.append(ModelCheckIssue("terminal_unreachable", "error", "No terminal state is reachable from the start state", sorted(definition.terminal_states)))

    valid = not any(issue.severity == "error" for issue in issues)
    return ModelCheckReport(
        machine=definition.name,
        valid=valid,
        states=sorted(states),
        reachable_states=sorted(reachable),
        unreachable_states=unreachable,
        dead_end_states=dead_ends,
        trapped_states=trapped,
        issues=issues,
    )
