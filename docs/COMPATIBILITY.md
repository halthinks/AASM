# AASM Compatibility Policy

AASM is **pre-1.0 experimental software**. The project nevertheless defines a supported adoption surface so applications do not have to depend on every historical module or internal implementation detail.

## Version identities

AASM has three separate identities:

| Identity | Current value | Meaning |
|---|---|---|
| Package/runtime | `0.28.2` | Python distribution and current server implementation |
| Adoption contract | `aasm.adoption.v1 / 0.4.1` | Supported imports, methods, commands, endpoints, and runbooks |
| Remote protocol | `aasm.remote.v1 / 0.19.0` | Compatibility identity used by existing remote clients |

A package release does not automatically require a wire-protocol version change.

## Support classes

### SUPPORTED

Documented golden-path behavior declared by `aasm.adoption.v1`.

A breaking change to this surface requires a changelog entry, an explicit version change, migration or deprecation guidance when practical, updated contract tests, and a clean-wheel installation test.

### EXPERIMENTAL

Available for evaluation but may change between pre-1.0 releases.

### INTERNAL

No compatibility promise. Applications should not import versioned runtime modules, mutate snapshots directly, write AASM tables directly, or depend on undocumented event payload details.

## Canonical public path

```bash
aasm adoption-contract
```

```python
from aasm import public_api_contract
contract = public_api_contract()
```

## Snapshot, event, and profile compatibility

AASM replays the authoritative event stream through the production reducer. Migrations preserve provenance and do not rewrite historical events. A profile identity is `profile_id + profile_version + fingerprint`; changing it requires a new version, conformance, and an explicit migration.

## Release artifacts

A release is identified by its immutable release tag, exact commit SHA, wheel/sdist SHA-256, and `release-manifest.json`.

The workflow uses a **no-move policy** for tags and a **no-overwrite policy** for assets. An existing tag must resolve to the recorded commit; the asset set, every digest, and every byte count must match. Missing or changed assets fail. Corrections require a new package version.

The build toolchain is exactly pinned, and `SOURCE_DATE_EPOCH` is derived from the commit so reruns reproduce the same Python distributions.

## Historical release references

`release-history.json` records exact maintained pre-automation commits. `historical-release-report.json` verifies existing historical tags and records missing tags as `PENDING_OWNER_PUBLICATION`. Missing older refs do not block the current binary release and are not falsely claimed as published.

## Deprecation before 1.0

Supported replacements are documented and normally retain the old path for at least one subsequent minor release when practical. Correctness or security defects may require faster removal.

## What this policy does not guarantee

This policy does not make domain evidence true, guarantee external-service behavior, or certify third-party adapters.

## Source-distribution contract

Beginning with v0.28.2, the source distribution includes the repository-level profiles, schemas, formal models, runbooks, workflows, examples, scripts, and tests required by its standalone smoke gate. This packaging promise does not make internal modules part of the supported Python API.
