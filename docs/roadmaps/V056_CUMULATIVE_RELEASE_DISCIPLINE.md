# AASM v0.56 — Cumulative Work-Package Release Discipline

**Date:** 2026-08-15  
**Status:** Canonical amendment to `GOVERNED_SEMANTIC_EVOLUTION_ROADMAP.md` for v0.56 delivery granularity only.

This document does **not** change the content, order, dependencies, claim ceilings, or acceptance requirements of work packages 56.1–56.5. It changes only when a completed work package becomes an immutable GitHub release.

## Rule

A completed v0.56 work package may not remain merely `GATED` while implementation advances to the next package. Each package must finish through the active public surface, exact-head gates, immutable GitHub tag/release, reproducible artifacts, release documentation, and canonical ledger before the next package begins.

This operationalizes the project rule:

> `proceed` means fully done on GitHub clean.

## Cumulative release mapping

| Work package | Capability | Immutable release boundary |
|---|---|---|
| 56.1 | Normalized Solver Outcome v2 | `v0.56.0` |
| 56.2 | Execution Profiles + Runtime Provenance | `v0.56.1` |
| 56.3 | Reproducibility Certification | `v0.56.2` |
| 56.4 | Governed Knowledge Applicability/Application | `v0.56.3` |
| 56.5 | Integrated Core/Conflict Pipeline | `v0.56.4` |

Every patch is cumulative: v0.56.N contains and preserves all earlier v0.56 work-package contracts.

## Invariants

1. Work-package order remains 56.1 → 56.2 → 56.3 → 56.4 → 56.5.
2. No later work package can be credited before its predecessor is immutably released.
3. Root `aasm` points to the latest released cumulative v0.56 public surface.
4. Earlier patch tags remain immutable parents.
5. The dedicated `aasm/v56` gate grows cumulatively; it never drops earlier v0.56 assertions.
6. The normal full CI/formal/RC/proof/optimization/authority/parent-release gates remain mandatory on the same exact release SHA.
7. A patch release must not weaken v0.55 semantic-evolution or v0.54 effect/solver authority boundaries.
8. Dormant future-work source files do not count as delivered capability.

## Final v0.56 family completion

`v0.56.4` is the point at which the complete original v0.56 roadmap goal—Truthful Solver Evidence + Governed Knowledge Application—is satisfied. The subsequent roadmap remains v0.57 External Machine Supervision + Artifact/Entity Lineage.
