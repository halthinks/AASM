# AASM Release Process

AASM releases are built from an exact `main` commit after ordinary CI and formal assurance succeed.

## Release chain

```text
main commit with a package-version change
  ↓
Python 3.11–3.13 + PostgreSQL + Compose + clean-wheel CI
  ↓
TLA+/TLC + Promela/SPIN formal gate
  ↓
exact pinned build toolchain
  ↓
independent build A + independent build B
  ↓
byte-identical wheel and source-distribution comparison
  ↓
metadata and package-content inspection
  ↓
clean virtual environment install and CLI smoke
  ↓
historical-release-report.json
  ↓
SHA256SUMS.txt + release-manifest.json
  ↓
immutable release tag created by the GitHub Release API
  ↓
exact remote tag and asset read-back verification
  ↓
optional PyPI Trusted Publisher job
```

The release workflow is `.github/workflows/release.yml`.

## Release intent

A successful ordinary CI run does not automatically republish the current package.

The workflow releases only when:

- the package version in `pyproject.toml` differs from the parent commit; or
- an operator explicitly dispatches the Release workflow.

A successful non-version commit publishes `aasm/release=success` with the description that no release is required. It does not recreate, upload, or overwrite assets.

## Version preparation

Before release, update all visible version surfaces:

- `pyproject.toml`;
- `src/aasm/__init__.py`;
- `README.md`;
- `ROADMAP.md`;
- `CHANGELOG.md`;
- release documentation;
- version-sensitive regression tests.

The source-contract check rejects inconsistent versions.

## Pinned build tools

The source distribution declares exact build-backend requirements:

```text
setuptools==83.0.0
wheel==0.47.0
```

CI and the release workflow install exact build frontends:

```text
build==1.5.0
twine==6.2.0
```

The workflow does not depend on an unspecified newest build tool.

## Local artifact verification

```bash
python -m pip install "build==1.5.0" "twine==6.2.0"
export SOURCE_DATE_EPOCH="$(git show -s --format=%ct HEAD)"
export PYTHONHASHSEED=0

rm -rf build dist-a dist-b *.egg-info src/*.egg-info
python -m build --outdir dist-a
rm -rf build *.egg-info src/*.egg-info
python -m build --outdir dist-b

python scripts/release_artifacts.py compare-builds dist-a dist-b
python -m twine check dist-a/*
python scripts/release_artifacts.py verify-wheel \
  "$(find dist-a -maxdepth 1 -name '*.whl' -print -quit)"
python scripts/release_artifacts.py verify-sdist \
  "$(find dist-a -maxdepth 1 -name '*.tar.gz' -print -quit)"
```

Both builds must have the same artifact names, sizes, and SHA-256 values. A byte difference fails the release.

## Historical release report

`release-history.json` records the exact commits for maintained historical releases that predate release automation.

The current release workflow does **not** attempt privileged creation of old tags or old releases. That operation may be rejected when an integration lacks permission over workflow-bearing history and is not necessary to validate the current package.

Instead it writes `historical-release-report.json`:

```text
VERIFIED                    tag exists at the recorded commit
PENDING_OWNER_PUBLICATION   tag is absent; owner publication remains optional
MISMATCH                    tag exists at the wrong commit; release fails
```

This turns the old-tag boundary into durable evidence. It does not hide it and does not let it invalidate unrelated current-release work.

## Current release

After CI succeeds on a version-changing `main` commit, the release workflow:

1. checks out the exact tested commit;
2. requires `aasm/ci-summary=success` on that commit;
3. requires `aasm/formal-assurance=success` on that commit;
4. builds two independent distributions with the pinned toolchain;
5. requires byte-identical wheel and source-distribution files;
6. inspects metadata and package contents;
7. installs the wheel in a clean virtual environment;
8. executes the installed adoption contract and a runbook;
9. writes `historical-release-report.json`;
10. generates `SHA256SUMS.txt` and `release-manifest.json`;
11. asks the GitHub Release API to create `vVERSION` at the exact commit only when it does not already exist;
12. reads the tag ref and every release asset back;
13. verifies the exact asset-name set, byte sizes, and SHA-256 digests;
14. publishes `aasm/release=success` only after remote verification;
15. uploads the same files as a temporary workflow artifact for the optional PyPI job.

The release workflow never overwrites an existing GitHub Release asset. There is no `--clobber` path. If a release or asset was published incorrectly, increment the package version and publish a new immutable release.

## PyPI Trusted Publisher

PyPI publication uses credential-free OpenID Connect through:

```text
pypa/gh-action-pypi-publish@release/v1
```

The PyPI project must be configured to trust:

```text
owner:       halthinks
repository:  AASM
workflow:    release.yml
environment: pypi
```

Then enable one of these gates:

- repository variable `AASM_PUBLISH_PYPI=true`; or
- manual Release workflow dispatch with `publish_pypi=true`.

No long-lived PyPI token is stored in the repository.

The first PyPI publication is an external account-level operation: the pending `aasm-runtime` publisher/project binding must exist on PyPI before the workflow can authenticate. This external binding is deliberately isolated from GitHub Release publication.

## Release assets

Every current binary release includes:

```text
aasm_runtime-VERSION-py3-none-any.whl
aasm_runtime-VERSION.tar.gz
historical-release-report.json
SHA256SUMS.txt
release-manifest.json
```

The JSON manifest records package name, version, tag, commit SHA, byte counts, and SHA-256 values for the wheel, source distribution, and historical report. The remote verifier additionally checks the manifest and checksum files themselves as published assets.

## Failure handling

A failed build, formal gate, reproducibility comparison, clean install, tag check, remote digest check, or release upload does not justify moving an existing tag or overwriting a file.

Repair the source, increment the version when immutable artifacts may already exist, and run the complete release chain again. Missing historical tags remain `PENDING_OWNER_PUBLICATION`; mismatched historical tags require owner investigation.
