# AASM v0.48.0 — Cross-Run Certified Knowledge & Governed Long-Term Memory

AASM v0.48 extends the existing v0.40 memory, v0.41 reuse, v0.47 SII, and event-sourced authority planes across run boundaries without importing prior-run authority.

## Contracts

```text
package/public surface: 0.48.0
aasm.adoption.v1 / 0.24.0
aasm.knowledge.cross-run.v1 / 0.1.0
aasm.knowledge.cross-run.admission.v1 / 0.1.0
aasm.principal.cross-run-map.v1 / 0.1.0
aasm.certification.v1 / 0.2.0
aasm.sii.v1 / 0.3.0
license: Apache-2.0
```

## Delivered

- immutable cross-run knowledge envelopes with exact source-run provenance;
- explicit scope, privacy, environment, dependency, freshness, retention, and verification-strength applicability checks;
- deterministic receiving-run admission certificates carrying validator ID/version;
- ordinary Decision → POLICY/CONTROLLER authorization → Obligation → Evidence admission;
- no inheritance of source truth/authority;
- local semantic materialization only after receiving-run AUTHORIZED reasoning exists;
- ordinary v0.40 memory authorization/commit for all materialized knowledge;
- ordinary v0.41 reuse candidates and reuse certificates for cross-run execution reuse;
- cross-run validator/version provenance preserved inside the ordinary reuse certificate;
- receiving-run admitted revocation/supersession signals;
- revocation blocking already-hot reuse candidates;
- revocation tombstoning already-materialized local memories through the existing FORGET path;
- stable principal mapping with no authority/resource-entitlement transfer;
- SII reputation as separate reference accounting, never local authority or automatic compute entitlement;
- dependency-neutral conformance, adversarial tests, JSON schemas, CLI/public APIs, and dedicated CI;
- bounded TLA+ and Promela/SPIN assurance for the cross-run authority/privacy/revocation boundaries;
- all Apache-2.0 / PEP 639 / NOTICE packaging guarantees from v0.47.1 preserved.

## Non-goals

v0.48 does not make serialized foreign truth locally authoritative. It does not trust source-run POLICY merely because source provenance says POLICY. It does not use foreign SII reputation to grant local resource tiers. It does not claim the envelope format itself authenticates untrusted network transport.

## Architecture

```text
source AASM run
      |
CrossRunKnowledgeEnvelope
      |
      v
receiving applicability validator
      |
CrossRunAdmissionCertificate
      |
Decision / POLICY authorization / Obligation
      |
foreign Evidence
   +--+-------------------+
   |                      |
   v                      v
local v0.40 memory     v0.41 reuse candidate
(admission still      (ReuseCertificate still
 required)             required)
   |                      |
   +----------+-----------+
              |
       source signal admitted
              |
      revoke / supersede
              |
  block reuse + tombstone memory
```

## Safety laws

```text
FOREIGN AUTHORITY IS PROVENANCE, NEVER RECEIVING AUTHORITY.
FOREIGN SEMANTIC CONTENT REQUIRES LOCAL AUTHORIZED REASONING.
CROSS-RUN REUSE STILL REQUIRES THE EXISTING REUSE CERTIFICATE.
REVOCATION CHANGES EXECUTION/MEMORY ELIGIBILITY, NOT HISTORY.
CROSS-RUN SII REPUTATION NEVER GRANTS AUTHORITY OR RESOURCE ENTITLEMENT.
```

Next: **v0.49 Semantic Solver Release Candidate**.
