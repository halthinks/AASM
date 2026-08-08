# Governance economics

AASM v0.12 separates **semantic model review** from **technical authority**.

A governance decision answers one question: *does this action need another intelligent review right now?* It does **not** grant permission to execute the action. Sandbox policy, authority policy, effect authorization, credentials, network policy, and destructive-operation guards remain independent boundaries.

## Why

Repeated reviewer-model calls can consume a large fraction of an agent workload even when the underlying permission decision is deterministic and unchanged. AASM therefore treats governance calls as measurable resource consumption rather than free supervision.

The goal is not to remove review. It is to spend model reasoning when information or risk changes.

## Decision actions

- `REVIEW_NOT_REQUIRED` — deterministic policy says semantic model review is unnecessary. This is not execution authorization.
- `MODEL_REVIEW_REQUIRED` — a semantic review must occur.
- `REVIEW_REUSED` — the same low-risk governance fingerprint was previously reviewed and completed, with no relevant policy/assumption/evidence change.
- `BUDGET_PAUSE` — review is still required, but a hard governance budget is exhausted. AASM pauses/escalates instead of waiving review.

High-risk classes such as destructive, credential, security-sensitive, external-write, unknown-network, irreversible, and unknown actions are never automatically reused.

## Fingerprints

`GovernanceContext` fingerprints:

- action class
- scope
- action signature
- policy revision
- assumption revision
- evidence revision

A changed fingerprint requires a new semantic decision. `assumption_changed` and `tests_failed` force fresh review independently.

Callers should make `action_signature` describe the material operation rather than a generic command class. For code work, a stable diff/artifact/action digest is preferable to a human-readable label.

## Budgets

`GovernanceBudgetPolicy` supports soft and hard token/cost ratios plus absolute governance-token, governance-cost, and permission-review-call ceilings.

Ratio enforcement has a minimum observed-token floor. This prevents the first governance call from being treated as a meaningful 100% overhead regime.

A soft budget does not suppress review. It can hint that a lower-cost eligible reviewer should be preferred.

A hard budget never converts required review into approval. Required review returns `BUDGET_PAUSE` until authority changes the budget/review strategy or stops the run.

## Avoided-overhead accounting

When AASM reuses a completed review, `governance_report()` estimates avoided tokens/cost using the workload's **observed average permission-review call**, when one exists. This is a counterfactual estimate, not a billing claim.

The report also distinguishes deterministic bypasses from genuinely reused semantic reviews.

## Python

```python
from aasm import GovernanceBudgetPolicy, GovernanceContext

engine.configure_governance_budget(GovernanceBudgetPolicy(
    soft_governance_token_ratio=0.35,
    hard_governance_token_ratio=0.75,
    min_total_tokens_for_ratio_enforcement=50_000,
))

decision = engine.governance_decide(GovernanceContext(
    action_class="architecture_choice",
    scope="backend",
    action_signature="sha256:...",
    assumption_revision="A17",
    evidence_revision="E42",
))

if decision["action"] == "MODEL_REVIEW_REQUIRED":
    # Run the selected reviewer, record its ModelUsageRecord as permission_review,
    # then persist its evidence.
    engine.complete_governance_review(decision["decision_id"], evidence=["review:accepted"])
```

## CLI

```bash
aasm governance MACHINE_ID --store runs.db

aasm governance-budget MACHINE_ID \
  --store runs.db \
  --policy governance-budget.json

aasm governance-decide MACHINE_ID \
  --store runs.db \
  --context governance-context.json

aasm governance-complete MACHINE_ID \
  --store runs.db \
  --decision-id GOV_DECISION_ID \
  --evidence review-evidence.json
```

## Remote control plane

The same workflow is available over `aasm.remote.v1` through `AASMRemoteClient.configure_governance_budget()`, `governance_decide()`, and `complete_governance_review()`.

## Relationship to Codex Auto-review

AASM does not disable Codex sandboxing. The intended architecture is:

```text
routine deterministic boundary -> static policy -> no semantic reviewer call
materially changed / risky action -> semantic reviewer -> evidence
hard governance budget + required review -> PAUSE, never silent approval
```

Codex/OpenTelemetry usage can still be imported into AASM so permission-review overhead and cache-adjusted model economics are visible in the same durable run.
