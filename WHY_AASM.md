# Why AASM? A Reproducible Research-Synthesis Comparison

This document does not ask the reader to accept a marketing claim. It defines one fixed, synthetic, offline problem and shows what is preserved or lost under two explicit control policies.

The corpus is intentionally synthetic. The comparison is about orchestration behavior, not a scientific claim about retrieval practice.

## The fixed problem

Question:

> Does spaced retrieval improve delayed retention primarily through retrieval practice rather than additional exposure time?

The packaged corpus contains:

- Alpha: an exposure-matched novice study supporting a retrieval-practice effect;
- Beta: a positive study confounded by additional exposure time;
- Gamma: an exposure-matched experienced-learner replication contradicting a universal effect;
- Delta: a prespecified subgroup reanalysis resolving the contradiction through prior-knowledge effect modification.

Every source is synthetic, redistributable under CC0-1.0, and verified by SHA-256 before the AASM run starts.

## Baseline control policy

The baseline is a conventional stateless retry loop:

```text
make a plan
→ extract sources
→ draft a conclusion
→ contradiction arrives
→ regenerate the current plan and draft
```

For this comparison, the baseline has no durable decision graph, obligation graph, causal explanation, learned no-good, or replayable event history. When Gamma contradicts the initial `retrieval_only` interpretation, the baseline restarts the synthesis branch. It has no machine-enforced rule preventing the same interpretation from being selected again.

This baseline is deliberately narrow and transparent. It is not a claim that every other framework behaves identically.

## AASM control policy

The AASM run uses the ordinary supported path:

```text
AASMEngine
→ event/reducer runtime
→ profile binding
→ Decision / Obligation / Evidence calculus
→ strict certificate boundary
→ change-impact steering
→ replay and observability
```

The run:

1. activates the initial `retrieval_only` causal model;
2. records source and method evidence;
3. records Gamma as a validated contradiction;
4. creates an explanation tied to the causal-model decision;
5. learns `LC-retrieval-only` as a soft no-good;
6. independently verifies a projection certificate;
7. promotes the exact learned constraint to hard knowledge;
8. backjumps to the causal decision;
9. preserves the unrelated structured-report decision;
10. proves the failed model cannot be selected again;
11. injects a new requirement to report prior-knowledge limits;
12. unlocks and executes only the affected subgroup work;
13. commits a corrected provenance-bearing artifact;
14. reconstructs the final machine through full event replay.

## Run the comparison

```bash
python -m venv .venv
# Windows: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -e .

aasm demo \
  --scenario research-synthesis \
  --mode complete \
  --db research-demo.db \
  --output-dir research-output
```

Inspect the emitted `run_summary.json`. The release gate requires these observations:

| Measure | Stateless retry baseline | AASM reference run |
|---|---|---|
| Causal decision named | No | Yes |
| Contradiction linked to evidence | Informal | Durable conflict object |
| Failed interpretation blocked from recurring | No | Yes, certified hard no-good |
| Recovery target | Current/recent work | Causal decision |
| Unrelated report-format decision preserved | Not guaranteed | Yes |
| Mid-run requirement impact bounded | No explicit boundary | Yes, affected and preserved plan regions recorded |
| Hidden subgroup work restored after model change | Manual | Conditional lock breaks automatically |
| Mandatory obligations checked at completion | No machine gate | Zero unresolved mandatory obligations required |
| Claim-level provenance | Optional prose | Structured evidence IDs |
| Exact history replay | No | Yes |
| Reconstructed snapshot compared with persistence | No | Yes |

## What to inspect

```bash
aasm inspect MACHINE_ID --db research-demo.db --surface decisions
aasm inspect MACHINE_ID --db research-demo.db --surface obligations
aasm inspect MACHINE_ID --db research-demo.db --surface evidence
aasm inspect MACHINE_ID --db research-demo.db --surface conflicts
aasm inspect MACHINE_ID --db research-demo.db --surface causal
aasm history-check MACHINE_ID --db research-demo.db --no-persist
aasm replay MACHINE_ID --db research-demo.db
```

The important result is not that AASM generated different prose. The important result is that the runtime can answer:

- Which decision authorized the rejected interpretation?
- Which evidence contradicted it?
- Which explanation justified the learned no-good?
- Which certificate allowed that no-good to become hard?
- Where did recovery backjump?
- Which unrelated work survived?
- Which requirement was injected mid-run?
- Which obligations were restored and completed?
- Which evidence supports every final claim?
- Does the event history reconstruct the persisted final state exactly?

A transcript-only loop cannot answer all of those questions reliably after the fact. AASM stores them as machine state.
