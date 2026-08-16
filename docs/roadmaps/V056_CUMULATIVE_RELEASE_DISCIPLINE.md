# AASM v0.56 — Historical Cumulative Work-Package Release Discipline

**Original date:** 2026-08-15  
**Current status:** **SUPERSEDED FOR FUTURE DEVELOPMENT** by [`docs/VERSIONING.md`](../VERSIONING.md)  
**Historical scope:** records the release discipline used to produce the immutable `v0.56.0` release and the original 56.1–56.5 work-package decomposition.

This file is retained because its work-package IDs and historical release reasoning are referenced by the Governed Semantic Evolution roadmap, execution ledger, source-lock materials, and release history. It no longer allocates future package versions or requires one package publication per work package.

## What remains binding

The following architectural properties survive unchanged:

1. Work-package dependency order remains meaningful where a later capability semantically depends on an earlier one.
2. Later work cannot claim a prerequisite capability until that prerequisite has a landed contract/runtime and the required qualification evidence.
3. The active public/runtime surface must preserve already released contracts and authority/truth boundaries.
4. Dedicated qualification gates grow cumulatively where appropriate; they do not silently drop earlier assertions.
5. Full CI, formal, solver/proof/optimization/authority, compatibility, and applicable exact-head gates remain mandatory before a package release.
6. Dormant or interrupted source files do not count as delivered capability.
7. Published tags/releases remain immutable.
8. No new work may weaken v0.55 semantic-evolution or v0.54 effect/solver authority boundaries.

## What is superseded

The old rule was:

> Every completed work package must be published as a distinct cumulative patch release before implementation of the next work package begins.

That rule caused package SemVer to double as architecture-milestone identity and development-progress identity. It is no longer used.

The superseding rule is:

> **Prerequisites must be semantically landed and qualified before dependent work relies on them. They do not need a separate package publication before dependent development can begin. Package SemVer advances only when a coherent externally meaningful release scope is deliberately frozen and qualified.**

Therefore the former mapping:

```text
56.2 -> v0.56.1
56.3 -> v0.56.2
56.4 -> v0.56.3
56.5 -> v0.56.4
```

is historical planning information, **not a reservation of package versions**.

The already-established `0.56.1` development target for Execution Profiles + Runtime Provenance is preserved because work on `main` had already adopted it before this policy change. No further package number is allocated merely because 56.3, 56.4, 56.5, or later architecture work begins.

## New identity model

```text
work package / capability milestone
        -> architecture identity

Git SHA
        -> exact development source identity

contract/schema/ABI version
        -> semantic compatibility identity

package SemVer + immutable tag
        -> deliberately published distribution identity
```

A work package may progress through:

```text
SOURCE_LOCKED
DESIGNED
CONTRACT_LANDED
RUNTIME_LANDED
TESTED
GATED
```

without forcing a package release at each stage. `RELEASED` is recorded only when the capability is actually exposed by an immutable published package release.

## Historical release boundary

Work package **56.1 — Normalized Solver Outcome v2** was published in immutable release `v0.56.0` and remains released history.

Work package **56.2 — Execution Profiles + Runtime Provenance** is being developed under the already-existing `0.56.1` target. Its qualification state is tracked by the execution ledger and exact-head `aasm/v56-provenance` / cumulative `aasm/v56` gates. Its completion does not reserve a new package number for 56.3.

## Canonical policy

For all future version/release decisions, [`docs/VERSIONING.md`](../VERSIONING.md) is authoritative. This file remains only to preserve the provenance of the earlier v0.56 cumulative-release plan and the stable work-package IDs that grew from it.
