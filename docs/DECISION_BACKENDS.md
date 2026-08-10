# Decision Backends

AASM v0.23 separates **how candidate decision models are found** from **whether a candidate is allowed to affect machine state**.

A decision backend may enumerate, search, optimize, ask a human, call a model, or combine several strategies. It never receives authority to mutate the machine.

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
AASM validation
      |
      +--> REJECTED
      |
      v
ADMISSIBLE -> SELECTED -> ACTIVATED
```

## Built-in backends

- `aasm.finite-domain` — deterministic finite-domain enumeration with stable ordering and continuation tokens.
- `aasm.human` — produces a structured decision packet and accepts a human response as an ordinary candidate.
- `aasm.callback` — provider-neutral callback adapter for heuristic, model, or external proposal systems.
- `aasm.portfolio` — collects and deduplicates proposals from multiple backends while preserving source provenance.

## Authority boundary

A backend can propose assignments. The runtime independently checks:

- decision identity and subject;
- decision status;
- parent dependencies;
- pinned assignments;
- profile decision namespaces;
- learned hard constraints;
- fairness obligations.

A backend score can influence preference among admissible candidates. It cannot override a hard constraint.

## Candidate lifecycle

Candidate records are durable machine state:

`PROPOSED -> VALIDATING -> ADMISSIBLE | REJECTED -> SELECTED -> ACTIVATED -> SUPERSEDED | EXPIRED`

The lifecycle retains validation output, rejection reasons, backend identity, and sequence information so search behavior is replayable and inspectable.

## Backend contracts

`BackendCapabilities`, `BackendBudget`, `BackendUsage`, `BackendDiagnostic`, `CandidateBatch`, and `CandidateLifecycleRecord` provide the stable execution contract. Optional external SAT, SMT, CP-SAT, MILP, LLM, or human systems can implement the same contract without changing the AASM kernel.
