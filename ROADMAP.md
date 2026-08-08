# AASM Roadmap

AASM is currently **v0.16.0 / early-stage**. This roadmap describes direction, not guaranteed delivery dates.

## Near term

- ✅ durable machine-state persistence (event stream + SQLite)
- ✅ persistent checkpoint backend (SQLite)
- ✅ persistent DP-memory backend
- ✅ durable plan graph + evidence lineage
- ✅ durable effect lifecycle + idempotency boundary
- ✅ durable capability registry + resource scheduler
- ✅ distributed worker registry + leases
- ✅ crash-safe task claiming + lease expiry/reclaim
- ✅ worker/resource quota enforcement
- ✅ remote worker transport/protocol
- ✅ PostgreSQL-backed coordination and advisory-lock sequencing
- ✅ model strength/cost/context/latency routing
- ✅ browser Control Center and provenance-preserving steering
- ✅ OpenAI Responses and Codex CLI executor adapters
- ✅ scheduled task → model route → executor → usage/evidence → durable completion orchestration
- ✅ worker-local executor registry and `aasm worker` launch surface
- ✅ durable worker reconnect after process restart
- ✅ empirical model outcome ledger by task class
- ✅ adaptive model routing with static hard gates, Wilson-bound evidence, repair/cost/latency metrics, and deterministic calibration
- ✅ remote/CLI model outcome feedback and model-performance inspection
- ✅ cache-adjusted model economics and governance-overhead accounting
- ✅ deterministic review gating / Codex policy generation
- ✅ durable governance budgets with soft/hard token/cost/call thresholds
- ✅ semantic-review fingerprints and completed-review reuse for unchanged low-risk decisions
- ✅ hard-budget `BUDGET_PAUSE` semantics that never waive required review
- ✅ observed-baseline avoided-review token/cost estimates
- ✅ remote/CLI governance decision, budget, review-completion, and reporting surfaces
- ✅ executable Planner/Builder/Verifier protocol with `CONTINUE | REPAIR | INVESTIGATE | PAUSE | PLAN_INTERRUPT`
- ✅ Planner-only authoritative plan mutation and durable plan revisions
- ✅ automatic Builder → Verifier → Planner handoff coordinator
- ✅ atomic validated `PLAN_INTERRUPT` graph patches and Planner override provenance
- ✅ remote/CLI PBV surfaces and live Control Center team state
- ✅ massive-collaboration analysis using dependency critical path and topological parallel width
- ✅ useful worker ceilings from physical capacity plus capability-eligible max-flow capacity
- ✅ coordination-overhead and marginal-improvement worker-count optimization
- ✅ min-cut/capability bottleneck evidence and durable collaboration history
- ✅ remote/CLI collaboration analysis and live Control Center fan-out status
- ✅ information-change signals and downstream selective impact closure
- ✅ selective affected-task pause with unaffected active leases preserved
- ✅ canonical pre/post claim checks so stale workers cannot successfully acquire newly paused work
- ✅ incremental Planner-only impact resolution with partial resume and durable remaining-node provenance
- ✅ remote/CLI change-control surfaces and live Control Center checkpoint state
- ✅ automatic Verifier checkpoint triggers for failed tests, changed assumptions, unexpected output, and blocking findings
- ✅ PBV Planner payloads carrying automatic trigger, impacted region, and fleet state
- ✅ opt-in fleet admission control derived from collaboration analysis
- ✅ durable machine-quota enforcement of fleet admission across SQLite/PostgreSQL claims
- ✅ automatic fleet refresh after triggered checkpoints, `PLAN_INTERRUPT`, and change resolution
- ✅ remote/CLI checkpoint-trigger and fleet-control configuration plus live Control Center state
- richer event/evidence contracts
- ✅ declarative machine definitions + initial static model checking
- improved schema validation
- configurable retry and recovery policies
- plugin/provider interfaces
- ✅ historical CLI replay + durable run forking
- more worked examples
- integration adapters for popular agent runtimes
- versioned release packaging

## Next architecture layer

- executor-fleet provisioning adapters that consume admission recommendations without bypassing deployment authority
- streamed worker logs and artifacts in the Control Center
- create/pause/resume/approve/fork controls with authority-policy enforcement
- richer executor adapters and provider-neutral structured result contract
- run- and project-level productive-work budgets in addition to governance budgets
- graph visualization and execution tracing
- automatic evidence/assumption → plan-node impact mappings with explicit provenance rather than inferred hidden dependencies
- ✅ deterministic state replay at explicit event boundaries
- richer human approval surfaces
- policy-as-data for authority rules
- pluggable adversarial/verifier agents
- benchmark suite for orchestration behavior and governance efficiency

## Longer-term possibilities

- cross-project model-performance priors with project/task-class isolation and explicit provenance
- Redis/cache adapters around PostgreSQL coordination
- multi-runtime SDKs
- deeper formal verification / temporal-property checking
- evidence lineage graphs
- sandbox integrations
- simulation-driven plan validation
- capability marketplaces / registries
- standardized interoperability contracts for agent runtimes

## Non-goals for the core

The project should avoid becoming a bundled LLM provider, a domain-specific application, or a monolithic framework that forces every user into one agent topology.
