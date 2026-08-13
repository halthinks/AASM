# AASM v0.34.0 — Distributed Recovery Certification

v0.34.0 adds `aasm.recovery.v1 / 0.1.0`, an executable deterministic failure-injection certificate over the existing worker, lease, persistence, and effect paths.

Scenarios:

- worker crash;
- lease expiry and reclaim;
- stale completion rejection;
- duplicate delivery rejection;
- database restart persistence;
- supervisor loss and reclaim;
- external effect `UNKNOWN` followed by explicit reconciliation.

A report passes only when every scenario reaches one valid authority/effect outcome or an explicit reconciliation boundary. No second scheduler, lease system, effect ledger, or recovery database is introduced.

```text
package/runtime: 0.34.0
adoption:         aasm.adoption.v1 / 0.10.0
recovery:         aasm.recovery.v1 / 0.1.0
remote:           aasm.remote.v1 / 0.19.0
next:             v0.35.0 Semantic Problem Model Foundations
```
