# S5.2 Governed Experiment Foundation and Durable Proposal Runtime

**Status:** pre-admission semantic/runtime foundation  
**Semantic contract:** `aasm.experiment.v1 / 0.1.0`  
**Runtime contract:** `aasm.experiment.runtime.v1 / 0.1.0`  
**Qualification:** `aasm/experiment`

## Purpose

AASM experiments are governed proposals for acquiring discriminating Evidence.
They are not executable jobs, effect authorizations, resource reservations, or
truth-producing shortcuts.

The experiment contract binds, in one deterministic revision-scoped object:

- explicit hypotheses;
- controlled variables;
- measured variables;
- ordered procedure;
- exact execution-environment reference;
- physical fixture identity or an explicit `NOT_APPLICABLE` declaration;
- calibration identity or an explicit `NOT_APPLICABLE` declaration;
- expected discriminating outcomes;
- existing evidence-floor references;
- existing resource-demand references;
- existing safety/risk references;
- exact `ProblemRevision` id and fingerprint;
- proposal-producing principal and supporting Evidence.

## No hidden applicability

Environment, evidence floor, resource demand, and safety/risk constraints cannot
be omitted or replaced by an implicit default.

Fixture and calibration are different because some experiments are purely
model/simulation-based. They still cannot disappear silently. Each must either
bind an exact existing object or carry an explicit `NOT_APPLICABLE` declaration
with a reason.

## Procedure boundary

Procedure steps are ordered descriptive records with capability and artifact
references. They contain no executable callback, shell command, code payload, or
authority token. A later execution layer must independently authorize and bind
real effects/resources.

## Information-value selection

`ExperimentSelectionCandidate` consumes a hard-constraint disposition backed by
existing AASM Evidence:

`ELIGIBLE | BLOCKED_REVISION | BLOCKED_SAFETY | BLOCKED_EVIDENCE | BLOCKED_RESOURCE | INDETERMINATE`

The experiment module does not calculate those hard dispositions. It does not
reimplement safety, risk, evidence, revision, or resource governance.

Only `ELIGIBLE` candidates enter information-value ranking. The deterministic
proposal order is:

1. maximum expected information gain;
2. maximum expected uncertainty reduction;
3. stable experiment/candidate identity tie-break.

Scores are integer parts-per-million values, not binary floating-point semantic
identity.

A blocked experiment with arbitrarily high information value cannot win. If no
candidate is eligible, no experiment is selected. This is not reported as
success.

## Durable proposal history

`ExperimentRuntimeMixin` records only two append-only proposal records through
the existing AASM Evidence/event/replay path:

- `EXPERIMENT_SPEC`
- `EXPERIMENT_SELECTION_PROPOSAL`

It introduces no experiment table or current-experiment pointer.

New experiment records must bind the exact current durable `ProblemRevision` and
may not cross a pending truth-maintenance boundary. Every supporting Evidence id
from the experiment, its hypothesis basis, and its bound context records must
exist and be active at record time.

New selection records require:

- every candidate experiment already exists in durable experiment history;
- exact experiment fingerprint and revision match;
- active hard-constraint assessment Evidence;
- active support for every `ELIGIBLE` experiment;
- deterministic recomputation of the selected candidate.

A lower-information eligible experiment cannot be forged into a durable
selection record. A blocked experiment still cannot win.

If supporting Evidence is invalidated later, the historical proposal is not
erased. The stale support only prevents that Evidence from authorizing a new
experiment or selection proposal.

## Authority ceiling

An experiment or selection proposal grants none of the following:

- FactAuthority;
- effect authority;
- artifact acceptance;
- problem mutation authority;
- resource reservation;
- effect dispatch;
- experiment execution.

Selection is proposal-only. Existing AASM authority/resource/effect systems must
perform any later admission or execution.

## Admission boundary

The semantic and durable proposal runtime remain `PRE_ADMISSION_ONLY`. They are
intentionally absent from the active public root. S5.2 does not add an execution
path; later verification/experiment execution work must independently bind the
existing authority, resource, effect, observation, and safety planes.
