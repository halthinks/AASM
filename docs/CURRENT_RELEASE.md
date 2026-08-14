# AASM v0.43.0 — Semantic Conformance, Adversarial Domains, and Certification

AASM v0.43 is a certification/public-surface release over the existing domain-neutral v0.41 solver runtime and the v0.42 reference-domain harness. It does not introduce `runtime_v43.py`, a second scheduler, a second reducer, or another truth store. The active engine remains `runtime_v41.AASMEngine`.

Contracts:

```text
aasm.adoption.v1 / 0.19.0
aasm.certification.v1 / 0.1.0
aasm.sii.v1 / 0.2.0              # experimental v0.44 target
aasm.reference-domains.v1 / 0.1.0
aasm.reuse.v1 / 0.1.0
aasm.reuse.certificate.v1 / 0.1.0
aasm.solver.loop.v1 / 0.1.0
aasm.memory.hierarchical.v1 / 0.1.0
aasm.capability.abi.v1 / 0.1.0
aasm.semantic.dependencies.v1 / 0.1.0
aasm.reasoning.admission.v1 / 0.1.0
aasm.remote.v1 / 0.19.0
```

## Certification semantics

Every v0.43 certification target terminates as one of:

- `PASS`: all required observed checks passed;
- `FAIL`: at least one required observed check failed;
- `INCONCLUSIVE`: no required observed check failed, but required evidence or enforcement is absent.

The harness has `CERTIFICATION_HARNESS_ONLY` authority. It does not promote evidence, authorize reasoning, mutate canonical state, or claim that arbitrary external domain conclusions are true.

## Core certification targets

The release certifies deterministic AASM behavior for:

1. the complete v0.42 reference-domain suite;
2. solver/reuse boundaries including freshness, dependency, effect, and verification-strength rejection;
3. truth-maintenance and governed-memory privacy/revocation;
4. formal verification-strength and certificate-gated reuse.

The aggregate report exposes `core_status` separately from experimental targets so unfinished experiments cannot be mistaken for either core failure or core proof.

## Experimental SII preview

v0.43 also stages `aasm.sii.v1 / 0.2.0` as the next release's participation/economic plane.

The SII preview preserves these laws:

1. the reasoner proposes; AASM measures;
2. utility may buy resources; utility never buys truth;
3. successful participation returns better governed context/search/compute, not authority.

Its adversarial profile already requires rejection of producer-controlled semantic fingerprints, stable-identity resets, self-measurement, forged reuse-metrics credit, resource-to-authority promotion, and repeated outcome farming.

The SII profile intentionally remains `INCONCLUSIVE` in v0.43 because two enforcement boundaries are not yet complete:

- measurement principal/authority still needs durable binding to governed AASM actor identity;
- computed `ResourceLease` values still need enforcement through existing scheduler/resource/capability paths.

These are v0.44 graduation gates, not hidden TODOs.

## Correctness boundary

v0.43 certifies observed contract behavior in deterministic fixtures. It does not establish the semantic truth of arbitrary external inputs, domain packages, model outputs, theorem statements, research claims, or real-world conclusions.

The following are explicitly invalid equivalences:

```text
synthetic fixture PASS != arbitrary external answer is correct
self-attestation       != certification
missing evidence       != PASS
resource utility       != epistemic authority
similarity             != safe reuse
```

Release identity:

```text
package/public surface: 0.43.0
kernel engine: runtime_v41.AASMEngine
adoption: aasm.adoption.v1 / 0.19.0
certification: aasm.certification.v1 / 0.1.0
SII preview: aasm.sii.v1 / 0.2.0
reference domains: aasm.reference-domains.v1 / 0.1.0
remote: aasm.remote.v1 / 0.19.0
next: v0.44.0 Symbiotic Intelligence Interface & Governed Intelligence Economics
```
