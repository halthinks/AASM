# AASM Roadmap

AASM is currently **v0.7.0 / early-stage**. This roadmap describes direction, not guaranteed delivery dates.

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
- richer event/evidence contracts
- ✅ declarative machine definitions + initial static model checking
- improved schema validation
- async execution primitives
- configurable retry and recovery policies
- plugin/provider interfaces
- ✅ historical CLI replay + durable run forking
- more worked examples
- integration adapters for popular agent runtimes
- versioned release packaging

## Next architecture layer

- remote worker transport/protocol
- Postgres-backed coordination and advisory-lock claims
- resumable long-running worker sessions
- budget accounting beyond active capacity quotas
- graph visualization and execution tracing
- ✅ deterministic state replay at explicit event boundaries
- human approval surfaces
- policy-as-data for authority rules
- pluggable adversarial/verifier agents
- benchmark suite for orchestration behavior

## Longer-term possibilities

- persistent state stores (SQLite/Postgres/Redis adapters)
- remote execution protocol
- multi-runtime SDKs
- web control/inspection UI
- deeper formal verification / temporal-property checking
- evidence lineage graphs
- sandbox integrations
- simulation-driven plan validation
- capability marketplaces / registries
- standardized interoperability contracts for agent runtimes

## Non-goals for the core

The project should avoid becoming a bundled LLM provider, a domain-specific application, or a monolithic framework that forces every user into one agent topology.
