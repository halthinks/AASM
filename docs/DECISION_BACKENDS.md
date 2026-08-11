# Decision Backends

AASM separates **how candidate decision models are found** from **whether a candidate is allowed to affect machine state**.

A backend may enumerate choices, search, optimize, ask a human, call a model, or combine several strategies. It never receives authority to mutate the machine.

```text
DecisionRequest
      |
      v
DecisionBackend
      |
      v
CandidateBatch
      |
      v
AASM kernel validation
      |
      +--> REJECTED
      |
      v
ADMISSIBLE -> SELECTED -> ACTIVATED
```

## Built-in backends

- `aasm.finite-domain` performs deterministic finite-domain enumeration with stable ordering and continuation tokens.
- `aasm.human` produces a structured decision packet and accepts a human response as an ordinary candidate.
- `aasm.callback` adapts a heuristic, model, or external proposal function.
- `aasm.portfolio` combines several backends, deduplicates equal assignments, and retains every contributing source in candidate provenance.

## Enforced budgets

`BackendBudget` can limit:

- candidates returned per call;
- combinations inspected per call;
- declared cost;
- elapsed latency.

The finite-domain backend enumerates incrementally inside those limits. It does not reject an entire search space merely because the full Cartesian product is larger than one call's budget.

The callback backend can stop waiting at a latency deadline and returns a typed `CALLBACK_TIMEOUT` diagnostic. This is a timeout boundary, **not a security sandbox**. Untrusted callback code belongs in a separate process or stronger isolation boundary.

Portfolio execution passes remaining budget to each backend, records backend errors as diagnostics, and stops when the shared budget is exhausted.

## Authority boundary

A backend can propose assignments. The runtime independently checks:

- decision identity and subject;
- decision status;
- parent and antecedent dependencies;
- pinned assignments;
- profile decision namespaces;
- active hard constraints;
- fairness requirements.

A backend score may help rank admissible candidates. It cannot override a hard constraint or kernel invariant.

## Atomic activation

Candidate activation is all-or-nothing.

AASM stages the complete assignment set in an isolated calculus copy, applies supersession and dependent suspension, re-evaluates locks, checks hard constraints and fairness, and validates every invariant. Only then does it commit the new calculus and candidate lifecycle together in one durable snapshot patch.

A failure in the last assignment therefore cannot leave earlier assignments partially active.

## Candidate lifecycle

Candidate records are durable machine state:

```text
PROPOSED
  -> VALIDATING
  -> ADMISSIBLE | REJECTED
  -> SELECTED
  -> ACTIVATED
  -> SUPERSEDED | EXPIRED
```

The lifecycle retains validation output, rejection reasons, backend identity, assignment provenance, sequence information, and activation effects so search behavior is replayable and inspectable.

## Extension contract

`BackendCapabilities`, `BackendBudget`, `BackendUsage`, `BackendDiagnostic`, `CandidateBatch`, and `CandidateLifecycleRecord` provide the provider-neutral contract. External SAT, SMT, CP-SAT, MILP, model, heuristic, or human systems can implement it without changing the AASM kernel.
