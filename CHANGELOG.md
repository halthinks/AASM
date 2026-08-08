# Changelog

All notable user-visible changes to AASM will be documented here.

The project uses semantic-versioning intent while the public API remains experimental before 1.0.

## [0.3.0] - 2026-08-07

### Added

- durable external-effect records with explicit proposal, authorization, execution, failure, unknown-outcome, and reconciliation lifecycle
- machine-scoped idempotency keys and duplicate-proposal suppression
- persisted effect attempts, results, errors, evidence, authority, and retry policy
- crash recovery that converts in-flight effects to `UNKNOWN` instead of blindly retrying
- explicit reconciliation API for ambiguous external outcomes
- `aasm effects` CLI inspection, effect JSON schema, documentation, and example

### Safety semantics

- recorded successful effects are never re-invoked by AASM
- retries reuse the original idempotency key
- unknown outcomes require reconciliation unless retry-on-unknown is explicitly enabled

## [0.2.0] - 2026-08-07

### Added

- event-sourced authoritative write path for machine creation, transitions, metadata patches, and checkpoint restoration
- `Store` persistence protocol with `MemoryStore` and crash-safe `SQLiteStore` implementations
- atomic SQLite event append + materialized snapshot updates using WAL mode
- `AASMEngine.resume()` and `recover_unfinished()` for process restart recovery
- deterministic event replay with canonical-state equality tests
- persisted checkpoints that can be restored by a later process
- durable runtime CLI commands: `runs`, `inspect`, and `replay`
- durable-run example and crash/recovery scenario documentation
- versioned durable event JSON schema

### Compatibility

- existing v0.1 `AASMEngine(problem)` and `transition()` call sites remain valid; in-memory persistence remains the default

## [0.1.0] - 2026-08-07

### Added

- explicit AASM machine states and legal transition table
- deterministic algorithm-selection router
- dependency graph planning, topological ordering, shortest-path search, and relaxation
- checkpoint and backtracking support
- dynamic-programming memoization store
- max-flow/min-cut resource allocation
- adversarial verifier
- generic agent protocol and function-agent adapter
- controller, autonomous, quorum, and hierarchical authority policies
- Planner/Builder, swarm, and human/tool protocol adapters
- six orchestration profiles
- JSON schemas for problem, state, transitions, and agent messages
- test suite and multi-agent example
- Codex/agent-oriented `SKILL.md`
- Erickson algorithmic design mapping
