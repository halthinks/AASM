# Reference Domain Stress Harness

AASM v0.42 exercises the existing domain-neutral solver, reuse, reasoning, truth-maintenance, and hierarchical-memory boundaries through five offline reference domains.

The harness is **not a second runtime** and does not add domain-specific branches to the kernel. It constructs ordinary `AASMEngine` machines, writes ordinary Evidence, creates ordinary Reasoning Artifacts and Memory Objects where appropriate, registers ordinary v0.41 reuse candidates, and then asks the existing runtime to accept or reject reuse.

Contract: `aasm.reference-domains.v1 / 0.1.0`.

## Reference domains

### Constraint solving

Exercises exact `SUBPROBLEM_RESULT` reuse, deletion of the process-local `HotReuseIndex`, environment invalidation, durable candidate recovery, and solver-loop `SKIP_EXECUTION` only after a committed reuse certificate.

### Software repair

Exercises bounded-freshness tool observations, repository/dependency fingerprint changes, expiration, and the invariant that `NON_IDEMPOTENT_EFFECT` work is never discharged by reuse.

### Research synthesis

Uses a real v0.37 `Claim` and the ordinary verification/authorization path as the canonical reusable source. A later stale transition must make the prior synthesis ineligible for reuse without deleting its provenance.

### Formal reasoning

Exercises `FORMAL_VERIFICATION_RESULT` reuse with an explicit required verification strength. A candidate whose `verification_strength` does not exactly satisfy `ReuseRequest.required_strength` is rejected even if its claimed request fingerprint matches. A valid strength can then be reused and certificate-gate solver execution skipping.

AASM deliberately does not invent a total ordering among verification strengths here. If callers need relations such as “trusted kernel is stronger than multi-solver agreement,” that relation must become an explicit contract rather than an implicit string ranking.

### Long-horizon memory

Creates a governed user-private Hierarchical Memory object through proposal → policy authorization → commit. The owner can project and reuse it; another principal cannot. A later governed memory tombstone changes the memory status to `REVOKED`, after which the prior memory cannot authorize reuse.

## Required boundaries

Every full harness run checks that:

- deleting the hot reuse index can affect performance but cannot change truth;
- environment, dependency, freshness, privacy, truth-status, revocation, effect-safety, and verification-strength changes block inapplicable reuse;
- solver execution is skipped only after validated reuse and a durable `ReuseCertificate`;
- reasoning invalidation and memory revocation are observed by the reuse plane;
- replay reconstructs the same canonical state as the persisted machine.

## Running the harness

Python:

```python
from aasm.reference_domains import run_reference_domain_stress

report = run_reference_domain_stress()
assert report["passed"]
```

A single domain may be selected by ID:

```python
run_reference_domain_stress("software-repair")
```

The harness is deterministic, synthetic, offline, and does not require model keys, network access, external solvers, or a production domain adapter. Its purpose is architecture stress, not benchmark claims about real-world domain quality.

## Boundary with v0.43

v0.42 provides reference-domain stress execution and ordinary pass/fail test assertions. It does **not** claim semantic certification of arbitrary domain packages. The planned v0.43 layer remains responsible for adversarial conformance and `PASS | FAIL | INCONCLUSIVE` certification semantics.
