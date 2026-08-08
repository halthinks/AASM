# AASM — Algorithmic Agent State Machine

AASM is a role-agnostic Python runtime for governing AI agents, tools, humans, and multi-agent teams with explicit state, legal transitions, graph planning, reversible search, memoized subproblems, capacity-aware allocation, adversarial verification, and append-only provenance.

**Core principle:** models propose; algorithms organize; policy authorizes; evidence validates; the state machine governs what can happen next.

## What is included

- Explicit hierarchical-ready machine states and transition guard table
- JSON Schemas for problems, snapshots, transition events, and agent messages
- Deterministic algorithm-selection router
- Dependency graph, topological ordering, Dijkstra shortest path, and edge relaxation
- Checkpoint/backtracking and branch pruning
- Dynamic-programming memory with canonical signatures and validity scopes
- Edmonds-Karp max-flow/min-cut resource allocator
- Rule-based adversarial verifier
- Generic agent interface and FunctionAgent adapter
- Single-controller, autonomous, quorum, and hierarchical authority policies
- Generic, Planner/Builder, swarm, and human/tool protocol adapters
- Six orchestration profiles
- Unit tests and multi-agent example
- Codex/agent-ready `SKILL.md`

## Install and test

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\\Scripts\\activate
pip install -e '.[dev]'
pytest -q
```

Run the minimal demonstration:

```bash
aasm demo
python examples/multi_agent_demo.py
```

## State lifecycle

`INGEST → FORMALIZE → CLASSIFY → DECOMPOSE/PLAN → SELECT → EXECUTE → OBSERVE → VERIFY`

Verification may lead to `COMMIT`, `REPAIR`, `BACKTRACK`, `INVESTIGATE`, `COMPLETE`, or `FAIL`. Illegal transitions raise an exception.

## Role agnosticism

There is no privileged Planner/Builder architecture in AASM. Agents register capabilities and operate through a generic proposal/authorization/result contract. Governance is selected independently through an authority policy. `PlannerBuilderAdapter` exists only for interoperability with systems that already use that pattern.

## Algorithmic lineage

The architectural mapping draws on standard algorithmic techniques presented in Jeff Erickson's open *Algorithms* materials: recursion/reduction, backtracking, dynamic programming, greedy methods, graph algorithms, shortest paths, max-flow/min-cut, adversary arguments, and automata. See `docs/ERICKSON_MAPPING.md` for source links and the design mapping.

AASM's source code and agent-runtime interpretation are original; the package does not copy Erickson's textbook text.

## License
MIT for AASM source. Erickson's materials remain under their own stated terms and are not bundled in this package.
