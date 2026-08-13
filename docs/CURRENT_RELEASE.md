# AASM v0.39.0 — Typed Protocol, Capability ABI, and Formal Verification Workers

V0.39.0 generalizes typed legal transitions into a versioned protocol/capability ABI and makes Vampire, Z3, cvc5, and Lean 4 first-class governed verifier workers without creating a second scheduler, reducer, event log, or truth authority.

## Contracts

```text
aasm.typed.protocol.v1      / 0.1.0
aasm.capability.abi.v1      / 0.1.0
aasm.formal.statement.v1    / 0.1.0
aasm.formal.verification.v1 / 0.1.0
```

Inherited contracts remain authoritative, including:

```text
aasm.reasoning.artifact.v1
aasm.reasoning.admission.v1
aasm.semantic.dependencies.v1
aasm.truth.maintenance.v1
aasm.scopes.v1
aasm.trace.v1
aasm.provenance.v1
```

## Delivered

- typed event payload schemas and deterministic legal transition rules;
- policy/controller-admitted `PatternMachine` versions;
- typed transitions proposed as existing causal decisions;
- guards/evidence requirements compiled into ordinary obligations;
- activation only after obligations complete and policy/controller authority is present;
- versioned capability/provider ABI with ordinary resource/worker/scheduler tokens;
- provenance-bearing `FormalStatement` objects with exact source-artifact fingerprints;
- formal query modes and canonical solver result semantics;
- Vampire/TPTP, Z3/SMT-LIB2, cvc5/SMT-LIB2, Lean 4/kernel, and certificate-checker capability declarations;
- SMT validity contract `ASSUMPTIONS_AND_NEGATED_CONJECTURE`;
- Lean rejection semantics `NOT_A_REFUTATION`;
- solver version plus binary SHA-256 or immutable container digest identity policy;
- independently hashed proof objects and diagnostic raw output;
- multi-solver agreement without majority-vote truth;
- disagreement remains `INCONCLUSIVE`;
- formal requests produce ordinary AASM obligations and `TaskDemand`s;
- result acceptance requires an admitted provider plus matching active `TaskLease`;
- solver results cross back through Evidence and then the v0.37 verification lifecycle;
- no formal solver may self-authorize reasoning;
- standalone successful formal results propose Lemma/Invariant artifacts; countermodels propose Counterexample artifacts;
- SQLite/replay preservation, JSON schemas, CLI surfaces, conformance tests, and bounded TLC/SPIN authority models.

## Authority boundary

```text
model / human / formalizer
          ↓ proposal
FormalStatement
          ↓
ordinary formal-verification Obligation
          ↓
TaskDemand → Resource/Worker → TaskLease
          ↓
Vampire / Z3 / cvc5 / Lean 4
          ↓ Evidence only
FormalVerificationResult
          ↓
v0.37 VERIFY
          ↓
POLICY / CONTROLLER only
          ↓
AUTHORIZED reasoning
          ↓
v0.38 dependency / truth-maintenance consequences
```

Formalization correctness is itself an explicit provenance boundary: proving a formal statement does not magically prove that an incorrect translation represented the intended source claim.

```text
package/runtime: 0.39.0
adoption:         aasm.adoption.v1 / 0.15.0
remote:           aasm.remote.v1 / 0.19.0
next:             v0.40.0 Hierarchical Memory, Reasoning Frontier, and Context Projection
```
