# AASM Release Process

AASM releases are immutable and tied to an exact tested `main` commit.

## Required gates

```text
main commit
  ↓
Python 3.11 / 3.12 / 3.13
  + full pytest suite
  + optional LangGraph integration
  + adapter conformance
  + PostgreSQL
  + Docker Compose
  + clean installed wheel
  ↓
TLA+/TLC + Promela/SPIN
  ↓
aasm/ci-summary = success
aasm/formal-assurance = success
  ↓
reproducible double build
  ↓
immutable GitHub tag + release assets
  ↓
remote tag/asset size/SHA-256 verification
  ↓
aasm/release = success
```

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

A release rerun never repairs an existing version in place. Existing tags are not moved and assets are not overwritten. A changed artifact requires a new package version.

## Current release notes

The workflow publishes human-readable notes from:

```text
docs/CURRENT_RELEASE.md
```

Each release also has a versioned `docs/RELEASE_X.Y.md` document.

## Historical tags

Maintained pre-automation commits in `release-history.json` are audited. Missing old tags may be recorded as `PENDING_OWNER_PUBLICATION`; a real tag/commit mismatch is a failure.

## Source-distribution gate

The source archive must be self-contained enough to run its bundled smoke contract outside a Git checkout. Missing required schemas, formal models, profiles, runbooks, workflows, examples, release scripts, or tests fail the gate.

## PyPI Trusted Publisher

PyPI publication uses OIDC Trusted Publisher configuration and no long-lived repository token. It is separately gated by `AASM_PUBLISH_PYPI=true` or an explicit manual dispatch. GitHub release publication and verification remain independent of PyPI availability.
