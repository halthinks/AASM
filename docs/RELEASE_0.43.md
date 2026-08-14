# AASM v0.43.0 Release Notes

**Semantic Conformance, Adversarial Domains, and Certification**

Released: 2026-08-14

## What this release changes

v0.43 adds a deterministic certification layer over the v0.42 reference-domain stress system while preserving the v0.41 domain-neutral engine as the active kernel.

The central new semantic distinction is explicit:

```text
PASS         all required observed checks passed
FAIL         at least one required observed check failed
INCONCLUSIVE no required observed check failed, but required evidence or enforcement is absent
```

AASM no longer needs to force every validation result into a boolean. Missing evidence is not success, and an architecture can explicitly say that a claim or subsystem is not yet certifiable.

## New certification contract

```text
aasm.certification.v1 / 0.1.0
```

The deterministic certification suite covers:

- the complete v0.42 reference-domain harness;
- solver/reuse safety and certificate-gated skipping;
- truth-maintenance and memory privacy/revocation;
- formal verification-strength requirements;
- the experimental SII participation plane.

Certification has harness-only authority and does not itself authorize reasoning, promote evidence, mutate canonical state, or establish the truth of arbitrary external conclusions.

## Experimental SII preview

v0.43 stages:

```text
aasm.sii.v1 / 0.2.0
stability = EXPERIMENTAL_CERTIFICATION_TARGET
```

The Symbiotic Intelligence Interface is the planned v0.44 participation/economic plane for replaceable intelligences operating through AASM.

Its design laws are:

1. the reasoner proposes; AASM measures;
2. utility may buy resources; utility never buys truth;
3. AASM returns compressed governed intelligence, not merely a reputation score.

The preview includes:

- stable proposer identities;
- structured proposal envelopes;
- typed reasoning consequences compiled into the existing v0.37 reasoning lifecycle;
- durable AASM-measured outcome records;
- bounded performance vectors;
- contextual ResourceLease projections;
- governed v0.40 context/reasoning-frontier access;
- durable savings attribution only through v0.41 reuse metrics.

The SII certification target adversarially tests producer-controlled fingerprints, identity reset, self-measurement, forged reuse telemetry, authority escalation, and repeated-outcome farming.

## Why SII is not yet active

The SII target intentionally reports `INCONCLUSIVE` for two unfinished enforcement boundaries:

1. measurement principal/authority must be resolved from durable governed actor identity rather than accepted as a caller assertion;
2. ResourceLease budgets/privileges must be enforced through the existing scheduler/resource/capability system.

Those are explicit v0.44 graduation gates. The release does not create `runtime_v43.py`, does not resurrect the original candidate `runtime_v42.py`, and does not create a second authority plane.

## Public surface

Package version:

```text
0.43.0
```

Adoption contract:

```text
aasm.adoption.v1 / 0.19.0
```

New CLI:

```bash
aasm certification-contract
aasm certify
aasm certify --target reference-domains
aasm certify --target solver-reuse
aasm certify --target truth-memory
aasm certify --target formal-verification
aasm certify --target sii-preview
aasm sii-contract
```

## Expected aggregate certification result

Until v0.44 graduation work is complete:

```text
core_status = PASS
status      = INCONCLUSIVE
```

`core_status` excludes explicitly experimental targets. A core failure is never masked by SII's experimental status.

## Kernel boundary

```text
package/public surface: 0.43.0
active kernel: runtime_v41.AASMEngine
v0.42 reference harness: retained
v0.43 certification: harness/public layer
v0.43 SII: experimental participation preview
```

No new scheduler, reducer, event log, truth store, or domain-specific kernel path is introduced in this release.

## Next release

**v0.44.0 — Symbiotic Intelligence Interface & Governed Intelligence Economics**

v0.44 is planned to bind measurement identity/authority into existing AASM governance, enforce ResourceLease budgets through existing resource/scheduler/capability paths, externalize scoring policy, expand adversarial economic tests, and require the SII certification target to graduate to `PASS` before activation.
