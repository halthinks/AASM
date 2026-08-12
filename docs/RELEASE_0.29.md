# AASM v0.29.0 — Thin LangGraph Adapter

AASM v0.29.0 is the first framework-adoption release. An existing LangGraph application keeps its graph, nodes, routes, interrupts, checkpoint data, and domain state while AASM supplies durable authority, obligations, evidence, effect authorization, conflict learning, replay, and recovery underneath it.

## Delivered boundary

```text
LangGraph graph and checkpoint runtime
        ↓ explicit adapter hooks
AASM public adoption surface
        ↓
existing event/reducer authority path
        ↓
existing Memory / SQLite / PostgreSQL stores
```

There is no second runtime, scheduler, lease system, effect ledger, event store, or framework-private AASM truth.

## Adapter contract

- deterministic thread/run to AASM machine identity;
- idempotent bind or resume;
- collision rejection for unrelated existing machines;
- explicit checkpoint-authority versus machine-authority declaration;
- sync and async node wrappers that return original outputs unchanged;
- selected decision, obligation, evidence, and effect mappings;
- `CONTINUE | REPAIR | BACKJUMP | PAUSE | RESTART | FORK` directives;
- dynamic LangGraph `Command` preservation and optional conversion;
- no mandatory LangGraph dependency in the core package.

## Conflict and recovery demonstration

The controlled comparison runs the same graph topology ordinarily and with AASM. The governed run identifies the failed assumption, preserves unrelated cache work, certifies and promotes a learned no-good, backjumps to the causal decision, blocks the same failed value on reuse, and verifies exact replay.

## Adoption surfaces

```text
src/aasm/integrations/langgraph.py
src/aasm/runtime_v29.py
src/aasm/cli_v29.py
src/aasm/server_v29.py
src/aasm/control_center_v29.py
schemas/langgraph-binding.schema.json
schemas/langgraph-recovery.schema.json
examples/langgraph_adoption.py
docs/LANGGRAPH_ADAPTER.md
tests/test_v29_langgraph_adapter.py
```

CLI:

```bash
aasm langgraph-binding THREAD_ID --namespace NAME --store runs.db
aasm inspect MACHINE_ID --store runs.db --surface langgraph
```

HTTP:

```text
GET /v1/machines/{machine_id}/inspect/langgraph
GET /v1/machines/{machine_id}/inspect/integrations
```

## Compatibility boundary

```text
package/runtime:    aasm-runtime 0.29.0
adoption contract:  aasm.adoption.v1 / 0.5.0
LangGraph adapter:  aasm.langgraph.v1 / 0.1.0
remote protocol:    aasm.remote.v1 / 0.19.0
```

The next release is **v0.30.0 — Adapter Conformance Kit**.
