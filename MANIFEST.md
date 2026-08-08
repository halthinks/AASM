# AASM source manifest policy

`main` is identified by its Git commit SHA. `FILE_LIST.txt` is the tracked inventory of source-controlled files and is checked in CI.

A tracked SHA-256 file is intentionally **not** maintained on `main`: any source change immediately makes such a file stale, and a checksum file cannot reliably attest to a moving branch. Instead, generate checksums from the exact checkout, tag, or release archive being distributed.

## Verify the tracked inventory

```bash
python scripts/release_manifest.py --check-file-list
```

If files were intentionally added or removed:

```bash
python scripts/release_manifest.py --write-file-list
```

## Generate SHA-256 checksums for an exact checkout

```bash
python scripts/release_manifest.py --sha256 SHA256SUMS.generated.txt
```

The output file is excluded from its own hash list. Publish that generated file alongside the corresponding immutable release/tag/archive, not as evidence for a moving branch.

## Integrity model

For development, record the Git commit SHA. For a release, record both the immutable Git tag/commit and the generated SHA-256 manifest. This keeps provenance reproducible without presenting stale checksums as current.
