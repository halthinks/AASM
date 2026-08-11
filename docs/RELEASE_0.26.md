# AASM v0.26.0 — Research Synthesis Hero Stack

AASM v0.26.0 is the first adoption-focused release built after the v0.25.1 stabilization and v0.25.2 canonical adoption contract.

The release does not add another kernel architecture layer. It makes the existing architecture runnable and visible through one end-to-end application.

## Added

- built-in `aasm.research-synthesis@1.0.0` hero profile;
- matching package manifest, evidence contracts, fairness defaults, model-routing defaults, and governance defaults;
- fixed synthetic CC0 offline corpus with SHA-256 manifest verification;
- deterministic research-synthesis reference runner;
- setup and complete demonstration modes;
- validated contradiction, exact learned no-good, certificate verification, hard promotion, and causal backjump;
- proof that unrelated report work remains active after recovery;
- mid-run selective requirement injection through the existing change-impact pathway;
- conditional subgroup-lock restoration;
- known-good structured synthesis with claim-level evidence IDs;
- full event replay and replay-versus-persistence verification;
- `WHY_AASM.md` reproducible baseline comparison;
- research-specific panels added to the existing Control Center;
- Python, CLI, profile-registry, HTTP-inspection, and output-artifact integration;
- packaged reference data in the Python wheel.

## Run

```bash
aasm demo \
  --scenario research-synthesis \
  --mode complete \
  --db research-demo.db \
  --output-dir research-output
```

## Existing architecture reused

The reference application calls the same methods used by external adopters:

- `bind_profile()`;
- `register_decision()` and `activate_decision()`;
- `register_obligation()` and obligation lifecycle methods;
- `add_evidence()`;
- `raise_conflict()` and `register_explanation()`;
- `learn_constraint()`;
- certificate registration, verification, and hard promotion;
- `backjump_conflict()`;
- `user_interrupt()` and change-impact resolution;
- `record_semantic_result()`;
- `inspect_machine()`;
- `check_durable_history()`;
- `replay()`.

All state changes still pass through the ordinary event/reducer path and existing stores.

## Compatibility

- package/runtime version is `0.26.0`;
- remote protocol remains `aasm.remote.v1 / 0.19.0`;
- older snapshots continue to receive existing compatibility normalization;
- the research profile is additive;
- the original `aasm demo` remains available as `--scenario classic`;
- the new reference corpus is package data and requires no network access.

## Correctness boundary

The release proves the controlled reference trajectory and the declared AASM machine properties. The corpus is synthetic and the final conclusion is not offered as a real scientific finding.

See [`docs/RESEARCH_SYNTHESIS_DEMO.md`](RESEARCH_SYNTHESIS_DEMO.md), [`WHY_AASM.md`](../WHY_AASM.md), and [`profiles/research/`](../profiles/research/).
