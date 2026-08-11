# AASM Compatibility Policy

AASM is **pre-1.0 experimental software**. The project nevertheless defines a supported adoption surface so applications do not have to depend on every historical module or internal implementation detail.

## Version identities

AASM has three separate identities:

| Identity | Current value | Meaning |
|---|---|---|
| Package/runtime | `0.28.1` | Python distribution and current server implementation |
| Adoption contract | `aasm.adoption.v1 / 0.4.0` | Supported imports, methods, commands, endpoints, and runbooks |
| Remote protocol | `aasm.remote.v1 / 0.19.0` | Compatibility identity used by existing remote clients |

A package release does not automatically require a wire-protocol version change.

## Support classes

### SUPPORTED

Documented golden-path behavior declared by `aasm.adoption.v1`.

A breaking change to this surface requires:

- a changelog entry;
- an explicit version change;
- migration or deprecation guidance when practical;
- updated contract tests;
- a clean-wheel installation test.

### EXPERIMENTAL

Available for evaluation but may change between pre-1.0 releases. Experimental does not mean undocumented or untested; it means no long-term compatibility promise has been made yet.

### INTERNAL

No compatibility promise. Applications should not import versioned runtime modules, mutate snapshots directly, write AASM tables directly, or depend on undocumented event payload details.

## Canonical public path

Inspect the current contract:

```bash
aasm adoption-contract
```

Or:

```python
from aasm import public_api_contract

contract = public_api_contract()
```

The contract names:

- supported package imports;
- supported `AASMEngine` methods;
- supported CLI commands;
- supported inspection surfaces;
- supported HTTP endpoints;
- reference application and local-stack entry points;
- executable operator runbooks;
- reproducible distribution and historical-release evidence policies.

## Snapshot and event compatibility

AASM replays the authoritative event stream through the production reducer. New fields are expected to have backward-compatible defaults when older snapshots are deserialized.

Compatibility does not authorize silent rewriting of historical events. Migrations must preserve provenance and must not make an old history claim that a newer event occurred.

## Profile/package compatibility

A profile identity is the tuple:

```text
profile_id + profile_version + fingerprint
```

Changing a profile contract requires a new semantic version and fingerprint. Activation requires conformance and an explicit migration rather than silent replacement.

## Release artifacts

An immutable release is identified by:

```text
immutable release tag
+ exact commit SHA
+ wheel/sdist SHA-256
+ historical-release-report.json SHA-256
+ release-manifest.json
```

The release tag is created through the GitHub Release API at the exact tested commit. The workflow then reads the resulting tag ref back and fails if it does not resolve to that commit.

AASM v0.28.1 requires two independent distribution builds to produce byte-identical wheel and source-distribution files. After publication, the workflow reads back the complete remote asset set and verifies every name, byte count, and SHA-256 digest.

Release files are never overwritten with different bytes under the same version. An existing release is verified, not repaired in place. A correction requires a new package version.

Historical tags that predate automated publishing are evidence, not a side effect of the current release. `historical-release-report.json` records:

- `VERIFIED` when the tag resolves to the recorded commit;
- `PENDING_OWNER_PUBLICATION` when the tag is absent and owner-level publication is still required;
- `MISMATCH` when an existing tag resolves to a different commit.

A missing historical tag does not invalidate a correctly built current release. A mismatch does.

## Deprecation before 1.0

For a supported surface, AASM will normally:

1. document the replacement;
2. retain the old surface for at least one subsequent minor release when practical;
3. emit a clear warning where runtime warnings are appropriate;
4. remove it only with an explicit changelog entry.

Security or correctness defects may require faster removal. Such changes will be called out prominently.

## What this policy does not guarantee

This policy does not make domain evidence true, guarantee external-service behavior, or certify third-party adapters. It defines how the AASM control-plane interface itself evolves.
