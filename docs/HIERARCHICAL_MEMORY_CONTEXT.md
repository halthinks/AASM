# Hierarchical Memory, Reasoning Frontier, and Context Projection

AASM v0.40 adds durable semantic memory without creating a second truth system.

## Contracts

`aasm.memory.hierarchical.v1`, `aasm.memory.index.v1`, `aasm.reasoning.frontier.v1`, and `aasm.context.projection.v1` are all version `0.1.0`.

## Authority

Every durable memory mutation follows **Decision → Obligation → Evidence**. Models/workers/users may propose. Policy or Controller authorizes. Commit writes only the exact authorized memory object.

## Embeddings are not memory

Embeddings, lexical indexes, graph indexes, tree indexes, and reranker outputs are derived `MemoryIndexEntry` records bound to the exact canonical memory fingerprint. Re-embedding does not rewrite historical memory identity.

## Semantic memory

Semantic memory must reference V37 `AUTHORIZED` reasoning artifacts. If V38 later marks those artifacts stale/refuted/rejected, the memory projection becomes stale and ordinary context excludes it by default.

## Privacy

`AGENT` and `USER` memory requires `metadata.privacy_principal_id`. A context request must present matching `metadata.principal_id`. Private memory is filtered before ranking. Scope visibility separately reuses AASM hierarchical Decision Scopes.

## Retention and forgetting

Retention is `permanent`, `forgettable`, or `ttl:<seconds>`. TTL uses explicit/durable time. Forgetting appends a `MemoryTombstone`; historical Evidence is preserved.

## Reasoning Frontier

The Reasoning Frontier is a deterministic bounded projection of nonterminal reasoning artifacts, active decisions, and open obligations relevant to a target scope/query.

## Context Projection

Context projection filters by truth/staleness, scope, privacy, kind, then ranks deterministically using query relevance plus V38 causal/objective relevance, verification strength, and admitted derived-index scores. Hard item and character budgets are enforced.

## Legacy cache

Existing `DPMemory`/`memo_*` behavior remains unchanged and separate from hierarchical semantic memory.
