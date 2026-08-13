# Typed Capabilities and Formal Verification

AASM v0.39 introduces a single typed capability boundary for tools that observe, verify, operate, or handle work. Formal theorem provers and proof assistants are the first reference family because they make the authority distinction especially clear: a solver can produce extremely strong evidence without becoming the machine's policy authority.

## 1. Typed protocol

`TypedEventSchema` defines the admitted event vocabulary and payload constraints. `ScopedLegalTransition` defines a legal `(from_state, event) -> to_state` relation. `PatternMachine` packages a versioned, scope-bound deterministic state vocabulary.

A pattern is not installed by a silent registry mutation. Admission requires `POLICY` or `CONTROLLER` authority and is stored through ordinary Evidence/event/reducer persistence.

A typed event is validated before any durable transition proposal. A successful proposal becomes an ordinary causal decision; guards, evidence requirements, and declared work become ordinary obligations. Activation requires those obligations to be `VERIFIED` or `COMMITTED`, followed by policy/controller authorization.

## 2. Capability ABI

A `CapabilityContract` defines:

- stable capability ID and version;
- `OPERATOR | OBSERVER | VERIFIER | HANDLER` class;
- input/output schemas;
- evidence types;
- supported formal logics/query modes when applicable;
- deterministic contract fingerprint.

A `CapabilityProvider` binds one admitted capability version to a real AASM `ResourceRecord` and `WorkerRecord`. The resource exposes both a capability token and a provider token. Existing scheduler selection and `TaskLease` ownership therefore remain the only execution ownership path.

Capability is not authority. A provider cannot directly alter durable planning, reasoning, effects, or state merely because it can perform work.

## 3. Formalization provenance

Before formal verification, AASM records a `FormalStatement` containing:

- source reasoning-artifact IDs;
- exact source artifact fingerprints;
- formal logic;
- query mode;
- query encoding;
- canonical formal source;
- declarations, assumptions, and conjecture where supplied;
- formalization compiler ID/version;
- optional environment fingerprint;
- deterministic formal-statement fingerprint.

This is a critical boundary. A theorem prover can prove only the exact formal statement it was given. A proof of a mistranslation is not silently upgraded into proof of the original natural-language claim.

Formalization authority remains `PROPOSAL_ONLY`.

## 4. Formal verifier capabilities

V0.39 declares reference providers for:

- **Vampire** — TPTP / first-order proving;
- **Z3** — SMT-LIB2;
- **cvc5** — SMT-LIB2;
- **Lean 4** — proof elaboration and trusted-kernel checking;
- a generic certificate-checker capability.

These providers normalize into the same result envelope but retain different semantics.

### Vampire

Vampire output is interpreted through its SZS status rather than brittle free-text substring guessing. For validity-style requests, statuses such as `Theorem`/`Unsatisfiable` can support `PROVED`; `CounterSatisfiable`/`Satisfiable` can support a countermodel interpretation.

### Z3 and cvc5

For `VALIDITY`, `INVARIANT`, and `EQUIVALENCE`, the `FormalStatement` must use:

```text
ASSUMPTIONS_AND_NEGATED_CONJECTURE
```

Under that explicit contract:

```text
UNSAT -> PROVED
SAT   -> COUNTERMODEL
```

For `SATISFIABILITY`, `sat` and `unsat` retain satisfiability semantics instead. This prevents AASM from treating every `sat` output as a theorem refutation.

### Lean 4

A successful Lean kernel check produces `PROVED` and may carry `TRUSTED_KERNEL` verification strength. A failed proof/elaboration is diagnostic/inconclusive evidence. The formal contract records Lean rejection as:

```text
NOT_A_REFUTATION
```

A failed candidate proof does not establish the theorem's negation.

## 5. Reproducible solver identity

The default verification policy requires conclusive solver evidence to identify:

- provider/solver ID;
- solver version;
- executable SHA-256 or immutable container digest;
- exact request fingerprint;
- exact formal-statement fingerprint.

Provider admission may pin expected version/binary/container identity; a result that conflicts with the admitted provider identity is rejected.

Raw output is diagnostic material with a separate SHA-256. Proof objects are also content-hashed separately. Neither is ambiguously folded into theorem identity.

## 6. Verification strength

Formal results expose explicit strength:

```text
SOLVER_VERDICT
MULTI_SOLVER_AGREEMENT
CHECKED_CERTIFICATE
TRUSTED_KERNEL
```

This is not a scalar claim that one solver is universally “better.” It records what kind of verification evidence was obtained so later policy and v0.40 context projection can distinguish them.

## 7. Agreement is not voting

`required_independent_results` may demand independent providers. If Z3 and cvc5 both produce the same conclusive semantic result, AASM may record `MULTI_SOLVER_AGREEMENT`.

If they disagree, the aggregate is `INCONCLUSIVE`. AASM does not use a majority vote to create truth. The verification policy can require another solver, a certificate checker, a Lean kernel check, human review, or another obligation.

## 8. TaskLease boundary

A formal request creates an ordinary AASM obligation plus one or more provider-specific `TaskDemand`s. The scheduler selects only resources carrying the required capability/provider tokens. A worker must hold the matching live `TaskLease` before its result can be committed.

This preserves existing distributed safety:

- stale workers cannot commit after lease expiry;
- a superseded attempt cannot mutate current state;
- task ownership is durable and replayable;
- provider identity must match provider-specific tasks;
- formal execution does not invent a second scheduler.

## 9. Epistemic admission

A `FormalVerificationResult` is Evidence. It is not an authorization.

For a linked v0.37 reasoning artifact:

```text
Formal result policy satisfied
        ↓
record_verification(... VERIFIER ...)
        ↓
VERIFIED
        ↓
POLICY / CONTROLLER authorize_artifact()
        ↓
AUTHORIZED
```

Countermodels can produce a proposed `Counterexample` artifact and a failed verification transition. Successful standalone formal results can propose `Lemma` or `Invariant` artifacts. These artifacts remain subject to the ordinary reasoning lifecycle.

## 10. V38 consequence propagation

Once policy changes upstream epistemic truth, v0.38 can determine what depends on it. A refuted/stale theorem can therefore invalidate only its downstream constraints/causal decisions and reopen only work that consumed the stale knowledge, preserving unrelated siblings.

That turns formal verification from a disconnected math utility into a governed deterministic worker inside the same causal state machine as every other AASM capability.
