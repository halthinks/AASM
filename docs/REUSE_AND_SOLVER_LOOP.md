# Deterministic Reuse and the V0.41 Solver Loop

V0.41 validates prior work before expensive execution. Reuse is not a second truth system: candidates reference canonical AASM Evidence, Reasoning Artifacts, or Hierarchical Memory.

A reusable candidate must satisfy canonical source identity, durable policy/controller admission, hierarchical scope visibility, principal privacy, environment compatibility, dependency validity, freshness when required, and effect safety. Similarity may discover candidates but cannot certify reuse.

Supported relations are `EXACT`, `IDEMPOTENT`, `SUBSUMES`, and `CERTIFIED_EQUIVALENT`. `SUBSUMES` requires an explicit semantic validator. `NON_IDEMPOTENT_EFFECT` is never discharged by reuse.

A validated hit produces a provenance-bearing `ReuseCertificate`. The certificate records the request, canonical source, candidate fingerprint, equivalence mode, scope/principal boundary, validation identity, and supporting Evidence. The certificate is committed through the ordinary AASM Evidence path.

The process-local `HotReuseIndex` is disposable. Clearing all reuse indexes can reduce performance but cannot change machine truth or legal work outcomes.

The solver-loop ordering is:

```text
reasoning frontier
→ open obligation
→ reuse validation
→ capability routing on miss
→ worker/model/tool/solver execution
→ Evidence
→ verification / epistemic admission
→ truth maintenance
→ memory / learning
→ deterministic completion or continued work
```

V41 coordinates existing V36 compiler caching, V37 reasoning, V38 dependency invalidation, V39 capability/formal verification, V40 memory/context, and learned no-goods. It introduces no second scheduler, event log, reducer, or authoritative cache.
