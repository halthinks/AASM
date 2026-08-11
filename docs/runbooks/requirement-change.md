# Inject a requirement without destroying the plan

## Starting state

A plan contains active core work, dependent verification work, and an unrelated completed documentation node.

## Execute the drill

```bash
aasm runbook requirement-change
```

## Procedure

1. Submit the new requirement through `user_interrupt()` with explicit seed nodes.
2. Inspect the generated change-impact object.
3. Verify that only the seeds and downstream dependents are affected.
4. Confirm unrelated completed work remains unchanged.
5. Resolve the impact by resuming or retiring every affected node.
6. Verify the paused-task set is empty after resolution.

## Expected evidence

- requirement ID;
- impact ID;
- affected node list;
- unaffected node list;
- terminal impact resolution.

## Failure indicators

- the entire plan is discarded;
- an unrelated completed node is reopened;
- affected work continues under the old requirement;
- unresolved nodes silently disappear.

## Reset

Run the drill again to create a separate machine. Do not rewrite the prior impact history.
