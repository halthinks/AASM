# PR-3C/3D — Bounded Effect Capability Foundation

**Program:** `physical-authority-capabilities` / PHY-01  
**Package development target:** 0.56.1  
**Parent prerequisite:** qualified PR-3A/3B authority-domain + authority-lease foundation  
**Semantic contract:** `aasm.effect.capability.v1`  
**Runtime contract:** `aasm.effect.capability.runtime.v1`  
**Status:** implementation/qualification candidate; not yet the PR-3H Effect authorization boundary

## Purpose

PR-3C/3D turns a broad, exclusive authority lease into a narrower transferable capability object without creating a second permission evaluator or Effect lifecycle.

The capability is a **bounded authority artifact**, not an Effect authorization by existence.

## Bound identity

`EffectCapability` binds:

```text
domain_id
authority_lease_id
workspace_id
scope_id
subject_id
holder_principal_id
issuer_principal_id
allowed_operations
numeric_bounds
valid_from
expires_at
authority_epoch
problem_revision_id
external_revision_id
remaining_delegation_depth
revocation_generation
parent_capability_id
parent_capability_fingerprint
parent_revocation_generation
```

## Non-amplification law

For a delegated child capability:

```text
child.operations ⊆ parent.operations
child.numeric_interval(name) ⊆ parent.numeric_interval(name)
child retains every parent numeric constraint
child.validity ⊆ parent.validity
child.workspace/scope == parent.workspace/scope
child.subject == parent.subject
child.authority_epoch == parent.authority_epoch
child.problem_revision == parent.problem_revision
child.external_revision == parent.external_revision
child.remaining_delegation_depth <= parent.remaining_delegation_depth - 1
```

A child may add an additional named numeric restriction because doing so narrows rather than amplifies authority.

## Root capability law

A root capability requires:

```text
existing active AuthorityLease
issuer == active lease holder
existing scoped physical.effect-capability.issue authority
operations ⊆ lease.permitted_effect_classes
validity ⊆ lease effective interval
epoch == lease epoch
exact domain/lease workspace, scope, subject and revision identity
```

A root capability may delegate to another known principal, but the issuer remains the active lease holder.

## Numeric bounds

The foundation implements deterministic **named closed numeric intervals** only:

```text
minimum <= value <= maximum
```

The parameter name carries external semantic meaning. AASM does not yet interpret physical units here.

Therefore:

```text
numeric_units = NOT_INTERPRETED_UNTIL_QUANTITY_CONTRACT
```

This prevents PR-3 from silently inventing dimensional semantics that belong to the later quantity/unit system.

## Revocation and stale descendant fencing

Capability revocation is append-only and advances the effective revocation generation.

Each child captures:

```text
parent_capability_id
parent_capability_fingerprint
parent_revocation_generation
```

A child is active only while the parent remains active and the captured generation still equals the parent's effective generation.

Revocation generation is query-time correct: a revocation at time `T` does not invalidate historical state queried for `t < T`, but invalidates the capability and descendants for `t >= T`.

Revoking the underlying AuthorityLease also invalidates every capability rooted in that lease without rewriting any capability record.

## Authority firewall

PR-3C/3D preserves:

```text
EffectCapability existence != effect.authorize
AuthorityLease existence != effect.authorize
resource availability != authority
FactAuthority != effect authority
scoped capability-reference existence != authority by itself
parallel authority evaluator = NONE
parallel Effect lifecycle = NONE
Effect dispatch = NONE
machine-state mutation = NONE
```

The runtime uses existing `authorize_scoped_request(...)` for:

```text
physical.effect-capability.issue
physical.effect-capability.delegate
physical.effect-capability.revoke
```

## Explicitly not implemented here

PR-3C/3D does not yet provide:

- integration with existing `authorize_effect` or `execute_effect`;
- command-time stale-epoch fencing at the Effect boundary;
- semantic preemption;
- safety-controller epoch advancement;
- unit-aware or dimension-aware numeric bounds;
- operation-specific payload schema interpretation;
- automatic actuation rights from a capability object.

Those boundaries remain PR-3E/F/G/H and later quantity/physical-semantics work.

## Qualification target

Dedicated gate:

```text
aasm/effect-capability
```

The gate must prove:

- operation allow-list non-amplification;
- numeric interval non-amplification, including rejection when a child drops a parent constraint;
- validity/scope/revision/epoch fencing;
- delegation-depth decrease;
- root lease-holder/scoped-authority requirements;
- parent revocation-generation propagation;
- underlying lease revocation propagation;
- no core machine-state mutation;
- no existing Effect authority from capability existence;
- SQLite restart and exact replay.

Public admission occurs only after this dedicated gate passes. Package SemVer remains 0.56.1; adoption-contract identity advances independently if the surface is admitted.
