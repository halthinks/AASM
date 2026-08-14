# AASM v0.47.0 — Governed Symbiotic Intelligence & Intelligence Economics

AASM v0.47 graduates SII from the experimental preview into an enforceable participation/resource plane over the real v0.46 native solver substrate. The runtime is `SIIGovernanceRuntimeMixin + runtime_v46.AASMEngine`; there is still one scheduler, one event/reducer path, one capability/provider registry, one reuse plane, and one truth boundary.

## Contracts

```text
aasm.adoption.v1 / 0.23.0
aasm.certification.v1 / 0.2.0
aasm.sii.v1 / 0.3.0
aasm.optimization.advanced.v1 / 0.1.0
aasm.optimization.v1 / 0.1.0
aasm.optimization.convex.v1 / 0.1.0
aasm.adapter.pulp.v1 / 0.1.0
aasm.reuse.v1 / 0.1.0
aasm.reuse.certificate.v1 / 0.1.0
aasm.capability.abi.v1 / 0.1.0
aasm.formal.verification.v1 / 0.1.0
aasm.remote.v1 / 0.19.0
```

## What graduated

### Durable principals

SII proposal and measurement actors now require policy-admitted `SIIPrincipalBinding` records. The same stable principal cannot silently rebind to a different authority/role set. Measurement authority is resolved from durable AASM state; callers no longer supply their own authority class at measurement time.

### Versioned intelligence economics

Resource thresholds and weights are now durable `SIIScoringPolicy` data. The default policy is version `1.0.0` and preserves reliability, calibration, verified utility, reuse contribution, compute efficiency, conflict-learning value, and artifact durability as the measured performance vector.

### Enforced ResourceLease

`GovernedResourceLease` values are compiled into existing AASM execution surfaces:

- v0.40 context projection size;
- TaskDemand scheduler priority;
- outstanding discretionary-task count;
- incremental CaDiCaL conflict/decision budgets;
- OR-Tools CP-SAT deterministic time and worker count;
- HiGHS MIP node budget;
- native/convex solve timeout;
- discretionary formal verification timeout and provider width.

Every governed request records enforcement Evidence and tags the ordinary task/TaskLease provenance with proposer, principal, scoring policy, resource tier, lease ID, and `authority_reward = NEVER`.

## Safety boundary

```text
UTILITY MAY BUY COMPUTE / SEARCH / CONTEXT.
UTILITY NEVER BUYS TRUTH / STATE AUTHORITY / SELF VERIFICATION.
REQUIRED VERIFICATION IS NEVER REDUCED BY SII.
```

A low SII score cannot remove a required verifier, weaken proof strength, shrink a required independent-result quorum, or bypass epistemic admission. Policy-required formal verification stays on the ordinary formal path; SII's formal path is explicitly discretionary.

## Certification

`aasm.certification.v1 / 0.2.0` includes governed SII in the default certification set. For compatibility:

```bash
aasm certify --target sii-preview
```

now aliases the governed v0.47 SII graduation fixture and must return `PASS` instead of the v0.43 expected `INCONCLUSIVE`.

The fixture checks durable measurement-principal binding, active versioned scoring policy, rejection of unbound meters, no authority reward, native SAT/time budget enforcement, scheduler provenance, mandatory-verification non-reduction, and exact replay.

## Solver portfolio preserved

v0.47 does not replace the native solver work from v0.44–v0.46:

- Kissat fast SAT;
- incremental CaDiCaL with assumptions/UNSAT cores/session reuse;
- OR-Tools CP-SAT scheduling;
- HiGHS MILP with warm starts/bounds/gap telemetry;
- CVXPY advanced convex optimization;
- PuLP translation-only import;
- Z3 / cvc5 / Vampire / Lean 4 formal verification.

The new SII layer allocates resources around those existing capabilities rather than becoming a solver itself.

Release identity:

```text
package/public surface: 0.47.0
runtime: runtime_v47.AASMEngine
base advanced solver runtime: runtime_v46.AASMEngine
base convex runtime: runtime_v45.AASMEngine
base optimization runtime: runtime_v44.AASMEngine
base solver/reuse kernel: runtime_v41.AASMEngine
adoption: aasm.adoption.v1 / 0.23.0
next: v0.48.0 Cross-Run Certified Knowledge & Governed Long-Term Memory
```

See `docs/SII_GOVERNED_ECONOMICS.md` and `docs/RELEASE_0.47.md`.
