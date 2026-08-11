# Generic Calculus Observability

AASM exposes durable reasoning state through domain-neutral projections rather than forcing every use case into one dashboard or ontology.

Every individual inspection call refreshes from the canonical store first. A long-lived reader therefore does not silently display an older in-memory snapshot after another process updates the machine.

## Core views

`AASMEngine.inspect_machine(surface)` supports:

- `summary` — the combined observability report;
- `decisions` — the Decision Graph;
- `obligations` — the Obligation Graph;
- `evidence` — the Evidence Graph;
- `causal` — one heterogeneous graph joining the major machine objects;
- `conflicts` — conflict lifecycle records, explanations, learned constraints, and recovery;
- `fairness` — persistent-obligation fairness debt;
- `packages` — profile binding and migration history;
- `candidates` — decision-backend and candidate lifecycle state;
- `assurance` — certificate, verification, history-check, and minimization state;
- `calculus` — the raw formal-calculus projection;
- `profile` — the bound profile package state.

## Closed graph contract

Each graph is closed over its edges: every `src` and `dst` identifier has a node in the same graph. When a projection references an object outside its primary node type, AASM includes either the typed object or an explicit external-reference node.

Consumers therefore do not have to guess what a dangling decision, certificate, or evidence identifier means.

## Decision, obligation, and evidence graphs

The Decision Graph presents planning decisions, values, status, levels, pinned assignments, scope, plan-node links, and dependency edges.

The Obligation Graph presents conditional obligations and their dependencies. Decision-to-obligation edges use `AUTHORIZED_BY`, and the corresponding decision nodes are present in the graph.

The Evidence Graph links evidence not only to other evidence but also to the decisions, obligations, conflicts, explanations, constraints, and certificates that cite it.

## Causal graph

The causal graph provides one joined inspection surface for:

- decisions;
- obligations;
- evidence;
- conditional locks;
- conflicts;
- explanations;
- learned constraints;
- certificates and verifications;
- candidate models.

Relations include `AUTHORIZES`, `LOCKS`, `IMPLICATED_IN`, `EXPLAINED_BY`, `CAUSAL_LITERAL`, `PROJECTS_TO`, `CERTIFIED_BY`, `VERIFIED_BY`, and `PROPOSES`.

## Timelines

Conflict history is represented as typed lifecycle records:

```text
CONFLICT_CREATED
CONFLICT_EXPLAINED
CONSTRAINT_LEARNED
CONFLICT_RESOLVED | CONFLICT_BACKJUMPED
```

The event timeline prefers typed operation fields emitted by the runtime. Reason-text classification remains only a compatibility fallback for older events.

## Fairness debt

Fairness records expose:

- hidden epochs;
- continuous lock age;
- lock count;
- policy thresholds;
- the amount each threshold is exceeded;
- active lock identities and reasons;
- last review and enablement epochs;
- the next required action.

This makes starvation risk operationally useful instead of returning only an opaque status label.

## Design boundary

A profile package may supply presentation hints outside the kernel, but the built-in observability model remains based on generic AASM objects. Research, engineering, operations, business, human, and autonomous software workflows can therefore use the same machine-level inspection contracts.
