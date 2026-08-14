# AASM v0.51.0 — Governed Solution Pools & Complete Enumeration

AASM v0.51 adds governed multi-solution state and complete finite enumeration over the existing v0.50 proof runtime.

```text
package/public surface: 0.51.0
runtime: runtime_v51.AASMEngine
parent runtime: runtime_v50.AASMEngine
aasm.adoption.v1 / 0.27.0
aasm.optimization.solution-pool.v1 / 0.1.0
aasm.optimization.enumeration.v1 / 0.1.0
license: Apache-2.0 project-wide declaration
```

A solution pool is useful Evidence even when partial, but only an independently certified exhausted finite enumeration may be marked `COMPLETE`. Real CP-SAT and HiGHS enumeration must agree exactly with the independent oracle, never by voting.

Required release gates include `aasm/ci-summary`, `aasm/formal-assurance`, `aasm/semantic-solver-rc`, `aasm/proof-claims`, and `aasm/solution-pools` on the exact current `main` SHA.
