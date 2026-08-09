# AASM v0.22 Domain-Neutral Extension Contract

## Goal

The extension contract allows an arbitrary use case to supply domain meaning without adding that domain to the AASM kernel.

```text
domain package
    vocabulary · adapters · validators · migrations
                         ↓
                  stable contracts
                         ↓
AASM kernel
    state · authority · evidence · constraints · locks
    fairness · backjumping · restart · replay · effects
```

The domain defines what decisions, obligations, evidence, and artifacts mean. AASM defines what they are allowed to change.

## `AASMProfile`

A profile is immutable by `(profile_id, profile_version, fingerprint)`. It declares:

- target AASM contract;
- machine definition identifier;
- decision namespaces;
- obligation, evidence, and artifact kinds;
- independent adapter bindings;
- policies and capabilities;
- migrations;
- an evolution policy.

The built-in profiles are:

- `aasm.bare` — minimal contract for applications that already own domain interpretation;
- `aasm.evolve` — iterative, conflict-learning execution without domain assumptions.

## `AASMPackageManifest`

A package manifest identifies the distribution containing one or more profiles. Package version and profile version are separate because one package release may update documentation or adapters without changing every profile contract.

## Independent adapter protocols

v0.22 defines five optional protocols:

```text
DecisionBackend
    proposes a CandidateModel

ObligationAdapter
    proposes obligations enabled by a candidate model

SemanticValidator
    evaluates execution evidence

ConflictExplainer
    proposes a causal explanation

ConstraintCertifier
    certifies whether a projected constraint deserves a trust level
```

No adapter receives machine-mutation authority. Adapter imports require explicit opt-in. Profile discovery performs no network installation and no adapter execution.

## Solver neutrality

`DecisionRequest` and `CandidateModel` do not assume SAT, SMT, MILP, an LLM, or a human. A backend can use any method. Before activation, the v0.22 runtime validates:

- decision identity and status;
- subject/namespace consistency;
- parent requirements;
- pinned assignments;
- active hard constraints;
- cross-model fairness.

A backend selects candidates. The kernel decides whether a candidate is admissible.

## Generic semantic-result envelope

Every domain validator can return `SemanticResultEnvelope` with one of:

```text
PASS
LOCAL_DEFECT
INFORMATION_GAP
ASSUMPTION_CONFLICT
EVIDENCE_CONFLICT
POLICY_CONFLICT
FATAL
```

The envelope contains producer identity, subjects, claims, observations, evidence, artifacts, optional conflict data, confidence, scope, and metadata. It is JSON-serializable, fingerprinted, and stored durably without forcing one evidence ontology.

## Conformance

`ProfileConformanceKit` checks:

- profile/package structure;
- AASM contract compatibility;
- immutable identity/fingerprint behavior;
- adapter-role declarations;
- package/profile agreement;
- serialization round-trip stability;
- optional adapter protocol and determinism probes;
- semantic-result round-trip stability.

Conformance is necessary but not sufficient for domain correctness. A syntactically valid thermal validator can still use a bad physical model. Domain evidence remains the responsibility of its producer and certifier.

## Binding and evolution

`AASMEngine.bind_profile()` records the exact profile and package fingerprints plus run configuration. Rebinding the same immutable profile may update instance configuration. Replacing the contract requires an explicit `ProfileMigration`.

`ProfileEvolutionProposal` is advisory. `activate_profile_evolution()` requires:

- a currently bound profile;
- an eligible proposal;
- an exact target profile and fingerprint;
- a migration from the active version to the target version;
- conformance;
- an authorized actor under the profile policy.

A profile never modifies itself in place.

## CLI

```bash
aasm profiles
aasm profile-describe aasm.evolve
aasm profile-validate profile.json
aasm package-validate package.json
aasm profile-conformance profile.json --package package.json
aasm profile MACHINE_ID --store runs.db
aasm profile-bind MACHINE_ID --store runs.db --profile aasm.evolve
aasm candidate-validate MACHINE_ID --store runs.db --candidate candidate.json
aasm decision-request MACHINE_ID --store runs.db
aasm semantic-result-validate result.json
aasm semantic-result-record MACHINE_ID --store runs.db --result result.json
aasm semantic-results MACHINE_ID --store runs.db
```

## Non-goals

The v0.22 core does not require:

- Planner/Builder/Verifier;
- SAT or SMT;
- an LLM or model provider;
- GitHub or a source repository;
- a particular artifact or evidence type;
- one user interface;
- automatic package installation;
- silent self-evolution.
