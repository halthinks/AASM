# AASM v0.30.0 — Adapter Conformance Kit

AASM v0.30.0 makes the integration boundary executable and reviewable. A framework adapter can now produce a machine-readable report showing whether it preserves AASM authority, durability, evidence, effects, leases, recovery, and replay. The release stays on the existing event/reducer authority path.

## Delivered contract

```text
aasm.adapter.conformance.v1 / 0.1.0
```

The release includes:

- framework-neutral adapter driver protocol;
- versioned capability and authority declaration;
- eight required black-box scenarios;
- semantic-result and evidence-provenance checks;
- direct Store mutation detection;
- duplicate-authority rejection;
- durable-history verification;
- replay-versus-persisted snapshot comparison;
- `PASS | FAIL | INCONCLUSIVE` reports;
- exact findings, event references, coverage, audit records, and report fingerprint;
- reference LangGraph conformance driver;
- deliberately broken negative fixtures;
- Python, CLI, authenticated HTTP, and Control Center surfaces;
- report and capability JSON schemas.

## Run it

```bash
aasm adapter-conformance --adapter langgraph
```

One scenario:

```bash
aasm adapter-conformance \
  --adapter langgraph \
  --scenario unknown_effect \
  --output conformance-report.json
```

## Existing event/reducer authority path retained

```text
framework adapter
    → AASM public adoption API
    → existing event/reducer runtime
    → existing Memory / SQLite / PostgreSQL stores
    → existing calculus, assurance, effects, workers, leases, replay, and fork
```

v0.30.0 introduces no alternate runtime, duplicate scheduler, duplicate effect ledger, private database mutation path, or framework-owned AASM truth.

## Compatibility identities

```text
package/runtime:       aasm-runtime 0.30.0
adoption contract:     aasm.adoption.v1 / 0.6.0
LangGraph adapter:     aasm.langgraph.v1 / 0.1.0
adapter conformance:   aasm.adapter.conformance.v1 / 0.1.0
remote protocol:       aasm.remote.v1 / 0.19.0
```

## Correctness boundary

The Store audit is an in-process conformance hook, not a security sandbox. It detects ordinary integration bypasses and explicitly distinguishes external effect execution. Untrusted code still requires process or host isolation.

A `PASS` applies to the exact driver, declared versions, and selected bounded scenarios. It does not manufacture truth or certify unexercised external behavior.

## Next release

**v0.31.0 — Hierarchical Decision Scopes** will introduce strategy, architecture, and implementation scopes while retaining one authoritative machine and one causal conflict graph.
