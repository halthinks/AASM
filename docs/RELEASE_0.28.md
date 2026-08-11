# AASM v0.28.1 — Distribution Release Hardening

AASM v0.28.1 repairs the release boundary exposed while publishing v0.28.0. The deterministic runtime, calculus, assurance system, local stack, and Operator runbooks continue through the same public AASM path.

## What remains from v0.28.0

v0.28.0 — Distribution and Operator Readiness delivered inspected Python distributions, a compatibility policy, and Seven executable runbooks:

1. lease-loss recovery;
2. additive requirement injection;
3. learned no-good inspection;
4. human quorum approval;
5. replay and fork;
6. `UNKNOWN` effect reconciliation;
7. durable-history diagnosis.

Each runbook still uses ordinary AASM APIs and returns a machine-readable PASS/FAIL report.

## Distribution hardening

The v0.28.1 pipeline now requires:

- exact build-backend and build-frontend versions;
- two independent builds under the same recorded source epoch;
- byte-identical wheel and source-distribution files;
- clean-wheel installation and installed CLI smoke tests;
- successful ordinary CI and formal assurance on the exact commit;
- one-time GitHub Release creation without asset overwrite;
- remote tag-target, asset-name, byte-size, and SHA-256 verification.

The published asset set is:

```text
aasm_runtime-0.28.1-py3-none-any.whl
aasm_runtime-0.28.1.tar.gz
historical-release-report.json
SHA256SUMS.txt
release-manifest.json
```

## Historical release boundary

Old workflow-bearing commits can require owner-level permission for retrospective tag publication. That boundary no longer causes a valid current release to fail after its own assets were already published.

`historical-release-report.json` records:

- `VERIFIED` for an old tag at the recorded commit;
- `PENDING_OWNER_PUBLICATION` for a missing tag;
- `MISMATCH` for an old tag at the wrong commit.

A missing tag is visible and non-blocking. A mismatch is blocking.

## Working-path rule

v0.28.1 does not create a release-only runtime.

```text
operator or release command
  ↓
public AASM API
  ↓
existing event/reducer authority path
  ↓
existing Memory / SQLite / PostgreSQL store
  ↓
existing calculus, assurance, effects, workers, leases, replay, and observability
```

No runbook or release operation writes AASM tables or snapshots directly.

## Version boundary

```text
package/runtime:   aasm-runtime 0.28.1
adoption contract: aasm.adoption.v1 / 0.4.0
remote protocol:   aasm.remote.v1 / 0.19.0
```

The next release is **v0.29.0 — Thin LangGraph Adapter**. The complete plan through v0.34.0 is in `ROADMAP.md`.
