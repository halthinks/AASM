# AASM source and release manifest policy

`main` is identified by its Git commit SHA. `FILE_LIST.txt` is the tracked source inventory and is checked in CI.

A moving branch cannot carry a permanently current checksum file. Checksums are generated only for an exact build, tag, and release.

## Verify the tracked inventory

```bash
python scripts/release_manifest.py --check-file-list
```

When files are intentionally added or removed:

```bash
python scripts/release_manifest.py --write-file-list
```

## Verify reproducible distributions

```bash
export SOURCE_DATE_EPOCH="$(git show -s --format=%ct HEAD)"
export PYTHONHASHSEED=0
python -m build --outdir dist-a
rm -rf build *.egg-info src/*.egg-info
python -m build --outdir dist-b
python scripts/release_artifacts.py compare-builds dist-a dist-b
python scripts/release_artifacts.py verify-wheel dist-a/*.whl
python scripts/release_artifacts.py verify-sdist dist-a/*.tar.gz
```

A release candidate is invalid unless both builds are byte-identical.

## Generate immutable release evidence

After writing `historical-release-report.json`:

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
historical-release-report.json SHA-256
release-manifest.json
exact remote asset set and byte sizes
```

The GitHub Release API creates a missing release tag at the exact tested commit. The workflow immediately reads the tag ref and every asset back and verifies the target, name, size, and SHA-256 digest.

An existing tag must never be moved to a different commit. Existing GitHub or PyPI files cannot be replaced. Corrections require a new package version.

## Historical release map

`release-history.json` records exact commits for maintained releases created before automated release publishing. The release workflow does not create those old tags. It emits `historical-release-report.json` and treats an absent tag as `PENDING_OWNER_PUBLICATION`, an exact tag as `VERIFIED`, and a wrong tag target as `MISMATCH`.
