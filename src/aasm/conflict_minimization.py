from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from itertools import combinations
import json
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


def _literal_key(literal: dict[str, Any]) -> str:
    return json.dumps(literal, sort_keys=True, separators=(",", ":"), default=str)


def _canonicalize_literals(
    literals: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], int]:
    seen: set[str] = set()
    canonical: list[dict[str, Any]] = []
    duplicate_count = 0
    for literal in literals:
        key = _literal_key(literal)
        if key in seen:
            duplicate_count += 1
            continue
        seen.add(key)
        canonical.append(deepcopy(literal))
    return canonical, duplicate_count


def minimize_conflict_core(
    conflict_id: str,
    explanation_id: str,
    literals: list[dict[str, Any]],
    oracle: ConflictOracle,
    *,
    mode: str = "GREEDY_IRREDUCIBLE",
    max_calls: int = 256,
) -> ConflictMinimizationResult:
    """Minimize a conflict core without overstating what the oracle proved.

    The complete input is checked first. Exact mode includes the empty subset,
    allowing unconditional/root conflicts to be represented. Duplicate
    literals are removed deterministically before search so call budgets and
    minimality claims refer to the semantic input rather than repeated rows.
    """

    if mode not in {"NONE", "GREEDY_IRREDUCIBLE", "EXACT_BOUNDED"}:
        raise ValueError(f"unknown minimization mode: {mode}")
    if max_calls <= 0:
        raise ValueError("max_calls must be positive")

    supplied = deepcopy(literals)
    original, duplicate_count = _canonicalize_literals(supplied)
    metadata: dict[str, Any] = {
        "duplicate_count": duplicate_count,
        "input_literal_count": len(supplied),
        "canonical_literal_count": len(original),
        "input_validated": False,
        "root_conflict": False,
        "budget_exhausted": False,
    }

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
            metadata=metadata,
        )

    calls = 1
    if not oracle.conflicts(deepcopy(original)):
        raise ValueError("the supplied literal set does not reproduce the conflict")
    metadata["input_validated"] = True

    if calls >= max_calls:
        metadata["budget_exhausted"] = True
        return ConflictMinimizationResult(
            conflict_id=conflict_id,
            explanation_id=explanation_id,
            mode=mode,
            original_literals=original,
            minimized_literals=deepcopy(original),
            removed_literals=[],
            oracle_calls=calls,
            minimality="PARTIAL",
            exhausted=False,
            metadata=metadata,
        )

    calls += 1
    if oracle.conflicts([]):
        metadata["root_conflict"] = True
        return ConflictMinimizationResult(
            conflict_id=conflict_id,
            explanation_id=explanation_id,
            mode=mode,
            original_literals=original,
            minimized_literals=[],
            removed_literals=deepcopy(original),
            oracle_calls=calls,
            minimality="PROVEN_MINIMAL",
            exhausted=True,
            metadata=metadata,
        )

    if not original:
        raise ValueError("the supplied literal set does not reproduce the conflict")

    if mode == "GREEDY_IRREDUCIBLE":
        current = deepcopy(original)
        index = 0
        completed = True
        while index < len(current):
            if calls >= max_calls:
                completed = False
                metadata["budget_exhausted"] = True
                break
            candidate = current[:index] + current[index + 1 :]
            calls += 1
            if oracle.conflicts(deepcopy(candidate)):
                current = candidate
            else:
                index += 1
        current_keys = {_literal_key(literal) for literal in current}
        removed = [literal for literal in original if _literal_key(literal) not in current_keys]
        return ConflictMinimizationResult(
            conflict_id=conflict_id,
            explanation_id=explanation_id,
            mode=mode,
            original_literals=original,
            minimized_literals=current,
            removed_literals=removed,
            oracle_calls=calls,
            minimality="IRREDUCIBLE" if completed else "PARTIAL",
            exhausted=completed,
            metadata=metadata,
        )

    best = deepcopy(original)
    completed = True
    found = False
    for size in range(1, len(original)):
        for subset in combinations(original, size):
            if calls >= max_calls:
                completed = False
                metadata["budget_exhausted"] = True
                break
            calls += 1
            candidate = [deepcopy(literal) for literal in subset]
            if oracle.conflicts(candidate):
                best = candidate
                found = True
                break
        if found or not completed:
            break

    best_keys = {_literal_key(literal) for literal in best}
    removed = [literal for literal in original if _literal_key(literal) not in best_keys]
    return ConflictMinimizationResult(
        conflict_id=conflict_id,
        explanation_id=explanation_id,
        mode=mode,
        original_literals=original,
        minimized_literals=best,
        removed_literals=removed,
        oracle_calls=calls,
        minimality="PROVEN_MINIMAL" if completed else "PARTIAL",
        exhausted=completed,
        metadata=metadata,
    )
