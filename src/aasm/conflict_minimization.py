from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from itertools import combinations
from typing import Any, Protocol


@dataclass
class ConflictMinimizationResult:
    conflict_id: str
    explanation_id: str
    mode: str
    original_literals: list[dict[str, Any]]
    minimized_literals: list[dict[str, Any]]
    removed_literals: list[dict[str, Any]]
    oracle_calls: int
    minimality: str
    exhausted: bool
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ConflictOracle(Protocol):
    def conflicts(self, assumption_literals: list[dict[str, Any]]) -> bool: ...


def minimize_conflict_core(
    conflict_id: str,
    explanation_id: str,
    literals: list[dict[str, Any]],
    oracle: ConflictOracle,
    *,
    mode: str = "GREEDY_IRREDUCIBLE",
    max_calls: int = 256,
) -> ConflictMinimizationResult:
    if mode not in {"NONE", "GREEDY_IRREDUCIBLE", "EXACT_BOUNDED"}:
        raise ValueError(f"unknown minimization mode: {mode}")
    if not literals:
        raise ValueError("conflict minimization requires at least one literal")
    if max_calls <= 0:
        raise ValueError("max_calls must be positive")

    original = deepcopy(literals)
    if mode == "NONE":
        return ConflictMinimizationResult(
            conflict_id=conflict_id,
            explanation_id=explanation_id,
            mode=mode,
            original_literals=original,
            minimized_literals=deepcopy(original),
            removed_literals=[],
            oracle_calls=0,
            minimality="NONE",
            exhausted=True,
        )

    calls = 0
    if mode == "GREEDY_IRREDUCIBLE":
        current = deepcopy(original)
        index = 0
        while index < len(current):
            if calls >= max_calls:
                break
            candidate = current[:index] + current[index + 1 :]
            if not candidate:
                index += 1
                continue
            calls += 1
            if oracle.conflicts(deepcopy(candidate)):
                current = candidate
            else:
                index += 1
        removed = [literal for literal in original if literal not in current]
        return ConflictMinimizationResult(
            conflict_id=conflict_id,
            explanation_id=explanation_id,
            mode=mode,
            original_literals=original,
            minimized_literals=current,
            removed_literals=removed,
            oracle_calls=calls,
            minimality="IRREDUCIBLE" if calls < max_calls else "PARTIAL",
            exhausted=calls < max_calls,
        )

    best = deepcopy(original)
    exhausted = True
    for size in range(1, len(original) + 1):
        found = None
        for subset in combinations(original, size):
            if calls >= max_calls:
                exhausted = False
                break
            calls += 1
            candidate = [deepcopy(literal) for literal in subset]
            if oracle.conflicts(candidate):
                found = candidate
                break
        if found is not None:
            best = found
            break
        if not exhausted:
            break
    removed = [literal for literal in original if literal not in best]
    return ConflictMinimizationResult(
        conflict_id=conflict_id,
        explanation_id=explanation_id,
        mode=mode,
        original_literals=original,
        minimized_literals=best,
        removed_literals=removed,
        oracle_calls=calls,
        minimality="PROVEN_MINIMAL" if exhausted else "PARTIAL",
        exhausted=exhausted,
    )
