# Changelog

All notable user-visible changes to AASM will be documented here.

The project uses semantic-versioning intent while the public API remains experimental before 1.0.

## [0.12.0] - 2026-08-08

### Added

- durable `GovernanceBudgetPolicy`, `GovernanceContext`, `GovernanceDecision`, and `GovernanceEconomicsController`
- deterministic semantic-review fingerprints over action, scope, policy, assumption, and evidence revisions
- explicit `REVIEW_NOT_REQUIRED`, `MODEL_REVIEW_REQUIRED`, `REVIEW_REUSED`, and `BUDGET_PAUSE` outcomes
- sample-aware soft/hard governance token and cost ratios plus absolute governance token/cost/permission-review-call ceilings
- durable governance decision history, completed-review evidence, and low-risk review reuse
- governance overhead report with deterministic bypass counts, reused-review counts, and observed-baseline avoided-token/cost estimates
- remote governance budget/decision/review-completion endpoints and `AASMRemoteClient` methods
- `aasm governance`, `governance-budget`, `governance-decide`, and `governance-complete` CLI commands
- governance budget/context/decision JSON schemas, documentation, example, and acceptance tests

### Safety semantics

- governance optimization controls only whether another semantic model review is needed; it does not authorize execution
- sandbox policy, authority policy, credentials, network rules, effect authorization/idempotency, and destructive-operation guards remain independent boundaries
- destructive, credential, security-sensitive, external-write, unknown-network, irreversible, and unknown actions never reuse prior semantic review automatically
- hard governance budget exhaustion returns `BUDGET_PAUSE`; required review is never silently waived
- ratio budgets wait for a minimum observed-token floor to avoid cutting work short because the first governance call temporarily represents 100% of usage
- soft budget pressure suggests a lower-cost eligible reviewer rather than less review

### Auto-review economics

- repeated low-risk semantic reviews can be reused only when their governance fingerprint is unchanged and the prior review was explicitly completed
- changed assumptions, failed tests, changed policy/evidence revisions, or changed action signatures force a fresh review
- avoided-overhead estimates use the run's observed average permission-review call when available rather than assuming a fixed reviewer cost
- Codex telemetry and model usage remain separable into productive, verification, governance, and permission-review purposes for cache-adjusted accounting

## [0.11.0] - 2026-08-08

### Added

- durable `ModelOutcomeRecord` feedback for explicitly evaluated model results by task class
- `ModelOutcomeLedger` aggregation of acceptance, repair, verification, latency, cost, and sample evidence
- Wilson lower/upper acceptance bounds and an auditable interval-concentration confidence metric
- `AdaptiveModelRouter` that re-ranks only models already eligible under the static capability/strength/context/cost contract
- adaptive objectives for conservative quality, latency, and cost-per-quality
- deterministic calibration of eligible under-sampled model classes when explicitly enabled
- durable `record_model_outcome()` and `model_performance()` engine APIs
- remote `/model-outcome` feedback plus `AASMRemoteClient.model_outcome()`
- `aasm model-outcome` and `aasm model-performance` CLI commands
- model-performance state in the Control Center/dashboard payload
- adaptive-routing schema extensions, outcome schema, documentation, example, and tests

### Routing semantics

- a successful API/executor call is not automatically treated as a successful model outcome; adaptive evidence must come from an explicit evaluator/verifier result
- static minimum strength, capability, context, enabled-state, candidate-set, and cost-ceiling constraints remain hard gates and cannot be weakened by empirical history
- empirical acceptance floors use the Wilson lower bound rather than raw observed acceptance
- when evidence is insufficient, routing falls back to the deterministic static router unless calibration is explicitly requested
- task-class-specific history prevents a globally cheap model from being treated as sufficient for every kind of work

### Architectural significance

- Luna/Terra/Sol-style routing can now evolve from configured priors into measured task-class behavior while retaining deterministic safety/quality floors
- v0.11 provides the evaluated outcome signal needed to optimize governance-model spend in the next milestone without confusing execution success with engineering acceptance

## [0.10.0] - 2026-08-08

### Added

