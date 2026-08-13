# AASM v0.33.0 — Signed Provenance and Verifiable Exports

v0.33.0 makes completed AASM runs portable and independently checkable without trusting the original server or database.

## Delivered

- `aasm.provenance.v1 / 0.1.0`;
- canonical UTF-8 JSON export files;
- content-addressed manifest with exact byte counts and SHA-256 digests;
- detached HMAC-SHA256 signature envelope and signer identity;
- offline verification from the export directory plus verification key;
- selective-disclosure sub-manifests retaining parent-manifest SHA-256 lineage;
- runtime and CLI export/verify/select surfaces;
- tamper, wrong-key, and lineage regression tests.

The authoritative runtime path is unchanged. Export is read-only over durable machine history and snapshots.

## Compatibility

```text
package/runtime: 0.33.0
adoption:         aasm.adoption.v1 / 0.9.0
trace:            aasm.trace.v1 / 0.1.0
provenance:       aasm.provenance.v1 / 0.1.0
remote:           aasm.remote.v1 / 0.19.0
```

## Next

**v0.34.0 — Distributed Recovery Certification**.
