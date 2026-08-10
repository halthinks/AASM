# AASM v0.23.0 — Decision Backend Ecosystem

v0.23 makes candidate decision generation replaceable while retaining deterministic AASM authority.

## Delivered

- durable candidate lifecycle state;
- solver-neutral backend capability, budget, usage, diagnostic, batch, and lifecycle contracts;
- deterministic finite-domain reference backend with continuation tokens;
- human proposal backend;
- provider-neutral callback backend for heuristic/model integrations;
- portfolio backend with deduplication and source provenance;
- backend registry and capability routing;
- runtime candidate generation, validation, selection, and activation;
- candidate state schema and batch schema;
- CLI surfaces and conformance tests.

Backends propose. AASM independently validates and authorizes activation.
