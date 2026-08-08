# Changelog

All notable user-visible changes to AASM will be documented here.

The project uses semantic-versioning intent while the public API remains experimental before 1.0.

## [0.15.0] - 2026-08-08

### Added

- `ChangeKind`, `ChangeSignal`, `ImpactAnalysis`, and `ChangeImpactAnalyzer`
- downstream dependency-closure mapping from changed plan nodes to affected work
- durable change-control checkpoints with affected, unaffected, active-affected, preserved-active, and remaining-node provenance
- selective pause semantics that release only affected active leases while preserving unrelated work
- canonical pre/post claim checks so stale worker processes cannot successfully acquire work that another host just paused
- incremental Planner-only impact resolution with partial resume, retirement, remaining-node tracking, and resolution history
- additive `user_interrupt()` steering through optional `seed_nodes` without regenerating or discarding the whole plan
- remote change-control analysis/resolution endpoints and matching `AASMRemoteClient` methods
- `change-control`, `change-analyze`, and `change-resolve` CLI commands
- live information-change checkpoint status in the browser Control Center
- change-signal schema, documentation, worked example, and regression tests

### Selective checkpoint semantics

- an edge `A -> B` means B depends on A, so a change anchored at A affects A and its downstream descendants
- unanchored changes require Planner attention without falsely invalidating every plan node
- paused tasks cannot be claimed until explicitly resolved
- active affected leases are released; unaffected active leases remain valid
- a worker that finishes local computation after its lease was released cannot turn that released lease into a successful durable completion
- partial resolution does not re-pause nodes already resumed in an earlier Planner resolution
- when the executable PBV profile is configured, only the authoritative Planner may resolve an impact checkpoint

### Distributed correctness

- task claim checks read the canonical stored pause set before ownership is attempted and re-check after ownership is created
- the pause path scans the post-pause canonical lease state, closing the claim-before-pause and pause-before-claim interleavings without weakening existing task-claim/resource/quota boundaries

### Architectural significance

- user steering, changed assumptions/evidence, failed verification, contradictions, and risk escalation can now interrupt only the affected dependency region instead of restarting the entire run
- v0.15 closes the loop between durable plan provenance, PBV Planner authority, and long-running multi-worker execution

## [0.14.0] - 2026-08-08

### Added

- `CollaborationPolicy`, `CollaborationCandidate`, `CollaborationAnalysis`, and `CollaborationPlanner`
- critical-path and topological-wave analysis over the durable plan graph
- maximum useful parallel-width calculation instead of assuming every task can run concurrently
- capability-aware fan-out ceiling based on max-flow-deliverable resource capacity rather than raw fleet size
- candidate worker-count projections using total work, critical path, and configurable coordination overhead
- smallest-near-optimal worker-count selection plus minimum marginal-improvement gating
- min-cut bottleneck, unmet-capability, schedulable-fraction, enabled-capacity, eligible-capacity, and resource-cost evidence in each analysis
- durable collaboration-analysis history and Control Center visibility
- remote collaboration analysis endpoint/client and `aasm collaboration` CLI command
- collaboration policy schema, documentation, example, and regression tests

### Scheduling semantics

- worker count is bounded by configured maximum, runnable task count, DAG parallel width, physical enabled capacity, and capability-eligible max-flow capacity
- serial critical paths reject useless fan-out even when hundreds of workers are available
- workers that cannot satisfy task capabilities do not count as useful concurrency
- coordination overhead can make a smaller team faster than the maximum available team
- AASM recommends the smallest worker count inside the configured near-optimal makespan band rather than maximizing concurrency
- v0.14 recommends useful concurrency; it does not silently provision workers or infrastructure

### Architectural significance

- max-flow/min-cut, graph planning, worker capability, and cost accounting now directly govern whether adding more agents can improve wall-clock completion
- the Planner/Control Center can distinguish a worker shortage from a dependency critical path, capability cut, or coordination-overhead problem before spawning more agents

## [0.13.0] - 2026-08-08

### Added

- durable `TeamMember`, `BuilderOutput`, `VerifierReport`, and `PlannerDecision` records
- exact runtime directives: `CONTINUE | REPAIR | INVESTIGATE | PAUSE | PLAN_INTERRUPT`
- executable `PlannerBuilderVerifierPolicy` with one authoritative Planner, Builder execution role, and advisory Verifier role
- atomic `PLAN_INTERRUPT` graph patches with plan-revision provenance and cycle validation before commit
- durable team status, per-task directives, Builder-output history, Verifier-report history, and Planner-decision history
- `PBVCoordinator` automatic Builder → Verifier → Planner handoff wrapper
- remote PBV protocol endpoints and matching `AASMRemoteClient` helpers
- `team`, `team-init`, `builder-output`, `verifier-report`, and `planner-decision` CLI commands
- live Planner/Builder/Verifier status in the browser Control Center
- executable PBV documentation, schema, profile, worked example, and acceptance tests

### Authority semantics

- only the registered Planner can commit an authoritative control directive
- Builders can produce work and evidence but cannot mutate the plan
- Verifiers can inspect Builder output and recommend a directive but cannot authorize continuation or rewrite the plan
- `PLAN_INTERRUPT` is the only directive allowed to mutate the authoritative plan and must include an explicit `plan_patch`
- plan patches are applied to a copy of the current graph and validated before one durable commit; invalid or cyclic patches leave the current plan and revision unchanged
- Planner overrides of Verifier recommendations remain linked to the source Verifier report for provenance

### Executable handoff

- `PBVCoordinator` persists Builder output, passes it to a Verifier callable, persists the Verifier report, passes both to the Planner callable, validates Planner identity, and commits the Planner decision
- Planner and Verifier callables remain transport-neutral and can be backed by Codex, OpenAI Responses, another model provider, deterministic code, a remote service, or a human approval surface
- the PBV profile remains an AASM orchestration profile rather than becoming the role-agnostic core architecture

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
- capability-aware max-flow scheduling with priorities, reliability/cost filters, durable assignments, utilization, unmet demand
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
- `aasm verify-machine` command and versioned machine-definition JSON schema
- historical replay at an exact machine-local event sequence
- durable machine forking with new machine IDs and explicit source lineage
- `aasm fork` command and fork demonstration
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
