# AASM v0.47.1 — Governed Symbiotic Intelligence & Apache-2.0 Licensing

AASM v0.47.1 is a licensing/packaging patch over v0.47.0. The runtime and public behavioral contracts remain the governed SII architecture introduced in v0.47.0; the project license is now Apache License 2.0 (`Apache-2.0`). The already-published v0.47.0 artifacts remain historically accurate under their original MIT license.

The runtime is still `SIIGovernanceRuntimeMixin + runtime_v46.AASMEngine`; there is one scheduler, one event/reducer path, one capability/provider registry, one reuse plane, and one truth boundary.

## Contracts

```text
package/public surface: 0.47.1
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
license: Apache-2.0
```

## Licensing patch

v0.47.1 changes the active project/distribution license from MIT to Apache License 2.0 and adds:

- the standard Apache License 2.0 text in `LICENSE`;
- a distributable `NOTICE` file preserving AASM attribution;
- PEP 639/SPDX `license = "Apache-2.0"` package metadata;
- no legacy `License :: ...` classifier, as required by the current setuptools PEP 639 path;
- `LICENSE` and `NOTICE` in `license-files`;
- `NOTICE` in the source-distribution manifest;
- contribution terms aligned to Apache-2.0;
- release gates that reject an incorrect license expression, a legacy license classifier, or missing Apache/NOTICE files.

No solver, authority, SII, memory, reuse, persistence, or verification semantics change in this patch.

## What graduated in v0.47.0

### Durable principals

SII proposal and measurement actors require policy-admitted `SIIPrincipalBinding` records. The same stable principal cannot silently rebind to a different authority/role set. Measurement authority is resolved from durable AASM state; callers do not supply their own authority class at measurement time.

### Versioned intelligence economics

Resource thresholds and weights are durable `SIIScoringPolicy` data. The default policy is version `1.0.0` and preserves reliability, calibration, verified utility, reuse contribution, compute efficiency, conflict-learning value, and artifact durability as the measured performance vector.

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

aliases the governed v0.47 SII graduation fixture and must return `PASS` instead of the v0.43 expected `INCONCLUSIVE`.

The fixture checks durable measurement-principal binding, active versioned scoring policy, rejection of unbound meters, no authority reward, native SAT/time budget enforcement, scheduler provenance, mandatory-verification non-reduction, and exact replay.

## Solver portfolio preserved

v0.47.1 preserves the native solver work from v0.44–v0.47.0:

- Kissat fast SAT;
- incremental CaDiCaL with assumptions/UNSAT cores/session reuse;
- OR-Tools CP-SAT scheduling;
- HiGHS MILP with warm starts/bounds/gap telemetry;
- CVXPY advanced convex optimization;
- PuLP translation-only import;
- Z3 / cvc5 / Vampire / Lean 4 formal verification.

Release identity:

```text
package/public surface: 0.47.1
runtime: runtime_v47.AASMEngine
base advanced solver runtime: runtime_v46.AASMEngine
base convex runtime: runtime_v45.AASMEngine
base optimization runtime: runtime_v44.AASMEngine
base solver/reuse kernel: runtime_v41.AASMEngine
adoption: aasm.adoption.v1 / 0.23.0
license: Apache-2.0
next: v0.48.0 Cross-Run Certified Knowledge & Governed Long-Term Memory
```

See `docs/SII_GOVERNED_ECONOMICS.md`, `docs/RELEASE_0.47.md`, and `docs/RELEASE_0.47.1.md`.
