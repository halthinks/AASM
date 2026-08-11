# Run a human approval gate with policy as data

## Starting state

An irreversible publication proposal requires two affirmative approvals.

## Execute the drill

```bash
aasm runbook human-approval
```

## Procedure

1. Load the declared quorum policy.
2. Submit the proposal with only one approval and confirm denial.
3. Submit the same declared action with the required quorum.
4. Confirm an authorization ID and authority are recorded.
5. Execute only the authorized action.
6. Inspect the result and authorization event.

## Expected evidence

- under-approved attempt denied;
- quorum policy `required_votes = 2`;
- durable authorization event;
- authorized artifact publication result.

## Failure indicators

- execution before authorization;
- policy inferred from conversation instead of supplied as data;
- missing authorization identity;
- a denied attempt mutating the external artifact.

## Reset

Run the drill again. Each execution creates a separate machine and authority history.
