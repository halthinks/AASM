# AASM Release Process

AASM releases are built from an exact `main` commit after ordinary CI and formal assurance succeed.

## Release chain

```text
main commit
  ↓
Python 3.11–3.13 + PostgreSQL + Compose + clean-wheel CI
  ↓
TLA+/TLC + Promela/SPIN formal gate
  ↓
wheel and source distribution
  ↓
metadata and package-content inspection
  ↓
clean-environment install and CLI smoke
  ↓
SHA256SUMS.txt + release-manifest.json
  ↓
annotated Git tag
  ↓
GitHub Release assets
  ↓
optional PyPI Trusted Publisher job
```

The release workflow is `.github/workflows/release.yml`.

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

## Local artifact verification

```bash
python -m pip install --upgrade build twine
python -m build
python -m twine check dist/*

python scripts/release_artifacts.py verify-wheel \
  "$(find dist -maxdepth 1 -name '*.whl' -print -quit)"

python scripts/release_artifacts.py verify-sdist \
  "$(find dist -maxdepth 1 -name '*.tar.gz' -print -quit)"

python scripts/release_artifacts.py manifest dist \
  --checksums dist/SHA256SUMS.txt \
  --json dist/release-manifest.json \
  --commit-sha "$(git rev-parse HEAD)"
```

## Historical tags

`release-history.json` records the exact commits for maintained historical releases that predate release automation.

The release workflow creates missing annotated tags and source-only GitHub Releases for those commits. It refuses to move a tag that already points somewhere else.

## Current release

After CI succeeds on `main`, the release workflow:

1. checks out the exact tested commit;
2. waits for `aasm/formal-assurance=success` on that same commit;
3. builds and verifies the distributions;
4. installs the wheel in a clean virtual environment;
5. executes the installed adoption contract and a runbook;
6. creates the annotated `vVERSION` tag;
7. creates the GitHub Release;
8. attaches wheel, source distribution, checksums, and manifest;
9. publishes `aasm/release=success` on the commit.

If the version tag already exists at a different commit, the workflow fails. The version must be bumped.

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

The first PyPI publication is an external account-level operation: the pending `aasm-runtime` publisher/project binding must exist on PyPI before the workflow can authenticate.

## Release assets

Every current binary release includes:

```text
aasm_runtime-VERSION-py3-none-any.whl
aasm_runtime-VERSION.tar.gz
SHA256SUMS.txt
release-manifest.json
```

The JSON manifest records package name, version, tag, commit SHA, byte counts, and SHA-256 values.

## Failure handling

A failed build, formal gate, clean install, tag check, or release upload does not justify moving an existing tag or overwriting a PyPI file.

Repair the source, increment the version when immutable artifacts may already exist, and run the complete release chain again.
