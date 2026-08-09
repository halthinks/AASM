# AASM Evolve Profile

`aasm.evolve` is the canonical domain-neutral profile. It assumes only that a goal can be formalized, decisions may activate different obligations, execution produces evidence, and contradictions may require repair, investigation, backjumping, or search restart.

It does **not** require software repositories, Planner/Builder/Verifier, SAT/SMT, a particular model provider, or a particular artifact type.

The profile can be copied into a separate package and specialized by adding a vocabulary, adapters, evidence policies, examples, and migrations. A specialization becomes a new profile ID and version; it does not silently mutate the built-in profile.
