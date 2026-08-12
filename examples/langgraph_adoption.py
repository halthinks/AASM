from __future__ import annotations

"""Run the same LangGraph topology ordinarily and with AASM underneath it.

Install the optional dependency first:

    pip install 'aasm-runtime[langgraph]'
"""

import json
from typing import TypedDict

from aasm import LangGraphAdapter, LangGraphNodePolicy, MemoryStore


class State(TypedDict, total=False):
    schema: str
    cache: str
    verification: str


def select_schema(_state: State) -> State:
    return {"schema": "v2"}


def select_cache(_state: State) -> State:
    return {"cache": "memory"}


def ordinary_verify(state: State) -> State:
    return {
        "verification": "conflict" if state.get("schema") == "v2" else "pass"
    }


def build_graph(*, adapter: LangGraphAdapter | None = None):
    try:
        from langgraph.graph import END, START, StateGraph
    except ImportError as exc:
        raise SystemExit(
            "LangGraph is not installed. Install aasm-runtime[langgraph]."
        ) from exc

    graph = StateGraph(State)
    schema_node = select_schema
    cache_node = select_cache
    verify_node = ordinary_verify

    if adapter is not None:
        schema_node = adapter.wrap_node(
            "select_schema",
            select_schema,
            policy=LangGraphNodePolicy(
                decision_mapper=lambda _state, _output: [
                    {
                        "decision_id": "D-schema-v2",
                        "subject": "schema",
                        "value": "v2",
                    }
                ]
            ),
        )
        cache_node = adapter.wrap_node(
            "select_cache",
            select_cache,
            policy=LangGraphNodePolicy(
                decision_mapper=lambda _state, _output: [
                    {
                        "decision_id": "D-cache-memory",
                        "subject": "cache",
                        "value": "memory",
                    }
                ]
            ),
        )

        def governed_verify(state: State, config=None) -> State:
            output = ordinary_verify(state)
            if output["verification"] == "conflict":
                engine, _ = adapter.bind(config)
                adapter.record_conflict(
                    engine,
                    statement="schema v2 violates the controlled compatibility fixture",
                    implicated_decision_ids=["D-schema-v2"],
                )
            return output

        verify_node = adapter.wrap_node("verify", governed_verify)

    graph.add_node("select_schema", schema_node)
    graph.add_node("select_cache", cache_node)
    graph.add_node("verify", verify_node)
    graph.add_edge(START, "select_schema")
    graph.add_edge("select_schema", "select_cache")
    graph.add_edge("select_cache", "verify")
    graph.add_edge("verify", END)
    return graph.compile()


def main() -> None:
    ordinary = build_graph().invoke({}, {"configurable": {"thread_id": "ordinary"}})

    store = MemoryStore()
    adapter = LangGraphAdapter(store=store, namespace="comparison")
    governed = build_graph(adapter=adapter).invoke(
        {}, {"configurable": {"thread_id": "governed"}}
    )
    engine, binding = adapter.bind(
        {"configurable": {"thread_id": "governed"}}
    )
    calculus = engine.calculus_report()
    learned_id = next(iter(calculus["constraints"]))

    blocked_reuse = False
    adapter.record_decision(
        engine,
        decision_id="D-schema-v2-repeat",
        subject="schema",
        value="v2",
        activate=False,
    )
    try:
        engine.activate_decision("D-schema-v2-repeat")
    except ValueError:
        blocked_reuse = True

    result = {
        "ordinary_output": ordinary,
        "governed_output": governed,
        "binding": binding.to_dict(),
        "failed_assumption": "D-schema-v2",
        "unrelated_cache_preserved": calculus["decisions"]["D-cache-memory"]["status"]
        == "ACTIVE",
        "learned_constraint": calculus["constraints"][learned_id],
        "failed_combination_blocked_on_reuse": blocked_reuse,
        "backjump_target": next(iter(calculus["conflicts"].values()))["backjump"][
            "pivot_decision_id"
        ],
        "exact_replay": engine.replay().canonical_hash()
        == engine.snapshot.canonical_hash(),
        "provenance": adapter.integration_report(engine),
    }
    print(json.dumps(result, indent=2, sort_keys=True, default=str))


if __name__ == "__main__":
    main()
