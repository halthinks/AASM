# AASM source and release manifest policy

`main` is identified by its Git commit SHA. `FILE_LIST.txt` is the tracked source inventory and is checked in CI.

A moving branch cannot carry a permanently current checksum file. Checksums are generated only for an exact build/tag/release.

## Verify the tracked inventory

```bash
python scripts/release_manifest.py --check-file-list
```

When files are intentionally added or removed:

```bash
python scripts/release_manifest.py --write-file-list
```

## Verify release artifacts

```bash
python -m build
python scripts/release_artifacts.py verify-wheel dist/*.whl
python scripts/release_artifacts.py verify-sdist dist/*.tar.gz
```

## Generate immutable release manifests

```bash
python scripts/release_artifacts.py manifest dist \
  --checksums dist/SHA256SUMS.txt \
  --json dist/release-manifest.json \
  --commit-sha "$(git rev-parse HEAD)"
```

The generated files belong beside the wheel and source distribution on the immutable GitHub Release.

## Release identity

A release is identified by all of:

```text
immutable vVERSION release tag
exact Git commit SHA
wheel SHA-256
source-distribution SHA-256
release-manifest.json
```

The GitHub Release API creates the missing release tag at the exact tested commit. The workflow immediately reads the tag ref back and verifies the target.

An existing tag must never be moved to a different commit. Existing PyPI files cannot be replaced. Corrections require a new package version.

## Historical release map

`release-history.json` records exact commits for maintained releases created before automated release publishing. The release workflow may create a missing source-only GitHub Release at the recorded commit and refuses any tag/commit mismatch.
