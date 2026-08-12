# Thin LangGraph Adapter

AASM v0.29.0 adds an optional LangGraph adapter that places the existing AASM authority, evidence, obligation, effect, conflict, replay, and recovery machinery underneath an existing graph.

It is intentionally an adapter—not a replacement graph runtime.

## Authority boundary

```text
LangGraph application
  owns graph topology, node execution, routing, interrupts, and checkpoints
        ↓ lifecycle signals
LangGraphAdapter
  maps selected activity into supported AASM records
        ↓
public AASM API
        ↓
authoritative event/reducer runtime
        ↓
Memory / SQLite / PostgreSQL
```

The adapter never writes AASM snapshots or tables directly. It does not store AASM machine truth inside LangGraph state or checkpoint metadata. It does not add a second scheduler, lease system, effect ledger, or event store.

## Installation

```bash
pip install 'aasm-runtime[langgraph]'
```

The core package has no mandatory LangGraph dependency. Importing `aasm` or `aasm.integrations.langgraph` works without LangGraph installed. A real LangGraph import occurs only when a real graph or `Command` conversion is requested.

## Identity mapping

LangGraph persistence identifies a continuing execution with `configurable.thread_id`. AASM derives a deterministic machine ID from:

```text
adapter identity
namespace
thread_id
binding scope
optional run_id
```

Thread scope is the default:

```python
adapter = LangGraphAdapter(namespace="customer-support")
engine, binding = adapter.bind(
    {"configurable": {"thread_id": "ticket-482"}}
)
```

Run scope separates individual attempts under the same thread:

```python
adapter = LangGraphAdapter(
    namespace="customer-support",
    binding_scope="RUN",
)
engine, binding = adapter.bind(
    {
        "configurable": {
            "thread_id": "ticket-482",
            "run_id": "attempt-3",
        }
    }
)
```

Binding is idempotent. A deterministic machine ID that already belongs to a non-adapter machine is rejected rather than silently adopted.

## Wrap existing nodes

```python
from aasm import LangGraphAdapter

adapter = LangGraphAdapter(namespace="example")

def search(state, config=None):
    return {"documents": ["result"]}

wrapped_search = adapter.wrap_node("search", search)
```

The wrapper:

1. binds the LangGraph thread/run to one AASM machine;
2. registers one invocation obligation;
3. marks the obligation in progress;
4. calls the original node;
5. records output evidence and commits the obligation;
6. returns the exact original node result.

Synchronous and asynchronous nodes are supported. `RunnableConfig` and runtime context are forwarded only when the original callable accepts them. A returned LangGraph `Command` is not replaced or reinterpreted; its dynamic route is only recorded as provenance.

## Map selected decisions and evidence

The adapter does not serialize the whole framework object model into AASM. Applications explicitly map the choices that carry authority.

```python
from aasm import LangGraphNodePolicy

policy = LangGraphNodePolicy(
    decision_mapper=lambda state, output: [
        {
            "decision_id": "D-retrieval-mode",
            "subject": "retrieval.mode",
            "value": output["mode"],
        }
    ],
    evidence_mapper=lambda state, output: [
        {
            "statement": "retrieval result validated",
            "evidence_type": "retrieval_validation",
            "metadata": {"count": len(output["documents"])},
        }
    ],
)

graph.add_node("retrieve", adapter.wrap_node("retrieve", retrieve, policy=policy))
```

Mapped decisions enter the existing AASM calculus. Mapped evidence enters the existing evidence ledger with producer and invocation provenance.

## External effects

An effect must be authorized through the existing AASM effect ledger before the application performs it:

```python
record = adapter.authorize_effect(
    engine,
    effect_type="send-email",
    payload={"recipient": "person@example.com"},
    idempotency_key="ticket-482-resolution-email",
)
```

The caller still owns the actual external implementation. AASM owns authorization, idempotency identity, retry safety, and outcome reconciliation.

## Contradiction and learned no-good

```python
result = adapter.record_conflict(
    engine,
    statement="schema v2 violates compatibility",
    implicated_decision_ids=["D-schema-v2"],
)
```

The adapter uses the ordinary AASM path:

```text
contradiction evidence
  → conflict
  → validated explanation
  → learned SOFT no-good
  → projection certificate
  → independent verification
  → HARD promotion
  → causal backjump
```

Unrelated active decisions remain active. Reconstructing the same failed decision combination is blocked by the learned hard constraint.

## Recovery directives

The supported adapter actions are:

```text
CONTINUE
REPAIR
BACKJUMP
PAUSE
RESTART
FORK
```

`BACKJUMP`, `RESTART`, and `FORK` call the existing AASM recovery operations. `PAUSE` deliberately does not replace LangGraph checkpoint control: node code must use LangGraph's interrupt mechanism, while AASM records why the pause is authoritative.

A recovery may be converted to a LangGraph `Command` when `goto` or state update routing is appropriate:

```python
recovery = adapter.recover(
    engine,
    "REPAIR",
    reason="rebuild invalidated schema region",
    target="repair_schema",
    update={"repair_required": True},
)
return recovery.to_langgraph_command()
```

Do not combine a dynamic `Command(goto=...)` route with a conflicting static edge.

## Inspection

Python:

```python
report = adapter.integration_report(engine)
```

CLI:

```bash
aasm langgraph-binding ticket-482 \
  --namespace customer-support \
  --store runs.db

aasm inspect MACHINE_ID \
  --store runs.db \
  --surface langgraph
```

HTTP:

```text
GET /v1/machines/{machine_id}/inspect/langgraph
GET /v1/machines/{machine_id}/inspect/integrations
```

The Control Center includes an Adapted Run panel showing the binding, node lifecycle, recovery activity, and the explicit authority split.

## Controlled comparison

Run:

```bash
python examples/langgraph_adoption.py
```

The example executes the same graph topology ordinarily and with AASM underneath it. The governed run demonstrates:

- failed-assumption identification;
- unrelated decision preservation;
- certified learned-constraint reuse;
- causal backjump target;
- exact replay;
- visible node and recovery provenance.

## Non-goals

The adapter does not:

- replace `StateGraph` or compiled graph execution;
- replace LangGraph persistence or interrupts;
- convert every state key into an AASM decision;
- make checkpoint state authoritative AASM truth;
- create framework-private AASM tables or snapshots;
- require Planner/Builder role topology;
- prove arbitrary node output or external evidence true.

## Version boundary

```text
package/runtime:    aasm-runtime 0.29.0
adoption contract:  aasm.adoption.v1 / 0.5.0
LangGraph adapter:  aasm.langgraph.v1 / 0.1.0
remote protocol:    aasm.remote.v1 / 0.19.0
```
