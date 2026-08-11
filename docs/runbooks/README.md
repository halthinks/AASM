# AASM Operator Runbooks

These are short operational procedures backed by executable scenario tests.

```bash
aasm runbook list
```

Every run returns structured JSON with:

```text
runbook_id
status
valid
machine_id
checks
summary
evidence
```

A runbook is not a substitute for production-specific incident policy. It proves the AASM control path used by the procedure and gives operators a concrete starting point.

| Runbook | Document |
|---|---|
| Recover after lease loss | [lease-loss.md](lease-loss.md) |
| Inject a requirement without destroying the plan | [requirement-change.md](requirement-change.md) |
| Inspect and act on a learned no-good | [learned-no-good.md](learned-no-good.md) |
| Run a human approval gate with policy as data | [human-approval.md](human-approval.md) |
| Safely replay and fork a machine | [replay-fork.md](replay-fork.md) |
| Reconcile an UNKNOWN external effect | [unknown-effect.md](unknown-effect.md) |
| Diagnose a failed durable-history verification | [history-diagnosis.md](history-diagnosis.md) |
