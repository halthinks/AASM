# Durable planning, memory, and evidence

AASM v0.5 extends durability beyond machine state and external effects into the runtime's working cognition.

## Durable planning graph
Plan nodes and edges are committed as typed events and reduced into the machine snapshot. Node status, owner, cost, evidence references, frontier membership, visited nodes, and pruned branches survive restart and historical replay. A fork receives the exact planning graph that existed at the selected event boundary.

## Persistent DP memory
`memo_put()` commits a solved subproblem with its value, validity scope, proof references, and metadata. `memo_get()` respects the saved scope. `memo_invalidate()` durably marks an entry invalid when assumptions or context change.

## Evidence lineage
AASM records claims, observations, assumptions, and contradictions as stable evidence records. Records can reference earlier records through `derived_from`, `supports`, and `contradicts`. `evidence_lineage(id)` reconstructs ancestry. Invalidations preserve history and reason.

## Fork semantics
Historical forks copy only the planning, memory, and evidence state represented by the selected event boundary. They do not copy external effect records, and they evolve independently after the fork.

## CLI inspection
```bash
aasm plan MACHINE_ID --db runs.db
aasm memory MACHINE_ID --db runs.db
aasm evidence MACHINE_ID --db runs.db
aasm evidence MACHINE_ID --db runs.db --lineage EVIDENCE_ID
```
