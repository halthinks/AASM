# S5.5 Integrated Core/Conflict Pipeline

**Status:** pre-admission foundation and enforcement runtime  
**Semantic contract:** `aasm.core-conflict.v1`  
**Runtime contract:** `aasm.core-conflict.runtime.v1`

## Purpose

S5.5 gives AASM one backend-independent semantic path for conflict cores while preserving the exact external references and proof strength supplied or established at each stage.

Canonical pipeline:

`RAW -> NORMALIZED -> REDUCED -> RECHECKED`

Each non-raw stage binds its parent fingerprint. Every member preserves both the backend/external reference and AASM's normalized reference. Every member is bound to the problem semantic fingerprint that produced the conflict.

## Claim-strength firewall

S5.5 deliberately treats these as different claims:

- backend-reported core;
- conflict-preserving core;
- irreducible/subset-minimal core;
- minimum-cardinality core;
- minimum-weight core;
- budget-limited partial reduction.

There is no implication chain that silently upgrades one into another.

**Irreducible is not minimum-cardinality. Minimum-cardinality is not minimum-weight. A smaller core is not proof of any of them.**

`strongest_established_claim()` therefore returns only the exact claim explicitly established on the exact core.

## Provenance

`CoreProvenance` binds:

- problem revision identity;
- problem semantic fingerprint;
- solver backend and backend version;
- solver run identity;
- solver Evidence;
- optional external result identity.

Core transformations may not cross a problem revision or semantic fingerprint.

## Reduction

Reduction may only remove existing members. It may not introduce a new member under an existing normalized identity or mutate member identity. A normal reduction produces no established minimality guarantee. If a budget is exhausted, the output is explicitly marked `BUDGET_LIMITED_PARTIAL`; that state is never represented as minimum.

## Independent recheck

A conflict-preserving result must reproduce the conflict for the exact member set. Irreducibility additionally requires:

1. an independent recheck showing the complete core still conflicts; and
2. one independent removal recheck for every member showing the remaining set is satisfiable.

An `UNKNOWN` or `ERROR` removal result fails closed and cannot establish irreducibility.

## Minimum claims

Minimum-cardinality requires explicit Evidence plus a certificate that smaller cardinalities were exhaustively ruled out for the exact problem semantic fingerprint.

Minimum-weight is independent of minimum-cardinality. It requires every member to have a weight, an explicit objective/weight policy, Evidence, and a certificate establishing the global weight optimum for the exact problem semantic fingerprint.

S5.5 does not prescribe one solver algorithm for creating those certificates; it specifies what AASM is allowed to claim after evidence is supplied.

## Relationship to legacy calculus conflicts

The existing calculus `ConflictRecord` and `ExplanationRecord` remain valid. S5.5 does not rewrite legacy event/state history or reinterpret legacy `PROVEN_MINIMAL` records. It provides the more precise semantic pipeline that future adapters and qualification paths can use before projecting results into older surfaces.

## Relationship to S5.4 knowledge applicability

Recurring conflict patterns may become knowledge, but S5.5 does not grant reuse authority. The runtime authority ceiling explicitly requires S5.4 applicability for knowledge reuse. Historical recurrence, solver agreement, or a previously certified core cannot silently legalize a learned constraint in a changed target context.

## Authority ceiling

The S5.5 runtime grants:

- no solver-output authority;
- no self-upgrade of claim strength;
- no learned-constraint admission;
- no effect dispatch;
- no problem mutation;
- no bypass around S5.4 knowledge applicability.

Public and runtime admission remain `PRE_ADMISSION_ONLY` until the qualification gate passes on the publication branch.
