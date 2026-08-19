# S4.8 Safety Envelope and Hybrid State Foundation

**Status:** implemented as a pre-admission semantic foundation  
**Contracts:** `aasm.safety.envelope.v1`, `aasm.hybrid.state.v1`, `aasm.safety.envelope.assessment.v1`  
**Runtime/public admission:** `PRE_ADMISSION_ONLY`

## Purpose

S4.8 gives AASM a deterministic, revision-bound way to state and assess safety envelopes that combine a discrete observed mode with continuous engineering quantities. It lets external simulation, measurement, control, CAD, SPICE, thermal, mechanical, robotics, and manufacturing systems report typed state into AASM without turning AASM into an ODE solver, physics engine, controller, dispatcher, or second operational state machine.

The foundation answers one narrow question:

> For this exact subject and ProblemRevision, does the explicitly observed hybrid state lie wholly inside the exact continuous safety region declared for its discrete mode?

The answer is a pure semantic assessment. It is not authorization, proof of physical truth, mode activation, artifact acceptance, or effect dispatch.

## Canonical composition

The foundation reuses existing live contracts rather than inventing parallel semantics:

- continuous values and intervals are exact `aasm.quantity.v1` objects;
- safety legality is an exact `aasm.rule.v1` `HARD_FLOOR` rule whose clause kind is `SAFETY_INVARIANT`;
- subjects use `SemanticSubjectRef`;
- external solver, sensor, calibration, or tool lineage uses `aasm.external.reference.v1`;
- evidence remains referenced by existing Evidence IDs;
- the envelope and observed state bind the exact ProblemRevision ID and fingerprint.

No second unit registry, quantity system, hard-floor vocabulary, evidence store, safety state machine, authority evaluator, operational-mode store, or dispatcher is introduced.

## Safety envelope

A `SafetyEnvelope` contains one or more `SafetyModeEnvelope` records. Each mode contains exactly one constraint per continuous variable. A constraint binds:

- a stable constraint and variable ID;
- the exact existing Rule revision ID and fingerprint;
- the exact allowed Quantity ID, object fingerprint, and canonical-projection fingerprint;
- optional evidence and external references;
- portable metadata with binary floating point forbidden.

Allowed regions are exact `INTERVAL` quantities. They may not carry tolerance or quantization: tolerance belongs to observations, not to the hard safety boundary.

## Hybrid state

A `HybridState` is an immutable observation record containing:

- exact subject and ProblemRevision binding;
- one observed discrete mode label;
- zero or more continuous-variable observations;
- explicit evidence or external-reference provenance for the mode;
- explicit evidence or external-reference provenance for every quantity observation.

Zero continuous observations are valid. This represents “the mode was observed, but all required telemetry is missing” honestly; assessment then becomes `INDETERMINATE` rather than manufacturing a value.

The mode label is not a current-mode pointer and does not activate, transition, or command an operational mode.

## Conservative support semantics

Observed support is evaluated in canonical Quantity units using exact rational arithmetic:

- exact scalar: singleton support;
- interval: declared interval support;
- measured/estimated quantity: declared uncertainty interval;
- absolute tolerance: exact symmetric support expansion;
- asymmetric tolerance: exact lower/upper expansion;
- relative tolerance: conservative exact expansion over interval extrema and zero when applicable;
- non-`EXACT` quantization: unsupported and therefore indeterminate.

The relation for each constraint is one of:

- `WITHIN` — the complete observed support is contained in the allowed interval;
- `OUTSIDE` — the complete observed support is disjoint from the allowed interval;
- `OVERLAPS_BOUNDARY` — support crosses or touches an excluded safety boundary;
- `UNKNOWN` — required telemetry is explicitly unknown or absent;
- `UNSUPPORTED` — the foundation cannot soundly interpret the observation semantics.

Aggregate status is:

- `SATISFIED` only when every required constraint is `WITHIN`;
- `VIOLATED` when any constraint is definitively `OUTSIDE`;
- `INDETERMINATE` when there is no definite violation but at least one constraint overlaps, is unknown, or is unsupported;
- `MODE_UNCOVERED` when the observed discrete mode has no declared envelope.

A definite violation dominates concurrent uncertainty. `SATISFIED` never means empirical proof that the world is safe; it means only that the supplied, revision-bound observations are wholly contained under the declared exact semantics.

## Failure-closed conditions

The foundation rejects or contains:

- forged Rule, Quantity, canonical projection, envelope, state, or assessment fingerprints;
- non-`HARD_FLOOR` rules;
- Rule clauses not classified as `SAFETY_INVARIANT`;
- non-interval allowed regions;
- tolerated or quantized safety boundaries;
- subject or ProblemRevision mismatch;
- dimensional or canonical-unit mismatch;
- missing observation provenance;
- duplicate modes, variables, constraints, rules, or quantities;
- binary floating-point metadata;
- non-exact observation quantization;
- unknown or missing telemetry;
- uncovered modes;
- attempts to set authority, dispatch, mode activation, solver execution, dynamics integration, or artifact acceptance flags.

## Explicit claim ceiling

S4.8 performs none of the following:

- ODE integration or physics solving;
- trajectory prediction;
- controller synthesis;
- fact or physical-state authority grant;
- effect authorization or dispatch;
- operational-mode activation;
- artifact acceptance;
- empirical safety proof;
- mutation of Rule, Quantity, Evidence, obligation, authority, or runtime state.

Later admission work may consume this assessment only through the existing AASM authority, effect, obligation, risk, and evidence planes. The S4.8 foundation itself remains inert and pre-admission.

## Qualification

The dedicated `aasm/engineering-safety-envelope-hybrid-state` gate compiles the model and schemas, runs a source-contract firewall, and executes an adversarial corpus covering exact containment, violation, boundary overlap, uncertainty, missing telemetry, uncovered modes, tolerance expansion, quantization, dimensional mismatch, forged identities, revision mismatch, provenance, schema closure, purity, and public/runtime non-exposure.
