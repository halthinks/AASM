# AASM v0.51.0 — Governed Solution Pools & Complete Enumeration

Release identity:

```text
package/public surface: 0.51.0
runtime: runtime_v51.AASMEngine
parent runtime: runtime_v50.AASMEngine
adoption: aasm.adoption.v1 / 0.27.0
solution pool: aasm.optimization.solution-pool.v1 / 0.1.0
enumeration: aasm.optimization.enumeration.v1 / 0.1.0
license: Apache-2.0 project-wide declaration
```

AASM v0.51 adds restart-safe governed solution pools, deterministic exact deduplication, durable no-goods, finite enumeration cursors, and independent exhaustion certificates. `COMPLETE` is unavailable until the finite model is exhausted and exact feasible-set equality is independently checked.

The dedicated `aasm/solution-pools` gate exercises oracle-known complete enumeration, SQLite restart/resume, false-completeness rejection, and real CP-SAT/HiGHS exact-set consistency.

No solution pool or completeness certificate gains truth authority: all are `EVIDENCE_ONLY`; canonical truth/state remains `EXISTING_AASM_POLICY_ONLY`.
