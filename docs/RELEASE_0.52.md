# AASM v0.52.0

**Resource-Governed Multi-Objective Decisions & Pareto Solving**

v0.52.0 makes the product-backward resource-governed decision foundation part of AASM's active public runtime.

## Public surface

```text
package/runtime: 0.52.0
aasm.adoption.v1 / 0.28.0

aasm.optimization.multi-objective.v1 / 0.1.0
aasm.optimization.frontier.v1 / 0.1.0
aasm.resource.capacity.v1 / 0.1.0
aasm.resource.observation.v1 / 0.1.0
aasm.resource.demand.v1 / 0.1.0
aasm.resource.routing.v1 / 0.1.0
aasm.resource.runtime.v1 / 0.1.0
aasm.sii.resource-aware-proposal.v1 / 0.1.0
```

## What changed

- exact finite lexicographic solving with explicit objective priority, direction, and tolerance;
- exact finite Pareto frontiers over v0.51 certified complete finite enumeration;
- independent full-point frontier verification: solution ID + assignment + objective vector;
- tolerance-aware Pareto dominance;
- governed capacity windows, protected reserves, and resource-observation provenance;
- explicit provider quota burn, cost, wall time, scarce-expert usage, correctness, evidence quality, and expected progress dimensions;
- policy-controlled resource objective ordering rather than a fixed economic scoring function;
- resource-aware SII successor proposals with exact parent proposal lineage;
- atomic conservative reservation before resource consumption;
- durable re-estimation with `CONTINUE | REPLAN_REQUIRED`, release, settlement, and calibration Evidence;
- non-committing Pareto analysis over supplied eligible resource candidates;
- workspace/scope-safe resource inspection and replay;
- dedicated `aasm/optimization` exact-SHA release status.

## Completeness boundary

Two Pareto claims are deliberately distinct:

- exact finite optimization `COMPLETE` is certified over the independently exhausted supported finite model space;
- resource-candidate Pareto is exact only over the supplied eligible candidate set and does not claim route-discovery completeness.

Neither claim grants truth, state authority, or permission to consume resources.

## Authority boundary

```text
RESOURCE STATE NEVER GRANTS AUTHORITY.
RESOURCE OBSERVATIONS REMAIN EVIDENCE.
OPTIMALITY / COMPLETENESS REMAIN EVIDENCE.
SII UTILITY NEVER BUYS TRUTH OR STATE AUTHORITY.
```

## Release gates

The release is publishable only when the exact current `main` SHA has successful:

```text
aasm/ci-summary
aasm/formal-assurance
aasm/semantic-solver-rc
aasm/proof-claims
aasm/solution-pools
aasm/optimization
```

## Next

v0.53 is **Durable Cross-Run Solver Learning + Scoped Identity/Authority Hardening**.

License: Apache-2.0 project-wide.
