# AASM Release Process

AASM releases are built from an exact `main` commit after ordinary CI and formal assurance succeed.

## Release chain

```text
main commit
  ↓
Python 3.11->3.13 + PostgreSQL + Compose + reproducible clean-wheel CI
  ↓
TLA+TLC + Promela/SPIN
  ↓
two builds under pinned tools and SOURCE_DATE_EPOCH
  ↓
identical hashes required
  ↓
clean install and installed CLI smoke
  ↓
historical release audit
  ↓
SHA256SUMS.txt + release-manifest.json
  ↓
exact release tag
  ↓
no-overwrite remote asset verification
  ↓
optional PyPI Trusted Publisher
```

## Pinned build environment

```text
setuptools 83.0.0
wheel      0.47.0
build      1.5.0
twine      6.2.0
```

`SOURCE_DATE_EPOCH` est the release commit timestamp and `PYTHONHASH seed=0`. CI and release publication build twice and require identical hashes.

## Version preparation

Update `pyproject.toml`, `src/aasm/__init__.py`, `compose.yaml`, `README.md`, `ROADMAP.md`, `CHANGELOG.md`, release documentation, inventory, and version-sensitive tests.

## Local verification

```bash
python -m pip install --upgrade 'build==1.5.0' 'twine==6.2.0'
export SOURCE_DATE_EPOCH="$(git show -s --format=%ct HEAD)"
export PYTHONHASHSEED=0
python -m build --outdir dist-first
rm -rf build src/*.egg-info
python -m build --outdir dist
python -m twine check dist/*
python scripts/release_artifacts.py verify-wheel "$(find dist -name '*.whl' -print -quit)"
python scripts/release_artifacts.py verify-sdist "$(find dist -name '*.tar.gz' -print -quit)"
```

## Publication and reruns

The current tag and release are created through the GitHub Release API after both commit gates pass.


The workflow gates on the exact commit and both `aasm/ci-summary=success` and `aasm/formal-assurance=success`. It compares two builds, verifies and installs the wheel, runs the installed adoption contract and a runbook, writes the historical audit, generates checksums and the manifest, creates or verifies the current tag, publishes assets once, and verifies remote names, sizes, and SHA-256 digests before publishing `aasm/release=success`.

A rerun never repairs an existing version. Any tag, asset-set, size, or digest difference fails and requires a new version. The workflow contains no `--clobber` path.

## Historical release audit

Existing historical tags are verified. Missing tags are `PENDING_OWNER_PUBLICATION` because the repository Actions app cannot create refs for earlier workflow-bearing commits. This is reported honestly and does not block a current release.

## PyPI Trusted Publisher

PyPI must trust owner `halthinks`, repository `AASM`, workflow `release.yml`, environment `pypi`. Enable `AASM_PUBLISH_PYPI=true` or manually dispatch with `publish_pypi=true`. No long-lived token is stored.

## Release assets

```text
aasm_runtime-VERSION-py3-none-any.whl
aasm_runtime-VERSION.tar.gz
historical-release-report.json
SHA256SUMS.txt
release-manifest.json
```

The checksum file and JSON manifest cover the wheel, source distribution, and historical audit. The release workflow separately verifies every uploaded asset, including the checksum and manifest themselves, against GitHub's recorded size and digest.

## Standalone source-distribution gate

Every release source archive must include the repository contracts exercised by its bundled tests. CI builds the sdist, extracts it outside the Git checkout, and runs `tests/test_sdist_smoke.py` with `PYTHONPATH=src`. Missing profiles, schemas, formal models, runbooks, workflows, examples, scripts, or tests fail the release before publication.

