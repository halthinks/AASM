# Governed Solution Pools & Complete Enumeration

AASM v0.51 introduces governed multi-solution state without creating a second solver, scheduler, reducer, or truth plane.

```text
A SOLUTION POOL IS NOT A COMPLETENESS CLAIM.
BOUNDED/NATIVE POOL != COMPLETE ENUMERATION.
```

## Contracts

- `aasm.optimization.solution-pool.v1 / 0.1.0`
- `aasm.optimization.enumeration.v1 / 0.1.0`
- completeness checker `aasm.checker.finite-enumeration-exhaustion.v1 / 0.1.0`

## COMPLETE semantics

`COMPLETE` requires a supported finite Boolean/integer model, deterministic exact solution identity, a durable no-good for every accepted solution, an exhausted durable cursor, and an independent exhaustion checker PASS proving exact feasible-set equality. Partial or solver-native pools cannot satisfy this rule merely because a backend stopped returning incumbents.

The checker reconstructs the finite domain independently of solver output and compares the complete oracle solution-ID set with the pool. Missing solutions, duplicates, foreign solutions, stale cursors, or incomplete traversal fail closed.

## Restart and durability

Pool, cursor, solutions, exclusions, and certificate are projected from the existing AASM Evidence/event history. SQLite restart/resume replays that same state; there is no second persistence authority.

## Cross-backend evidence

Real OR-Tools CP-SAT and HiGHS fixtures iteratively add canonical no-goods and must terminate with the same exact binary feasible set as the independent oracle. Policy: `EXACT_SOLUTION_SET_EQUALITY_NEVER_VOTING`.

## Authority

```text
solution/pool/certificate authority = EVIDENCE_ONLY
truth/state authority               = EXISTING_AASM_POLICY_ONLY
```

Completeness strengthens Evidence; it does not directly authorize canonical truth or state.
