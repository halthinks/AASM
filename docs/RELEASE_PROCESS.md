# AASM Release Process

AASM releases are deliberate, immutable publication events tied to one exact tested `main` commit. Ordinary development does **not** publish a package merely because CI becomes green or because an architecture milestone is complete.

See [`VERSIONING.md`](VERSIONING.md) for the separation between Git development identity, architecture/capability identity, contract identity, and package SemVer.

## Development versus release

```text
ordinary main development
  ↓
Git SHA identifies exact source
  + named capability milestones
  + independently versioned schemas / ABIs / contracts
  ↓
CI + compatibility + formal qualification
  ↓
NO AUTOMATIC PACKAGE RELEASE
```

A package release begins only through an explicit `workflow_dispatch` of the `Release` workflow with `confirm_release=true`.

## Required release gates

```text
deliberate release intent
  ↓
exact current main commit
  ↓
Python 3.11 / 3.12 / 3.13
  + full pytest suite
  + optional LangGraph integration
  + adapter conformance
  + PostgreSQL
  + Docker Compose
  + clean installed wheel
  ↓
parent compatibility + solver/authority/resource qualification
  ↓
TLA+/TLC + Promela/SPIN
  ↓
all required exact-head status contexts = success
  ↓
version-policy check
  + strict FILE_LIST tracked-file inventory
  + development/release contract check
  ↓
reproducible double build
  ↓
new GitHub tag + release assets
  ↓
remote tag/asset size/SHA-256 verification
  ↓
aasm/release = success
```

The strict tracked-file inventory belongs at this release boundary. It is intentionally not a per-feature development checkpoint; `FILE_LIST.txt` is regenerated and reviewed when release scope freezes.

## Required exact-head contexts

The release workflow currently requires the applicable status contexts on the exact release SHA, including:

```text
aasm/ci-summary
aasm/formal-assurance
aasm/semantic-solver-rc
aasm/proof-claims
aasm/solution-pools
aasm/optimization
aasm/scoped-authority
aasm/solver-learning
aasm/v54
aasm/v55
aasm/v56
aasm/v56-provenance
```

A new architecture milestone does not get a new package number merely to create another status context. Qualification contexts may evolve independently from SemVer.

## Pinned build environment

```text
setuptools 83.0.0
wheel      0.47.0
build      1.5.0
twine      6.2.0
```

`SOURCE_DATE_EPOCH` is derived from the exact release commit and `PYTHONHASHSEED=0`. The wheel and source distribution are built twice and their bytes must match.

## Release assets

```text
aasm_runtime-VERSION-py3-none-any.whl
aasm_runtime-VERSION.tar.gz
historical-release-report.json
SHA256SUMS.txt
release-manifest.json
```

The release workflow reads the remote tag and every published asset back from GitHub and verifies exact names, byte counts, and SHA-256 digests.

## No-repair rule

A published version is never repaired in place. Existing tags are not moved and assets are not overwritten. A changed published artifact requires a new deliberate package release.

The workflow refuses to publish when the target tag already exists.

## Current release notes and candidate notes

`docs/CURRENT_RELEASE.md` describes the **latest actually published release**.

A future release may have a versioned candidate document, such as `docs/RELEASE_0.56.1.md`, while it is being developed. Candidate documentation must clearly say that it is unreleased and may not make publication claims before the tag/assets exist.

At release freeze, the selected candidate scope is promoted into current release notes as part of the deliberate release change.

## Historical tags

Maintained pre-automation commits in `release-history.json` are audited. Missing old tags may be recorded as `PENDING_OWNER_PUBLICATION`; a real tag/commit mismatch is a failure.

Historical releases remain immutable even after the development versioning policy changes.

## Source-distribution gate

The source archive must be self-contained enough to run its bundled smoke contract outside a Git checkout. Missing required schemas, formal models, profiles, runbooks, workflows, examples, release scripts, or tests fail the gate.

## PyPI Trusted Publisher

PyPI publication uses OIDC Trusted Publisher configuration and no long-lived repository token. It remains separately gated by the release workflow input/policy. GitHub release publication and verification remain independent of PyPI availability.

## Release-version authority

Package SemVer is changed only as part of a deliberate release-scope decision. Development does not continuously edit it.

For an unreleased source tree, the authoritative identity is:

```text
package development target + exact Git SHA
```

For a published release, the following must agree:

```text
Git tag
package metadata
wheel/sdist metadata
release manifest/history
GitHub Release
CURRENT_RELEASE documentation
```

No architecture milestone is allowed to acquire package-release authority merely by being complete.
