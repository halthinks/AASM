# AASM Roadmap

AASM is currently **v0.1.0 / early-stage**. This roadmap describes direction, not guaranteed delivery dates.

## Near term

- durable machine-state persistence
- persistent checkpoint and DP-memory backends
- richer event/evidence contracts
- improved schema validation
- async execution primitives
- configurable retry and recovery policies
- plugin/provider interfaces
- stronger CLI inspection and replay tools
- more worked examples
- integration adapters for popular agent runtimes
- versioned release packaging

## Next architecture layer

- distributed workers and leases
- crash-safe orchestration
- resumable long-running runs
- resource quotas and budget accounting
- graph visualization and execution tracing
- deterministic replay where external side effects permit it
- human approval surfaces
- policy-as-data for authority rules
- pluggable adversarial/verifier agents
- benchmark suite for orchestration behavior

## Longer-term possibilities

- persistent state stores (SQLite/Postgres/Redis adapters)
- remote execution protocol
- multi-runtime SDKs
- web control/inspection UI
- formal transition/model checking
- evidence lineage graphs
- sandbox integrations
- simulation-driven plan validation
- capability marketplaces / registries
- standardized interoperability contracts for agent runtimes

## Non-goals for the core

The project should avoid becoming a bundled LLM provider, a domain-specific application, or a monolithic framework that forces every user into one agent topology.
