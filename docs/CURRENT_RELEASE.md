# AASM v0.48.1 — Cross-Run Certified Knowledge & Project-Wide Apache-2.0 Policy Correction

AASM v0.48.1 preserves the v0.48 cross-run runtime and corrects the public licensing policy so it matches the intended project-wide Apache-2.0 declaration.

The runtime remains `CrossRunKnowledgeRuntimeMixin + runtime_v47.AASMEngine`. There is still one event/reducer path, one scheduler/TaskLease plane, one memory governance path, one reuse certificate path, and one truth boundary.

## Contracts

```text
package/public surface: 0.48.1
aasm.adoption.v1 / 0.24.0
aasm.knowledge.cross-run.v1 / 0.1.0
aasm.knowledge.cross-run.admission.v1 / 0.1.0
aasm.principal.cross-run-map.v1 / 0.1.0
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

## Project-wide Apache-2.0 policy

AASM's declared license is **Apache License 2.0 (`Apache-2.0`) across the project**.

`LICENSE_POLICY.md` states the project-wide grant: to the extent AASM has the necessary relicensing rights, prior AASM versions that were first distributed under MIT are **also offered under Apache-2.0**. Previously granted MIT permissions remain valid for their recipients, but those surviving grants do not classify prior AASM versions as MIT-only.

Current distributions package `LICENSE` and `NOTICE` through PEP 639/SPDX metadata. Release gates require the project-wide declaration and reject stale “first Apache release” or “old release is MIT-only” wording.

## Cross-run boundary

A source run exports immutable `CrossRunKnowledgeEnvelope` objects with source run/machine/scope, memory/evidence/artifact lineage, fingerprints, environment/dependency declarations, privacy, retention/freshness, verification strength, content, and source authority provenance.

The receiving run validates applicability and emits a `CrossRunAdmissionCertificate`. A valid certificate still requires an ordinary AASM Decision plus POLICY/CONTROLLER authorization and an Obligation before the envelope becomes receiving-run Evidence.

```text
FOREIGN AUTHORITY IS PROVENANCE, NEVER RECEIVING AUTHORITY.
```

## Memory and reuse

Foreign Evidence never becomes semantic memory merely because the source run considered it true. Local semantic materialization requires receiving-run reasoning artifacts already in `AUTHORIZED` state, then uses the normal v0.40 memory authorization/commit path.

Cross-run reuse uses the existing v0.41 candidate/validation/`ReuseCertificate` path and preserves exact verification-strength matching. The ordinary reuse certificate records the envelope ID/fingerprint and receiving validator ID/version.

## Revocation and supersession

A source signal must itself be admitted by receiving POLICY/CONTROLLER. Once admitted, the source envelope becomes REVOKED/SUPERSEDED, already-hot reuse candidates are blocked, and locally materialized memories are tombstoned through the existing v0.40 FORGET path. History is never deleted.

## SII identity/reputation

Stable cross-run principal mapping is explicit. SII reputation must name the exact source principal and match an admitted `(source run, source principal → local principal)` mapping. Cross-run reputation is reference accounting only:

```text
truth_authority              = NONE
resource_entitlement         = NONE
used_by_sii_resource_lease   = false
```

It does not modify local SII authority or local compute tiers.

## Preserved v0.47 safety boundary

```text
UTILITY MAY BUY COMPUTE / SEARCH / CONTEXT.
UTILITY NEVER BUYS TRUTH / STATE AUTHORITY / SELF VERIFICATION.
REQUIRED VERIFICATION IS NEVER REDUCED BY SII.
```

## Solver/formal portfolio preserved

- Kissat fast SAT;
- incremental CaDiCaL assumptions/UNSAT cores/session reuse;
- OR-Tools CP-SAT scheduling;
- HiGHS MILP with warm starts/bounds/gap telemetry;
- CVXPY advanced convex optimization;
- PuLP translation-only import;
- Z3 / cvc5 / Vampire / Lean 4 formal verification.

## Verification

v0.48.1 preserves the dedicated Cross-Run Knowledge workflow, dependency-neutral conformance, adversarial runtime tests, JSON schemas, and bounded `AASMCrossRunKnowledge.tla` / `aasm_cross_run_knowledge.pml` assurance. All existing CI, Formal Assurance, Optimization Backends, replay, persistence, packaging, scopes, adapters, and LangGraph gates remain required.

## Release identity

```text
package/public surface: 0.48.1
runtime: runtime_v48.AASMEngine
base governed-SII runtime: runtime_v47.AASMEngine
base solver/reuse kernel: runtime_v41.AASMEngine
adoption: aasm.adoption.v1 / 0.24.0
license: Apache-2.0 project-wide declaration
next: v0.49.0 Semantic Solver Release Candidate
```

See `LICENSE_POLICY.md`, `docs/CROSS_RUN_CERTIFIED_KNOWLEDGE.md`, `docs/RELEASE_0.48.md`, and `docs/RELEASE_0.48.1.md`.
