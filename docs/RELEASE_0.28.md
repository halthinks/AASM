# AASM v0.28.0 — Distribution and Operator Readiness

AASM v0.28.0 closes the next adoption gap: the system can now be distributed as an inspected wheel and operated through tested recovery procedures.

## Distribution

The release pipeline now produces:

- a wheel;
- a source distribution;
- `SHA256SUMS.txt`;
- `release-manifest.json`;
- an annotated Git tag;
- a GitHub Release with immutable assets.

The wheel is installed into a clean virtual environment before release. That installed package must validate `aasm.adoption.v1` and execute an operator runbook.

The workflow can publish to PyPI through Trusted Publishing after the external `aasm-runtime` PyPI publisher binding is configured. The repository contains no long-lived PyPI credential.

## Operator readiness

Seven executable runbooks cover:

1. lease-loss recovery;
2. additive requirement injection;
3. learned no-good inspection;
4. human quorum approval;
5. replay and fork;
6. `UNKNOWN` effect reconciliation;
7. durable-history diagnosis.

Each runbook uses ordinary AASM APIs and returns a machine-readable PASS/FAIL report. The matching one-page document gives the starting state, commands, expected evidence, failure indicators, and reset procedure.

## Working-path rule

v0.28.0 does not create an operations-only runtime.

```text
operator command
  ↓
public AASM API
  ↓
existing event/reducer authority path
  ↓
existing Memory / SQLite / PostgreSQL store
  ↓
existing calculus, assurance, effects, workers, leases, replay, and observability
```

No runbook writes AASM tables or snapshots directly.

## Version boundary

```text
package/runtime:  aasm-runtime 0.28.0
adoption contract: aasm.adoption.v1 / 0.4.0
remote protocol:   aasm.remote.v1 / 0.19.0
```

The next release is **v0.29.0 — Thin LangGraph Adapter**.
