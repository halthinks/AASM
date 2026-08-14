# Cross-Run Certified Knowledge & Governed Long-Term Memory

AASM v0.48 adds a receiving-run admission boundary for knowledge produced in another durable AASM run.

```text
aasm.knowledge.cross-run.v1 / 0.1.0
aasm.knowledge.cross-run.admission.v1 / 0.1.0
aasm.principal.cross-run-map.v1 / 0.1.0
```

## Core law

> **A prior run may provide provenance and evidence. It never exports authority.**

A `CrossRunKnowledgeEnvelope` fingerprints its source run, machine and scope, source memory/evidence/artifact lineage, declared environment and dependency compatibility, privacy, retention/freshness, verification strength, content, and source authority provenance. Its authority-transfer field is permanently `NEVER`.

## Receiving-run admission

The receiving run performs deterministic applicability checks before any admission proposal exists:

- source run must be foreign;
- target scope must be explicitly allowed;
- USER/AGENT privacy must match the receiving principal;
- declared environment fingerprint must match;
- declared dependency fingerprints must be available;
- freshness and retention must still be active;
- verification strength must satisfy the receiving requirement;
- source authority is provenance only.

A valid `CrossRunAdmissionCertificate` is still not authority. Admission then follows ordinary AASM control:

```text
foreign envelope
      ↓
receiving validation
      ↓
CrossRunAdmissionCertificate
      ↓
DecisionRecord(PROPOSED)
      ↓
POLICY / CONTROLLER authorization
      ↓
ObligationRecord
      ↓
worker commit
      ↓
foreign knowledge Evidence
```

## Long-term memory materialization

An admitted foreign envelope is Evidence. It does not bypass v0.40 memory governance.

`materialize_cross_run_knowledge()` only proposes an ordinary memory operation. POLICY/CONTROLLER authorization and ordinary memory commit remain required.

Foreign `SEMANTIC` knowledge has an additional boundary: it cannot become local semantic memory unless the receiving run supplies local reasoning artifacts already in `AUTHORIZED` state. This prevents a source run's truth decision from becoming the receiving run's truth by serialization.

## Reuse

Cross-run reuse uses the existing v0.41 `ReuseCandidate` and `ReuseCertificate` path. v0.48 does not create another cache/certificate system.

The first v0.48 contract uses exact semantic payload equality and preserves v0.41's exact verification-strength rule. Cross-run candidate metadata is copied into the ordinary `ReuseCertificate`, including:

- source and receiving run IDs;
- envelope ID/fingerprint;
- receiving admission validator ID/version;
- `authority_inherited = false`.

## Revocation and supersession

Source-run revocation/supersession signals are never applied automatically. The receiving POLICY/CONTROLLER must admit the matching source signal.

Once admitted:

- `cross_run_knowledge_report()` marks the envelope REVOKED/SUPERSEDED;
- existing hot reuse candidates are blocked by the v0.48 runtime before a certificate can be used;
- locally materialized memories tied to the envelope are tombstoned through the existing v0.40 FORGET decision/authorization/commit path.

This means revocation changes execution and memory projection behavior, not merely UI status.

## Principal identity and SII reputation

Cross-run principal mapping is explicit and stable:

```text
(source_run_id, source_principal_id) → local_principal_id
```

Mappings require POLICY/CONTROLLER admission and carry:

```text
authority_transfer            = NEVER
resource_entitlement_transfer = NEVER
```

An `SII_REPUTATION` envelope must name its exact source principal and match the admitted mapping. Reputation is stored in `CROSS_RUN_REFERENCE_ONLY` accounting Evidence with:

```text
truth_authority       = NONE
resource_entitlement  = NONE
used_by_sii_resource_lease = false
```

It does not modify local SII principal authority or local v0.47 resource tiers.

## Transport boundary

The envelope contract is not a network authentication protocol. For untrusted transport, callers must use authenticated transport or signed provenance/export mechanisms before asking the receiving run to admit the envelope.

## Formal invariants

`AASMCrossRunKnowledge.tla` and `aasm_cross_run_knowledge.pml` independently check:

- `ForeignAuthorityNeverInherited`;
- `AdmissionRequiredBeforeMaterialization`;
- `AdmissionRequiredBeforeReuse`;
- `RevocationBlocksReuse`;
- `RevocationInvalidatesMaterializedMemory`;
- `PrivateKnowledgeNeverLeaksAcrossPrincipal`;
- `ReputationNeverGrantsAuthority`;
- `ReputationNeverGrantsResourceEntitlement`.

## CLI

```bash
aasm cross-run-knowledge-contract
aasm cross-run-knowledge-conformance
```
