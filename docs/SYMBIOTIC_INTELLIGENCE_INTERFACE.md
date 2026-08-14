# Symbiotic Intelligence Interface (SII)

## Status

Experimental v0.44 participation plane staged in v0.43 as an adversarial certification target.

```text
aasm.sii.v1 / 0.2.0
stability = EXPERIMENTAL_CERTIFICATION_TARGET
```

SII sits above the existing AASM authority machinery. It does not create another truth store, scheduler, reducer, event log, or kernel runtime.

## Core laws

1. **The reasoner proposes; AASM measures.**
2. **Utility may buy resources; utility never buys truth.**
3. **AASM returns compressed governed intelligence, not merely a reputation score.**

## Architecture

```text
intelligences: models / agents / humans / solvers / ensembles
                         |
                         v
                 SII participation plane
        identity / structured proposals / outcomes
        performance vector / resource lease / context
                         |
                         v
              existing AASM authority plane
     v0.37 reasoning + v0.38 truth maintenance
     v0.39 capabilities + formal verification
     v0.40 memory/context + v0.41 solver/reuse
                         |
                         v
             v0.43 adversarial certification
```

The active engine remains `runtime_v41.AASMEngine`. v0.43 intentionally does not add `runtime_v43.py` or resurrect the old candidate `runtime_v42.py` overlay.

## Proposal contract

A producer may submit:

- stable proposer identity;
- task class;
- decision name and scope;
- chosen candidate;
- rejected alternatives with reason codes;
- confidence;
- concise public rationale summary;
- typed `ArtifactProposal` consequences;
- references to existing AASM evidence;
- expected token/tool cost as an estimate.

A producer may not submit:

- its own semantic fingerprint;
- novelty/depth scores;
- a verification result as authority;
- a resource tier;
- raw private chain-of-thought as a required field.

Typed artifact proposals compile into the existing v0.37 `ReasoningArtifact` lifecycle with producer authority fixed to `PROPOSER`.

## Outcome measurement

SII derives verdicts from durable reasoning state when typed artifacts exist. A measurement caller cannot contradict that state.

Savings credit is read only from existing v0.41 `reuse_metrics` evidence. A producer cannot claim that it saved tokens or solver calls and receive credit merely because the proposal says so.

One proposal may contribute at most one scoreable outcome sample. Exact replay is idempotent; later reuse belongs in reuse telemetry instead of creating additional reputation samples.

## Performance vector

SII projects a bounded recent window rather than storing permanent power:

- Wilson lower-bound reliability;
- Brier confidence/calibration score;
- verified utility;
- reuse contribution;
- compute efficiency;
- conflict-learning value;
- artifact durability;
- repair rate;
- measured avoided input/output units;
- measured avoided model/tool/solver calls.

A contextual weight profile may emphasize exploration, exploitation, formal work, or the default mix.

## ResourceLease

A ResourceLease is an economic/search policy projection, never epistemic authority.

It may eventually grant more:

- context budget;
- parallel candidate budget;
- allowed solver classes;
- scheduler priority;
- permission to request long-lived memory;
- permission to propose schema changes.

It can never grant:

- direct truth promotion;
- direct canonical-state mutation;
- self-verification;
- POLICY or CONTROLLER authority.

v0.43 deliberately marks lease enforcement as:

```text
POLICY_PROJECTION_ONLY_V043
```

The lease is computed and inspectable, but scheduler/capability enforcement is a v0.44 graduation gate.

## Symbiotic context loop

```text
better structured contribution
        ↓
more verified reusable machine knowledge
        ↓
smaller / better future governed context
        ↓
more budget available for novel reasoning
        ↓
better reasoning
        ↓
more reusable knowledge
```

SII uses the existing v0.40 bounded context projection and reasoning frontier. Returned knowledge retains its original AASM truth state and authority.

## v0.44 graduation gates

SII does not graduate to an active runtime participation plane until all of these are satisfied:

1. **measurement principal/authority binding** — `measured_by` and its authority class must resolve from durable governed actor identity rather than caller assertion;
2. **scheduler enforcement** — context/candidate/priority budgets must be enforced by the existing resource/scheduling path;
3. **capability enforcement** — solver-class and privilege restrictions must be enforced by the existing capability/lease boundary;
4. **adversarial certification** — the SII certification target must reach `PASS`, including farming, forgery, reset, collusion, stale-data, and privilege-escalation fixtures.

Until then `aasm certify --target sii-preview` is expected to return `INCONCLUSIVE`, not `PASS`.

## Programmatic preview

```python
from aasm import AASMEngine, ProblemSpec, StructuredProposal, create_sii

engine = AASMEngine(ProblemSpec("participation preview"))
sii = create_sii(engine)
identity = sii.register(principal_id="provider:model:stable", name="reasoner")
proposal = StructuredProposal(
    proposer_id=identity["identity"]["proposer_id"],
    decision_name="choose_strategy",
    scope_id="root",
    chosen={"strategy": "reuse-first"},
    confidence=.8,
)
sii.submit(proposal)
```

This preview does not change the AASM kernel or grant the proposer additional authority.
