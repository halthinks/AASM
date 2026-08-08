# AASM Roadmap

AASM is currently **v0.9.0 / early-stage**. This roadmap describes direction, not guaranteed delivery dates.

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
- ✅ cache-adjusted model economics and governance-overhead accounting
- ✅ deterministic review gating / Codex policy generation
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

- streamed worker logs and artifacts in the Control Center
- create/pause/resume/approve/fork controls with authority-policy enforcement
- richer executor adapters and provider-neutral structured result contract
- empirical model-strength calibration from tests, repair rate, latency, and accepted evidence
- run- and project-level token/cost budgets with hard/soft thresholds
- graph visualization and execution tracing
- ✅ deterministic state replay at explicit event boundaries
- richer human approval surfaces
- policy-as-data for authority rules
- pluggable adversarial/verifier agents
- benchmark suite for orchestration behavior and governance efficiency

## Longer-term possibilities

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
