# AASM Compatibility Policy

AASM is **pre-1.0 experimental software**. The project nevertheless defines a supported adoption surface so applications do not have to depend on every historical module or internal implementation detail.

## Version identities

AASM has three separate identities:

| Identity | Current value | Meaning |
|---|---|---|
| Package/runtime | `0.30.0` | Python distribution and current server implementation |
| Adoption contract | `aasm.adoption.v1 / 0.6.0` | Supported imports, methods, commands, endpoints, and runbooks |
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

## Framework adapter compatibility

The first optional adapter is `aasm.langgraph.v1 / 0.1.0`. It is EXPERIMENTAL and supports LangGraph `>=1.2,<2`. The core `aasm-runtime` install has no mandatory LangGraph dependency.

The supported boundary is explicit:

- LangGraph owns graph topology, node execution, dynamic routing, interrupts, and checkpoints;
- AASM owns durable machine truth, decisions, obligations, evidence, effects, conflicts, replay, and recovery;
- thread/run binding derives from `configurable.thread_id` and optional run identity;
- checkpoint state must not become competing AASM authority;
- adapter code must not mutate AASM tables or snapshots directly.

A future adapter version can change independently of the remote wire protocol and package version.


## Adapter conformance compatibility

AASM v0.30.0 adds `aasm.adapter.conformance.v1 / 0.1.0`. The contract is EXPERIMENTAL and independent of the package, LangGraph adapter, and remote-protocol versions.

A conformance driver must declare supported scenarios and authority ownership. The canonical requirements are AASM event history for machine truth and AASM authority for decisions, effects, workers/leases, and recovery. Missing required coverage produces `INCONCLUSIVE`; direct Store mutation, duplicate authority, invalid history, or replay mismatch produces `FAIL`.

The in-process mutation audit is a diagnostic hook, not a sandbox. Compatibility with the conformance API does not imply that untrusted adapter code is safe to execute in the AASM server process.

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