- `ExecutionContract` for carrying prompt, purpose, model-routing constraints, executor-routing constraints, and fixed-model/executor overrides inside task metadata
- worker-local `ExecutorRegistry` and `ExecutorBinding` capability/provider matching
- `ExecutionOrchestrator` that turns a claimed task lease into a model route, physical executor invocation, model-usage record, provider evidence, and normalized durable completion result
- `OrchestratedRemoteWorker`, composing the existing durable worker loop with real executor orchestration
- `aasm worker` CLI for launching Codex CLI or OpenAI Responses workers on separate machines
- execution-contract JSON schema, worked example, and executor-orchestration documentation
- HTTP client model-usage reporting so remote workers feed the durable economics ledger automatically

### Reliability

- remote worker processes can reconnect using the same durable worker ID after restart when the resource binding matches
- changed worker/resource identity is rejected instead of silently moving durable ownership
- orchestration results preserve selected model, provider, executor, route, output, usage, evidence IDs, and the execution contract that caused the call
- routed execution retains the lease/effect boundary: claiming work does not bypass external-effect authorization/idempotency semantics

### Architectural significance

- scheduled work no longer stops at an abstract assignment: AASM now has an end-to-end path from task scheduling through model and executor routing to physical execution and durable completion
- v0.10 captures the task/model/executor/outcome data required for the next milestone: empirical model-strength calibration and adaptive Luna/Terra/Sol-style routing

## [0.9.0] - 2026-08-08

### Added

- browser Control Center with live run, worker, lease, plan, model, evidence, and economics inspection
- OpenAI Responses API executor adapter with cache-aware token usage capture
- headless Codex CLI executor adapter using `codex exec --json` without changing Codex sandbox posture
- durable model-call economics ledger separating productive, verification, governance, permission-review, synthesis, and retry usage
- deterministic `ReviewGatePolicy` for routine benign actions with escalation on risk, changed assumptions, failed tests, or material diffs
- conservative Codex rules/requirements generator through `CodexGovernancePolicy`
- provenance-preserving user steering/interrupt API and Control Center action
- dashboard, model-usage, review-gate, interrupt, and Codex telemetry inspection/import surfaces

### Audit hardening

- SQLite and PostgreSQL hot-path event append now reduce one event against the locked canonical materialized snapshot instead of replaying the full event history on every heartbeat/write
- stateless HTTP handlers use lazy resume (`load_history=False`) and synchronize only events committed since the last known sequence; full replay/export remains available on demand
- stale hosts cannot overwrite materialized state committed by another host
- PostgreSQL task claims enforce current worker/resource/quota policy from the canonical database snapshot, including stale-host capacity and quota changes
- SQLite mirrors canonical capacity/quota enforcement under `BEGIN IMMEDIATE` for local multi-process coordination
- external effect attempts are atomically claimed before execution in SQLite and PostgreSQL, preventing two workers from executing one authorized effect concurrently
- effect attempts carry an `execution_id`; success/failure finalization is compare-and-set against that execution owner so stale recovery/finalization cannot overwrite the active attempt
- passive `resume()` and `recover_unfinished()` no longer reclassify healthy remote `RUNNING` effects; crash reconciliation requires explicit `recover_effects=True`
- failed durable appends no longer leave uncommitted ghost state in the live runtime
- CLI storage arguments support PostgreSQL across inspection/coordination commands while retaining `--db` as a SQLite compatibility alias
- cache-write tokens, long-context pricing multipliers, unpriced internal models, and governance-token/cost completeness are represented explicitly in economics accounting
- Control Center durable labels are escaped before HTML rendering; the server adds no-store/CSP/no-sniff/no-referrer/frame-deny headers, request-size limits, constant-time bearer comparison, and refuses unauthenticated non-loopback binding
- tracked release inventory is CI-checked; SHA-256 manifests are generated from immutable checkouts/releases instead of maintained as stale moving-branch data

### Design principle

- preserve sandboxing and technical boundaries; express repeatable permission decisions as deterministic policy and spend model reasoning on substantive review or genuinely ambiguous/risky actions

## [0.8.0] - 2026-08-07

### Added

- optional PostgreSQL coordination store with advisory-lock event sequencing and atomic cross-host task claims
- dependency-free `aasm.remote.v1` JSON/HTTP worker protocol and `AASMRemoteClient`
- `aasm serve` control-plane server with bearer-token protection and a built-in `/ui` inspector
- real multi-host worker registration, heartbeat, lease claim/renew/complete/fail over the network
- durable model profiles with capability, strength, cost, latency, context, and concurrency metadata
- deterministic model routing with hard quality/cost/context filters and balanced/strength/cost/latency objectives
- PostgreSQL integration CI service and remote-protocol/model-routing tests

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
