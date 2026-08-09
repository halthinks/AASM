# AASM Profile Packages

## The four layers

AASM v0.22 uses four separate concepts:

1. **Package** — a distributable artifact containing profiles, adapters, schemas, migrations, documentation, examples, and conformance tests.
2. **Profile** — the versioned use-case contract inside a package: vocabulary, machine definition, evidence categories, policies, and adapter bindings.
3. **Binding** — the exact profile version, fingerprint, package identity, and user configuration attached to one AASM machine.
4. **Run** — the actual event-sourced execution history governed by that binding.

A package can contain one profile or a family of related profiles. A profile can be bound to many runs with different instance configuration.

## Is package design an art form?

Yes—within a disciplined engineering boundary.

A good package captures the smallest useful vocabulary for a class of work without embedding accidental assumptions. Its author decides:

- which decisions deserve explicit names;
- which obligations are persistent or conditional;
- what counts as acceptable evidence;
- what validators and explainers are appropriate;
- which conflicts may become hard constraints;
- how much domain detail belongs in the package versus run configuration;
- what can safely migrate between versions.

That is a design craft. Two packages can address the same use case with different decompositions, just as two programming languages, scientific protocols, or manufacturing systems can embody different philosophies.

AASM does not judge the taste of that design. It enforces the package contract, authority boundaries, persistence, evidence provenance, conformance, and migration rules.

## Do packages naturally evolve?

They may **evolve through a governed lifecycle**, but they do not silently rewrite themselves.

```text
repeated evidence or conflicts
          ↓
ProfileEvolutionProposal
          ↓
new package/profile version is authored
          ↓
conformance and domain validation
          ↓
explicit ProfileMigration
          ↓
authorized activation
          ↓
new immutable binding
```

The runtime may record an evidence-backed proposal that a profile should change. It may not manufacture a new authoritative contract and activate it without an explicit target version, fingerprint, migration, conformance result, and actor.

This distinction preserves replay and meaning. If a profile changed invisibly, an old event history could no longer be interpreted under the same rules.

## What can evolve automatically?

The **run** can adapt automatically within its bound profile:

- active decisions may change;
- obligations may enable or lock;
- conflicts may produce learned constraints;
- search may backjump or restart;
- fairness may force reconsideration.

Those are ordinary AASM state changes under a stable contract.

The **package contract** changes only through versioned evolution. A system may automatically produce a candidate proposal when evidence crosses a policy threshold, but activation remains explicit.

## Configuration is not package evolution

Changing a run-specific value does not necessarily create a new profile version.

Examples of configuration:

- a temperature threshold;
- a list of allowed sites;
- a review quorum;
- a simulation budget;
- a reporting format.

Examples of contract evolution:

- introducing a new decision namespace;
- changing the meaning of an obligation kind;
- replacing the evidence policy;
- changing an adapter interface;
- altering migration or fairness semantics.

AASM records configuration history separately from profile-version history.

## Package contents

A typical external package may look like:

```text
my-aasm-package/
├── pyproject.toml
├── aasm-package.json
├── profiles/
│   ├── standard.json
│   └── high-assurance.json
├── adapters/
│   ├── decisions.py
│   ├── obligations.py
│   ├── validation.py
│   ├── explanation.py
│   └── certification.py
├── migrations/
├── schemas/
├── examples/
├── tests/
└── README.md
```

Installed packages advertise profiles through the Python entry-point group:

```toml
[project.entry-points."aasm.profiles"]
standard = "my_package:standard_profile"
high_assurance = "my_package:high_assurance_profile"
```

Discovery loads only already-installed entry points. AASM never downloads or installs package code as a side effect of profile discovery.

## Authority boundary

A package may propose candidate models, obligations, validation results, explanations, and certificates. It may not:

- mutate `MachineSnapshot` directly;
- activate a decision;
- commit an obligation;
- authorize an external effect;
- create a hard constraint by itself;
- bypass Planner or configured authority;
- replace its own profile binding.

AASM remains the authority layer.
