# Changelog

All notable user-visible changes to AASM will be documented here.

The project uses semantic-versioning intent while the public API remains experimental before 1.0.

## [0.7.0] - 2026-08-07

### Added

- durable worker registry with heartbeat, draining/offline/stale states
- crash-safe task leases with claim, heartbeat, completion, failure, release, expiry, and reclaim lifecycle
- SQLite-backed atomic task-claim reservations to prevent duplicate multi-process claims
- machine, worker, and resource quotas for active leases and capacity units
- stale-worker reaping that expires abandoned leases
- restart/replay/fork preservation of worker, quota, and lease state
- worker/lease CLI inspection, JSON schemas, documentation, and example

## [0.6.0] - 2026-08-07

### Added

- durable resource/capability registry for agents, tools, humans, services, and constrained execution slots
- capability-aware max-flow scheduling with priorities, reliability/cost filters, durable assignments, utilization, and unmet demand
- min-cut bottleneck reporting and explicit missing-capability diagnostics
- automatic durable plan-node ownership updates when task IDs match plan nodes
- restart/replay/fork-safe resource and scheduling state
- `aasm resources` and `aasm schedule` CLI commands, schemas, documentation, and scheduler example

## [0.5.0] - 2026-08-07

### Added

- event-sourced durable planning graph nodes, edges, node updates, visited/frontier state, and branch pruning
- persistent DP memory with validity scopes, proof references, metadata, and durable invalidation
- evidence ledger for claims, observations, assumptions, and contradictions with derivation/support/contradiction links
- durable evidence invalidation that preserves provenance
- fork-aware planning, memory, and evidence state at historical event boundaries
- CLI inspection commands for plan, memory, evidence, and evidence lineage
- plan-node and evidence JSON schemas plus durable-cognition documentation

### Compatibility

- existing graph and DPMemory APIs remain available; engine-level durable wrappers add persistence without requiring custom stores

## [0.4.0] - 2026-08-07

### Added

- declarative `MachineDefinition` runtime with JSON/TOML loading and optional YAML loading
- static transition-graph model checker for undefined targets, unreachable states, dead ends, invalid terminal edges, and non-terminating reachable regions
- `aasm verify-machine` CLI command and versioned machine-definition JSON schema
- historical replay at an exact machine-local event sequence
- durable machine forking with new machine IDs and explicit source lineage
- `aasm fork` CLI command and fork demonstration
- custom terminal-state awareness in unfinished-run recovery

### Compatibility and safety

- the original AASM lifecycle is still the default machine definition, preserving existing call sites
- forks never copy or re-execute source-run external effects
- machine-definition identity and terminal-state semantics are persisted in the event stream

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
