# Contributing to AASM

Thank you for considering a contribution. AASM is early-stage, so thoughtful feedback, tests, documentation improvements, bug reports, design critiques, and focused code contributions are all valuable.

## Before you start

For small bug fixes, tests, docs improvements, and clearly scoped refactors, feel free to open a pull request directly.

For large architectural changes, new authority semantics, new state-machine behavior, persistence formats, protocol changes, or changes that may break compatibility, please open an issue first. That gives the design a place to be discussed before significant implementation work is done.

## Development setup

```bash
git clone https://github.com/halthinks/AASM.git
cd AASM
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e '.[dev]'
pytest -q
```

## Pull request policy

A good PR should be small enough to review, explicit about its intent, and accompanied by evidence that it works.

Every PR should:

1. Explain the problem being solved.
2. Explain why the change belongs in AASM's core, an adapter, a profile, or documentation.
3. Describe the implementation approach and important tradeoffs.
4. Add or update tests for behavioral changes.
5. Keep existing public contracts stable unless the PR explicitly proposes a breaking change.
6. Call out changes to machine states, legal transitions, schemas, authority semantics, persistence, or protocol messages.
7. Update relevant documentation and examples.
8. Pass the repository test suite and CI.
9. Avoid unrelated formatting or refactoring noise.
10. Disclose meaningful AI-assisted code generation when it affects reviewability, and confirm that the contributor has actually reviewed and tested the submitted code.

## Review criteria

PRs are reviewed for:

- correctness
- clarity
- test coverage
- backward compatibility
- state-machine safety
- recovery behavior
- provenance implications
- authority/security implications
- documentation quality
- whether the abstraction is general enough for AASM rather than one narrow application

A maintainer may ask that a large PR be split into smaller changes.

## State-machine changes require extra care

Changes to machine state or transitions can affect every integration. A PR that modifies `MachineState`, transition legality, checkpoint semantics, authority, or event contracts should include:

- a transition rationale
- positive tests for newly legal behavior
- negative tests for behavior that must remain illegal
- migration notes if serialized state or public schemas change
- an explanation of rollback/recovery implications

## Compatibility policy

Until `1.0.0`, AASM may evolve quickly. Even so, breaking changes should be intentional and documented.

Prefer additive changes. When a breaking change is necessary, describe:

- the old behavior
- the new behavior
- why compatibility cannot reasonably be preserved
- any migration path available

## Development and release identity

AASM does **not** assign a new package version to every feature merge or architecture milestone.

- Git commit SHA identifies exact unreleased source.
- Named roadmap milestones/capabilities identify architecture work.
- Schema, protocol, ABI, and machine-contract versions evolve independently when their compatibility semantics require it.
- Package SemVer identifies a deliberately published, qualified distribution.
- Published tags and release artifacts are immutable.

Do not add new implementation-generation modules such as `runtime_v57.py`, `public_v57.py`, or `_runtime_v57_feature.py`. New implementation belongs under stable semantic module names. Existing version-numbered modules are historical/compatibility surfaces and will be consolidated deliberately behind stable facades rather than removed by mass rename.

Ordinary development commits must not change the package version. Version changes are explicit release operations and are checked by the repository version-policy gate.

See [`docs/VERSIONING.md`](docs/VERSIONING.md) for the full policy and migration rules.

## Tests

Run:

```bash
pytest -q
```

New behavior should normally have tests. Bug fixes should include a regression test when practical.

## Commits

There is no rigid commit-message format. Prefer concise imperative summaries such as:

```text
Add persistent checkpoint store
Reject unauthorized plan mutation
Document quorum authority semantics
```

Release-version commits are exceptional and should use an explicit release-oriented summary such as `Prepare AASM release X.Y.Z` or `Release AASM X.Y.Z` so the release policy is auditable.

## Code style

Keep the code readable and boring in the best sense:

- favor explicit types and data contracts
- avoid hidden global state
- avoid unnecessary dependencies
- keep algorithms independently testable
- separate policy from mechanism
- keep agent-provider-specific behavior out of the core when an adapter can contain it

## New dependencies

AASM currently has no runtime dependencies outside the standard library. New runtime dependencies should have a strong justification, a clear maintenance story, and a meaningful benefit that outweighs the added supply-chain and installation cost.

## Issues

When reporting a bug, include the smallest reproduction you can, expected behavior, actual behavior, Python version, and relevant traceback/output.

Feature requests are strongest when they describe the underlying use case rather than only prescribing an implementation.

## Security issues

Do **not** report security vulnerabilities in a public issue. See [`SECURITY.md`](SECURITY.md).

## Conduct

Participation in this project is governed by [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md).

## License

By contributing, you agree that your contributions will be licensed under the Apache License, Version 2.0 (`Apache-2.0`). See [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE).
