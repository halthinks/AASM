# PR-3C/3D — Exact-Head Qualification Checkpoint

**Program:** `physical-authority-capabilities` / PHY-01  
**Child slice:** PR-3C/3D bounded effect capability  
**Package target:** 0.56.1  
**Expected adoption surface after admission:** `aasm.adoption.v1 / 0.32.7`

This file is a qualification checkpoint, **not** a declaration that PR-3C/3D is GATED.

The bounded capability slice may be promoted only when the same exact Git head passes:

```text
aasm/effect-capability
aasm/physical-authority
aasm/state-authority
aasm/external-machine
aasm/machine-transition
aasm/machine-postcondition
aasm/v56
aasm/v56-provenance
aasm/formal-assurance
aasm/ci-summary
```

plus the inherited solver/proof/optimization/scoped-authority gates required by the deliberate release workflow.

The qualification must preserve these ceilings:

```text
EffectCapability existence != effect.authorize
AuthorityLease existence != effect.authorize
child rights ⊆ parent rights
parent/lease revocation fences descendants
numeric units are not interpreted yet
semantic preemption remains PR-3G
effect authorization integration remains PR-3H
parallel authority evaluator = NONE
parallel Effect lifecycle = NONE
```

If any exact-head gate fails, the child slice remains an implementation candidate until the specific failure is repaired and the matrix passes on a later head.
