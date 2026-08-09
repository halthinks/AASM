# AASM Roadmap

AASM is currently **v0.19.0 / experimental**. This roadmap describes direction, not guaranteed delivery dates.

## Delivered foundation

- ✅ explicit algorithmic state machine and legal transitions
- ✅ graph planning, shortest paths, backtracking, and DP memory
- ✅ evidence, assumptions, observations, contradictions, and lineage
- ✅ event-sourced durability, checkpoints, SQLite, replay, and forks
- ✅ external-effect proposal, authorization, idempotency, attempt ownership, UNKNOWN outcomes, and reconciliation
- ✅ declarative machine definitions and static model checking
- ✅ capability resources, max-flow/min-cut scheduling, priorities, and quotas
- ✅ distributed worker registry, heartbeats, leases, expiry, reclaim, and stale-worker handling
- ✅ PostgreSQL multi-host coordination and canonical task claims
- ✅ model capability/strength/context/cost/latency routing
- ✅ OpenAI Responses and Codex CLI executor adapters
- ✅ end-to-end task → model → executor → usage/evidence → completion orchestration
- ✅ evaluated-outcome adaptive model routing by task class
- ✅ cache-aware model economics and governance-overhead accounting
- ✅ deterministic review gating, governance budgets, and safe review reuse
- ✅ executable Planner / Builder / Verifier protocol with Planner-only plan authority
- ✅ automatic Builder → Verifier → Planner handoff
- ✅ critical-path, DAG-width, coordination-overhead, and useful-worker analysis
- ✅ selective information-change checkpoints and additive steering
- ✅ automatic Verifier checkpoint triggers and fleet-admission recalculation
- ✅ authority-gated provider-neutral physical provisioning
- ✅ live execution telemetry and observed-duration feedback
- ✅ Kubernetes, local-process, and Docker Compose provisioning adapters
- ✅ external artifact references and bounded previews
- ✅ worker drain/resume/offline controls
- ✅ durable mission `QUIESCE`, `SUSPEND`, and `RESUME`
- ✅ status-separated effect queue and explicit effect approval
- ✅ controlled authority-gated fork creation
- ✅ opaque cursor paging for telemetry and artifact references
- ✅ `LEASE_LOST` semantics for results produced after ownership revocation
- ✅ browser Control Center, CLI, and remote-client operator surfaces

## Next architecture layer

- run- and project-level productive-work budgets in addition to governance budgets
- richer human approval queues with policy-as-data and delegation scopes
- provider-neutral structured executor results and streamed tool events
- external log-store backends with retention, search, and signed references
- deeper graph visualization, critical-path tracing, and event-timeline inspection
- automatic evidence/assumption → plan-node impact mappings with explicit provenance
- reconciliation assistants for UNKNOWN external effects that never guess external state
- rolling worker-fleet health, startup timeout, and provider/AASM identity reconciliation
- pluggable adversarial/verifier agents and benchmark suites
- formal temporal-property checking over machine and effect histories
- release packaging, signed artifacts, and package-registry publication

## Longer-term possibilities

- cross-project model-performance priors with strict project/task-class isolation
- Redis/cache acceleration around PostgreSQL coordination
- multi-runtime SDKs and standardized agent-runtime interoperability contracts
- simulation-driven plan validation and counterfactual forks
- capability registries/marketplaces with explicit trust and cost evidence
- domain adapters for CAD, robotics, research, deployment, and scientific simulation

## Non-goals for the core

AASM should not become a bundled LLM provider, a domain-specific application, or a monolithic framework that forces every user into one agent topology. The core should remain a role-agnostic control plane with explicit extension points.
