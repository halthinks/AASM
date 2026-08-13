# Runtime/Formal Trace Conformance

AASM v0.32.0 connects production event histories to a versioned formal abstraction without introducing a second runtime.

## Contract

```text
aasm.trace.v1 / 0.1.0
aasm.trace.semantic.v1 / 0.1.0
```

## Lossless projection

```python
from aasm import project_trace

report = project_trace(engine.events)
```

Each step contains:

```text
event_id
source_sequence
event_type
transition_class
support_status
source_sha256
source_event
```

The projector preserves source order and emits deterministic source-trace and projection fingerprints.

Unknown events are represented as:

```text
support_status = UNSUPPORTED
```

They are not omitted.

## Snapshot-only input

A snapshot is not a transition history. Therefore:

```python
project_trace({"snapshot": {...}})
```

is rejected. The trace layer accepts ordered durable events or an engine exposing its authoritative `.events` history.

## Semantic witness checks

A source event may carry an explicit semantic witness in its existing `data` payload:

```json
{
  "semantic_witness": {
    "pre_state": {},
    "post_state": {},
    "properties": {
      "restart_retains_hard_knowledge": true
    }
  }
}
```

The checker does not infer a witness from the final snapshot. If no adequate witness exists, that event is reported as unsupported for semantic refinement and the report can be `INCONCLUSIVE`.

Supported failure codes include:

```text
HARD_CONSTRAINT_WITHOUT_VERIFIED_CERTIFICATE
PARTIAL_CANDIDATE_ACTIVATION
RESTART_LOST_HARD_KNOWLEDGE
RESTART_LOST_PINNED_DECISION
COMPLETION_WITH_UNRESOLVED_MANDATORY
BACKJUMP_TARGET_REMAINS_ACTIVE
OPERATIONAL_EVENT_CHANGED_CALCULUS_ABSTRACTION
```

Every semantic failure records exact event identity and pre/post-state fingerprints.

## Corpus

```python
from aasm import build_trace_corpus

corpus = build_trace_corpus({
    "reference": engine.events,
    "operator-drill": other_engine.events,
})
```

The corpus is deterministically ordered and content-addressed.

## CLI

```bash
aasm trace-project MACHINE_ID --store runs.db
aasm trace-check MACHINE_ID --store runs.db
aasm inspect MACHINE_ID --store runs.db --surface trace
aasm inspect MACHINE_ID --store runs.db --surface trace-semantic
```

## Formal boundary

`formal/AASMTraceConformance.tla` and `formal/aasm_trace_conformance.pml` check a bounded abstraction of:

- source order preserved;
- projected prefix equals source prefix;
- no projected event lacks a support classification;
- unknown events remain explicitly `UNSUPPORTED`;
- known events remain `SUPPORTED`.

These models do not prove arbitrary domain semantics. The semantic checker requires explicit witnesses for covered runtime properties.
