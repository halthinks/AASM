from __future__ import annotations

from copy import deepcopy
from typing import Any

from ._scopes_model import *

def scoped_subject_key(scope_id: str, subject: str) -> str:
    return str(subject) if scope_id == ROOT_SCOPE_ID else f"{scope_id}::{subject}"


def scope_parent_map(scope_state: dict[str, Any]) -> dict[str, str | None]:
    state = normalize_scope_state(scope_state)
    return {
        scope_id: record.get("parent_scope_id")
        for scope_id, record in state["records"].items()
    }


def scope_ancestors(
    scope_state: dict[str, Any],
    scope_id: str,
    *,
    include_self: bool = True,
) -> list[str]:
    state = normalize_scope_state(scope_state)
    if scope_id not in state["records"]:
        raise KeyError(scope_id)
    chain: list[str] = []
    current: str | None = scope_id
    seen: set[str] = set()
    while current is not None:
        if current in seen:
            raise ValueError(f"scope hierarchy cycle at {current}")
        seen.add(current)
        chain.append(current)
        current = state["records"][current].get("parent_scope_id")
    chain.reverse()
    return chain if include_self else chain[:-1]


def scope_descendants(
    scope_state: dict[str, Any],
    scope_id: str,
    *,
    include_self: bool = True,
) -> set[str]:
    state = normalize_scope_state(scope_state)
    if scope_id not in state["records"]:
        raise KeyError(scope_id)
    children: dict[str, set[str]] = {item: set() for item in state["records"]}
    for child_id, record in state["records"].items():
        parent = record.get("parent_scope_id")
        if parent is not None:
            children.setdefault(str(parent), set()).add(child_id)
    seen: set[str] = {scope_id} if include_self else set()
    todo = [scope_id]
    while todo:
        current = todo.pop()
        for child in sorted(children.get(current, set())):
            if child not in seen:
                seen.add(child)
                todo.append(child)
    return seen


def scope_depth(scope_state: dict[str, Any], scope_id: str) -> int:
    return max(0, len(scope_ancestors(scope_state, scope_id)) - 1)


def _dependency_scope_edges(scope_state: dict[str, Any]) -> dict[str, set[str]]:
    state = normalize_scope_state(scope_state)
    edges: dict[str, set[str]] = {scope_id: set() for scope_id in state["records"]}
    for dependency in state["dependencies"].values():
        edges.setdefault(str(dependency["upstream_scope_id"]), set()).add(
            str(dependency["downstream_scope_id"])
        )
    return edges


def dependency_reachable(
    scope_state: dict[str, Any],
    upstream_scope_id: str,
    downstream_scope_id: str,
) -> bool:
    if upstream_scope_id == downstream_scope_id:
        return True
    edges = _dependency_scope_edges(scope_state)
    seen = {upstream_scope_id}
    todo = [upstream_scope_id]
    while todo:
        current = todo.pop()
        for child in edges.get(current, set()):
            if child == downstream_scope_id:
                return True
            if child not in seen:
                seen.add(child)
                todo.append(child)
    return False


def inheritance_chain(scope_state: dict[str, Any], scope_id: str) -> list[str]:
    state = normalize_scope_state(scope_state)
    chain = scope_ancestors(state, scope_id)
    if scope_id == ROOT_SCOPE_ID:
        return chain
    start = 0
    for index, current in enumerate(chain[1:], start=1):
        if state["records"][current].get("inheritance") == "ISOLATED":
            start = index
    return chain[start:]


def scope_flow_allowed(
    scope_state: dict[str, Any], source_scope_id: str, target_scope_id: str
) -> bool:
    state = normalize_scope_state(scope_state)
    if source_scope_id == target_scope_id:
        return True
    if source_scope_id in inheritance_chain(state, target_scope_id)[:-1]:
        return True
    return dependency_reachable(state, source_scope_id, target_scope_id)


def _combined_scope_edges(scope_state: dict[str, Any]) -> dict[str, set[str]]:
    state = normalize_scope_state(scope_state)
    edges: dict[str, set[str]] = {scope_id: set() for scope_id in state["records"]}
    for scope_id, record in state["records"].items():
        parent = record.get("parent_scope_id")
        if parent is not None:
            edges.setdefault(str(parent), set()).add(scope_id)
    for dependency in state["dependencies"].values():
        edges.setdefault(str(dependency["upstream_scope_id"]), set()).add(
            str(dependency["downstream_scope_id"])
        )
    return edges


def scope_reachable(
    scope_state: dict[str, Any],
    upstream_scope_id: str,
    downstream_scope_id: str,
) -> bool:
    if upstream_scope_id == downstream_scope_id:
        return True
    edges = _combined_scope_edges(scope_state)
    if upstream_scope_id not in edges or downstream_scope_id not in edges:
        return False
    seen = {upstream_scope_id}
    todo = [upstream_scope_id]
    while todo:
        current = todo.pop()
        for child in edges.get(current, set()):
            if child == downstream_scope_id:
                return True
            if child not in seen:
                seen.add(child)
                todo.append(child)
    return False


def validate_scope_state(scope_state: dict[str, Any]) -> dict[str, Any]:
    state = normalize_scope_state(scope_state)
    records = state["records"]
    for scope_id, raw in records.items():
        record = DecisionScope(**deepcopy(raw))
        if record.scope_id != scope_id:
            raise ValueError(f"scope key mismatch: {scope_id} != {record.scope_id}")
        if scope_id != ROOT_SCOPE_ID and record.parent_scope_id not in records:
            raise ValueError(
                f"scope {scope_id} references unknown parent {record.parent_scope_id}"
            )
    for dependency_id, raw in state["dependencies"].items():
        dependency = ScopeDependency(**deepcopy(raw))
        if dependency.dependency_id != dependency_id:
            raise ValueError(
                f"scope dependency key mismatch: {dependency_id} != {dependency.dependency_id}"
            )
        if dependency.upstream_scope_id not in records:
            raise ValueError(
                f"scope dependency {dependency_id} references unknown upstream scope"
            )
        if dependency.downstream_scope_id not in records:
            raise ValueError(
                f"scope dependency {dependency_id} references unknown downstream scope"
            )

    edges = _combined_scope_edges(state)
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(item: str) -> None:
        if item in visiting:
            raise ValueError(f"scope hierarchy/dependency cycle includes {item}")
        if item in visited:
            return
        visiting.add(item)
        for child in sorted(edges.get(item, set())):
            visit(child)
        visiting.remove(item)
        visited.add(item)

    for scope_id in sorted(records):
        visit(scope_id)
    return state

__all__ = [name for name in globals() if not name.startswith("_")]
