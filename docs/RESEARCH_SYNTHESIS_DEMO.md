# Research Synthesis Hero Stack

AASM v0.26.0 ships one complete, deterministic reference application built on the ordinary AASM runtime.

It is designed to answer the adoption question:

> What does AASM preserve and make inspectable when a plausible long-running plan is contradicted after work has already been completed?

## Architectural rule

The hero stack does not own state directly. It calls the supported AASM API and therefore receives the same durability, legality, assurance, replay, and observability behavior as any other application.

```text
research demo
    ↓
AASMEngine public operations
    ↓
existing event/reducer runtime
    ↓
Memory / SQLite / PostgreSQL store
    ↓
calculus + assurance + observability
    ↓
existing CLI / HTTP / Control Center
```

There is no research-only reducer, event type system, database mutation path, scheduler, or recovery mechanism.

## Two modes

### Setup mode

```bash
aasm demo \
  --scenario research-synthesis \
  --mode setup \
  --db research-demo.db \
  --output-dir research-setup
```

Setup mode creates:

- the fixed question and verified corpus;
- the bound `aasm.research-synthesis@1.0.0` profile;
- the plan graph;
- the initial `retrieval_only` causal decision;
- source-review and synthesis obligations;
- evidence records;
- a conditional lock hiding subgroup work under the initial model.

It stops before the known contradiction.

### Complete mode

```bash
aasm demo \
  --scenario research-synthesis \
  --mode complete \
  --db research-demo.db \
  --output-dir research-output
```

Complete mode continues through:

```text
Gamma contradiction
→ validated explanation
→ soft learned constraint
→ certificate registration
→ independent verification
→ hard promotion
→ causal backjump
→ failed-model blocking
→ mid-run requirement injection
→ subgroup lock break
→ Delta resolution
→ corrected causal model
→ final artifact
→ durable-history replay verification
```

## Expected output

The command prints structured JSON containing the machine ID, final artifact, run summary, and output paths.

The output directory contains:

| File | Purpose |
|---|---|
| `final_synthesis.json` | Known-good structured synthesis with claim-level provenance |
| `run_summary.json` | Machine-readable demonstration measurements |
| `history_check.json` | Durable-history verification result or assurance state |
| `machine_export.json` | Complete exported machine and event history |
| `machine_id.txt` | Machine identity for later commands |
| `replay_commands.txt` | Ready-to-adapt inspection and replay commands |

## Required final properties

The v0.26 release test requires:

- final machine state `COMPLETE`;
- profile `aasm.research-synthesis@1.0.0` bound by fingerprint;
- corpus manifest valid;
- conflict `C-retrieval-only` resolved;
- learned constraint `LC-retrieval-only` active and hard;
- certificate `CERT-retrieval-only` independently verified;
- failed `retrieval_only` model blocked from reactivation;
- unrelated `report.format = structured_json` decision preserved;
- mid-run steering impact recorded;
- conditional subgroup lock broken;
- corrected model `effect_modified_by_prior_knowledge` active;
- every mandatory obligation committed or explicitly dispositioned;
- final semantic result classified `PASS`;
- exact replay reconstructing the final snapshot;
- durable-history verifier returning `PASS`.

## Inspecting the run

```bash
aasm inspect MACHINE_ID --db research-demo.db --surface summary
aasm inspect MACHINE_ID --db research-demo.db --surface decisions
aasm inspect MACHINE_ID --db research-demo.db --surface obligations
aasm inspect MACHINE_ID --db research-demo.db --surface evidence
aasm inspect MACHINE_ID --db research-demo.db --surface conflicts
aasm inspect MACHINE_ID --db research-demo.db --surface causal
aasm inspect MACHINE_ID --db research-demo.db --surface fairness
aasm inspect MACHINE_ID --db research-demo.db --surface packages
```

The authenticated HTTP equivalents remain:

```text
GET /v1/machines/{machine_id}/inspect/summary
GET /v1/machines/{machine_id}/inspect/decisions
GET /v1/machines/{machine_id}/inspect/obligations
GET /v1/machines/{machine_id}/inspect/evidence
GET /v1/machines/{machine_id}/inspect/conflicts
GET /v1/machines/{machine_id}/inspect/causal
```

The existing Control Center now loads these surfaces into human-readable panels.

## Corpus and truth boundary

The corpus is synthetic, not a literature review. Its conclusion is a deterministic expected result for a controlled orchestration scenario.

This separation is intentional:

- the corpus proves that the demo is reproducible;
- AASM proves that the run followed its declared machine rules;
- neither proves a real scientific theory.

The synthetic documents live under `src/aasm/reference_data/research/` and are distributed with the Python package.

## Programmatic use

```python
from aasm import SQLiteStore, run_research_synthesis_demo

store = SQLiteStore("research-demo.db")
try:
    result = run_research_synthesis_demo(
        store=store,
        mode="complete",
        output_dir="research-output",
    )
    print(result.summary)
finally:
    store.close()
```

The returned `ResearchDemoResult` contains the live engine, summary, artifact, and generated-file paths so tests and integrations can inspect the same canonical machine.
