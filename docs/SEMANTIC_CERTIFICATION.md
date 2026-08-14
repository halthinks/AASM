# AASM v0.43 Semantic Conformance & Adversarial Certification

## Purpose

v0.42 proved that the existing AASM solver/reuse/memory/reasoning stack can survive deterministic offline stress fixtures across several very different reference domains.

v0.43 adds a stricter question:

> Given an explicit target and explicit evidence, what is AASM actually justified in certifying?

The answer is always one of:

- `PASS` — every required observed check passed;
- `FAIL` — at least one required observed check failed;
- `INCONCLUSIVE` — no observed check failed, but required evidence or enforcement is missing.

`INCONCLUSIVE` is a first-class terminal result. Missing evidence is never silently converted to success.

## Contract

```text
aasm.certification.v1 / 0.1.0
```

The certification harness is not a new truth store or runtime kernel. Its declared authority is `CERTIFICATION_HARNESS_ONLY`; the active engine remains `runtime_v41.AASMEngine`.

It makes no general claim that arbitrary external data, model output, domain package, theorem, or conclusion is true. It certifies only the deterministic AASM contract behavior actually exercised by the selected profile.

## Profiles

### Reference domains

Runs the complete v0.42 reference-domain suite and requires every declared check to pass.

### Solver/reuse

Adversarially checks:

- durable reuse surviving hot-index deletion;
- certificate-gated execution skipping;
- freshness rejection;
- dependency-fingerprint rejection;
- rejection of non-idempotent effects;
- rejection of insufficient verification strength.

### Truth/memory

Checks that ordinary AASM truth-state and memory-state transitions remain authoritative:

- stale reasoning invalidates reuse;
- stale state remains durable;
- private memory is isolated by principal;
- private memory cannot be reused by another principal;
- tombstone/revocation invalidates reuse;
- revocation remains durable.

### Formal verification

Checks that a weaker verification-strength label cannot satisfy an exact stronger requirement, that the required-strength candidate is accepted, and that execution skipping still flows through validated reuse.

This is a contract-path certification. It is not a theorem that an arbitrary external solver is sound.

### SII preview

The experimental Symbiotic Intelligence Interface is deliberately included as an adversarial target before it becomes an active runtime surface.

The profile currently verifies that:

- a proposer cannot supply its own semantic fingerprint;
- stable-principal identity-reset attempts are rejected;
- a proposer cannot score its own outcome;
- forged reuse telemetry receives no savings credit;
- a ResourceLease never promotes authority;
- one proposal cannot be counted as multiple scoreable outcomes.

The same profile deliberately returns `INCONCLUSIVE` for two v0.44 graduation gates:

1. measurement-principal authority is not yet durably bound to an authenticated/governed AASM actor;
2. ResourceLease values are not yet enforced through the existing scheduler/capability plane.

That is expected behavior. v0.43 is designed to say **not certified yet** when the architecture has not supplied the required evidence or enforcement.

## CLI

```bash
aasm certification-contract
aasm certify
aasm certify --target solver-reuse
aasm certify --target sii-preview
```

A full v0.43 run should report:

```text
core_status = PASS
status      = INCONCLUSIVE
```

The combined status is inconclusive only because the explicitly experimental SII preview has unresolved v0.44 graduation gates. A failure in any core target changes `core_status` to `FAIL`.

## Certification boundary

The following equivalences are forbidden:

```text
synthetic fixture passed != arbitrary real-world answer is correct
self-attestation         != certification
missing evidence         != PASS
resource utility         != epistemic authority
similarity               != safe reuse
```

This distinction is the main semantic purpose of v0.43.
