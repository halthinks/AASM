# AASM v0.42.0 Release Notes

## Reference Domains & Reuse/Memory/Reasoning Stress Tests

v0.42.0 turns the v0.41 domain-neutral reuse/solver architecture into a stress-tested public release surface without creating a second runtime.

### New contract

```text
aasm.reference-domains.v1 / 0.1.0
aasm.adoption.v1 / 0.18.0
```

The package/runtime surface is `0.42.0`. The active engine remains `runtime_v41.AASMEngine`; the stable remote wire protocol remains `aasm.remote.v1 / 0.19.0`.

## Five deterministic reference domains

The offline harness now runs controlled scenarios for:

- constraint solving;
- software repair;
- research synthesis;
- formal reasoning;
- long-horizon memory.

These scenarios intentionally exercise different architectural boundaries: durable reuse after hot-index deletion, environment/dependency/freshness invalidation, non-idempotent effect safety, reasoning staleness, verification strength, principal privacy, memory revocation, certificate-gated execution skipping, and replay identity.

## Reuse assurance hardening

Stress implementation exposed a missing independent guard for `ReuseRequest.required_strength`. v0.42 validates the requested strength directly against the candidate `verification_strength`; a candidate carrying the same request fingerprint cannot bypass this check.

The runtime deliberately does not infer an ordering among proof-strength strings. Any allowed substitution relation must be explicit in a future contract.

## Public surfaces

Python:

```python
from aasm import REFERENCE_DOMAIN_IDS, reference_domain_contract, run_reference_domain_stress

report = run_reference_domain_stress()
```

CLI:

```bash
aasm reference-domain-contract
aasm reference-domain-stress
aasm reference-domain-stress --domain formal-reasoning
```

Schema:

```text
schemas/reference-domain-stress-report.schema.json
```

Documentation and example:

```text
docs/REFERENCE_DOMAIN_STRESS.md
examples/reference_domain_stress.py
```

## Correctness boundary

The reference domains are deterministic synthetic stress fixtures. Passing them demonstrates that the implemented AASM boundaries behave as specified under those fixtures. It does not certify arbitrary external domain data, scientific claims, mathematical statements, software diagnoses, or memories.

v0.43 is reserved for semantic conformance, adversarial domains, and explicit `PASS | FAIL | INCONCLUSIVE` certification semantics.
