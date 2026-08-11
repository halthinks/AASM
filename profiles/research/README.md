# AASM Research Synthesis Profile

`aasm.research-synthesis@1.0.0` is the first finished AASM hero profile. It uses the existing AASM event/reducer runtime, calculus, assurance boundary, stores, replay, observability, CLI, HTTP server, and Control Center.

It does not introduce a separate research workflow engine.

## What it demonstrates

The bundled offline reference run starts from a plausible but overbroad causal model, records a matched-exposure contradiction, learns a certified no-good, backjumps to the causal decision, preserves unrelated report work, accepts a mid-run requirement, unlocks the newly relevant subgroup obligation, and produces a provenance-bearing synthesis.

```text
fixed question
→ fixed synthetic corpus
→ initial causal model
→ evidence extraction
→ contradiction
→ explanation
→ certified learned no-good
→ causal backjump
→ selective steering
→ corrected model
→ final artifact
→ exact replay verification
```

## Run it

```bash
# Create and complete a fresh reference run in SQLite.
aasm demo \
  --scenario research-synthesis \
  --mode complete \
  --db research-demo.db \
  --output-dir research-output
```

The command prints the machine ID and writes:

- `final_synthesis.json`
- `run_summary.json`
- `history_check.json`
- `machine_export.json`
- `machine_id.txt`
- `replay_commands.txt`

To inspect the machine:

```bash
aasm inspect MACHINE_ID --db research-demo.db --surface summary
aasm inspect MACHINE_ID --db research-demo.db --surface causal
aasm history-check MACHINE_ID --db research-demo.db --no-persist
aasm replay MACHINE_ID --db research-demo.db
```

Use `--mode setup` to stop before the known contradiction so the initial decisions, obligations, evidence, and conditional lock can be inspected.

## Corpus boundary

The packaged corpus is synthetic and released under CC0-1.0. It is intentionally small, deterministic, offline, and hash-verified. It is designed to demonstrate AASM mechanics, not to make a real scientific claim about retrieval practice.

The corpus lives in `src/aasm/reference_data/research/` and is verified against `manifest.json` before a run begins.

## Profile defaults

The profile includes:

- research, synthesis, and report decision namespaces;
- persistent source-review, contradiction-resolution, provenance, steering, and artifact obligations;
- explicit evidence contracts;
- bounded fairness defaults;
- governance-budget defaults;
- model-routing defaults;
- controlled profile evolution requiring explicit activation by `research-owner`.

See [`docs/RESEARCH_SYNTHESIS_DEMO.md`](../../docs/RESEARCH_SYNTHESIS_DEMO.md) and [`WHY_AASM.md`](../../WHY_AASM.md).
