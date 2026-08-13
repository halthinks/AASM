# Changelog

Detailed history through v0.27.0 is preserved in [`CHANGELOG_0.27_AND_EARLIER.md`](CHANGELOG_0.27_AND_EARLIER.md). Git history and immutable release tags preserve the complete source history for later releases.

## [0.32.0] - 2026-08-12

### Runtime/Formal Trace Conformance

- added `aasm.trace.v1 / 0.1.0` lossless production-event projection;
- added `aasm.trace.semantic.v1 / 0.1.0` semantic witness checking;
- preserved exact event IDs, source sequences, raw source mappings, and per-event SHA-256 digests;
- added deterministic source-trace, projection, semantic-report, and trace-corpus fingerprints;
- made unknown transitions explicitly `UNSUPPORTED` instead of silently dropping them;
- rejected snapshot-only input as insufficient evidence of transition history;
- linked semantic counterexamples to exact source event IDs and pre/post-state fingerprints;
- added CLI and inspection surfaces for trace projection and semantic checking;
- added JSON schemas and bounded TLA+/Promela trace models;
- advanced `aasm.adoption.v1` to `0.8.0`;
- retained `aasm.scopes.v1 / 0.1.0` and `aasm.remote.v1 / 0.19.0`.

## [0.31.0] - 2026-08-12

### Hierarchical Decision Scopes

- added `aasm.scopes.v1 / 0.1.0`;
- added permanent root plus strategy, architecture, implementation, workstream, and custom scopes;
- added scope-local models, inherited effective models, explicit override policy, and validated cross-scope dependencies;
- added causal cross-scope backjumping preserving unrelated sibling subtrees;
- added scoped restart retaining parents, evidence, pinned decisions, certified hard knowledge, and append-only history;
- added atomic multi-scope candidate activation and legacy-flat root migration;
- added Python, CLI, HTTP, Control Center, schema, TLC, and SPIN surfaces;
- retained one authoritative machine and one event/reducer/store path.

## [0.30.0] - 2026-08-11

Added the framework-neutral Adapter Conformance Kit with eight black-box scenarios, real LangGraph coverage, replay verification, provenance checks, direct-storage-write detection, duplicate-authority detection, and `PASS | FAIL | INCONCLUSIVE` reports.

## [0.29.0] - 2026-08-11

Added the thin LangGraph adapter while preserving LangGraph graph/checkpoint ownership and placing durable authority, obligations, evidence, effects, conflict learning, replay, and recovery under AASM.

## [0.28.x] - 2026-08-11

Added one-command local operation, executable runbooks, immutable release evidence, reproducible double builds, exact remote asset verification, and a self-contained source distribution.
