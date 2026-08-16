# AASM Versioning and Development Identity

AASM separates **release identity**, **development identity**, **contract identity**, and **architecture milestone identity**.

## Policy

**Package SemVer identifies deliberately published AASM distributions. It does not count development milestones or feature merges.**

Ordinary development must not increment the package version. Exact development state is identified by Git commit SHA. Architecture work is identified by named milestones/capabilities. Public schemas, wire protocols, ABIs, machine contracts, and other compatibility-sensitive contracts keep their own independent versions.

Published tags and release artifacts are immutable.

## Identity planes

| Identity | Purpose | Example |
|---|---|---|
| Git SHA | exact development source | `fffc488...` |
| architecture milestone | planning / dependency ordering | `external-machine-supervision` |
| capability identity | runtime feature discovery | `solver.runtime-provenance` |
| contract identity | semantic compatibility family | `aasm.solver.outcome.v2` |
| contract revision | compatible/incompatible evolution inside a contract family | contract-defined |
| package SemVer | published distribution | `0.56.0` |
| release tag | immutable source identity for a published distribution | `v0.56.0` |

A change in one identity plane does not automatically require a change in another.

## Development rules

1. Feature merges, architecture milestones, tests, documentation, refactors, and internal implementation changes do **not** automatically bump package SemVer.
2. Git SHA is the authoritative identity of an unreleased source tree.
3. Future roadmap work uses named milestone IDs instead of reserving package versions in advance.
4. New implementation modules must use stable semantic names. Do not create new chronology modules such as `runtime_v57.py`, `public_v57.py`, or `_runtime_v57_feature.py` merely because development advanced.
5. Existing version-numbered implementation modules are grandfathered historical/compatibility surfaces. They must be consolidated deliberately behind stable semantic modules; do not mass-delete or mass-rename them.
6. Contract/schema/ABI versions remain independent and may evolve when their own compatibility semantics require it.
7. A package version change is a release operation and must be explicit, reviewed by the release gates, and tied to one exact Git SHA.
8. Published releases are never rewritten, force-moved, or republished under the same version.

## Release cadence

AASM uses **release-on-coherent-contract**, not version-per-feature.

Several completed capability milestones may ship together in one release. A release is cut when its public scope is coherent and the applicable qualification gates pass.

Typical lifecycle:

```text
released tag
    |
    v
main development (identified by Git SHA)
    |
    +-- capability milestone A
    +-- capability milestone B
    +-- compatibility work
    +-- qualification
    |
    v
release-scope freeze
    |
    v
release candidate, if used
    |
    v
qualified immutable release tag
```

Patch releases are for actual compatible fixes/backports or urgent security/safety corrections, not ordinary development checkpoints.

## Development build identity

Build tooling may expose a PEP 440 development identifier derived from Git, for example:

```text
0.57.0.dev23+g1a2b3c4
```

Such an identifier is generated from source history; developers should not manually commit a new package version for every development checkpoint.

Package version and Git revision must remain separate observable fields.

## Stable module architecture

Chronology must move out of the active implementation graph over time.

Target shape:

```text
src/aasm/
  runtime/
  solver/
  optimization/
  knowledge/
  authority/
  verification/
  contracts/
  compat/
```

Versioned protocol identifiers such as `aasm.capability.abi.v1` are **not** implementation chronology and must not be flattened.

Existing Python paths such as `runtime_vNN` may remain as forwarding compatibility shims after their implementation has moved behind stable semantic modules. Historical replay fixtures may also retain versioned names where the historical identity is meaningful.

## Compatibility migration rule

For any version-numbered implementation path that has been public or may have escaped into serialized state:

```text
create stable semantic facade
        |
        v
switch internal imports to stable facade
        |
        v
prove behavior/replay compatibility
        |
        v
move implementation behind stable facade
        |
        v
turn old path into compatibility shim
```

Do not start with a mass rename.

## Roadmap rule

Historical releases keep their actual release numbers.

Unreleased future architecture is named by capability/milestone, for example:

```text
external-machine-supervision
refinement-and-verification-planning
engineering-semantics
uncertainty-readiness-conformance
cross-capability-stress-corpus
hosted-foundation-review
```

A package version is assigned only when a release scope is deliberately frozen.

## CI enforcement

The repository version-policy gate must reject:

- newly added version-numbered implementation modules outside an explicit compatibility/history location;
- ordinary commits that change the package version without an explicit release operation;
- future roadmap sections that once again reserve package versions as architecture milestone numbers.

The gate intentionally does **not** reject existing historical modules or independently versioned contracts.

## Release-source-of-truth rule

For a stable release, the following must resolve to one release identity and one exact source SHA:

```text
Git tag
package metadata
wheel/sdist metadata
release manifest/history
GitHub Release
current-release documentation
```

Development documentation may separately report the current Git SHA and active milestone set.

## Adoption rule

This policy is additive and does not rewrite AASM history. Existing published releases remain immutable, and the already-active development target at the moment this policy is adopted may be completed without inventing another intermediate package number. From this point forward, architecture progress is tracked by milestones/capabilities and Git history rather than by continuously incrementing package SemVer.
