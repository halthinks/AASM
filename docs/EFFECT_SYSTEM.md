# Durable Effect System

AASM v0.3 introduces a durable effect boundary between **deciding** and **doing**.

An effect represents an externally observable operation such as writing a file, running a command, calling an API, invoking a tool, or requesting a human action. AASM persists the effect record separately from the machine snapshot and records lifecycle events in the machine event stream.

## Lifecycle

`PROPOSED → AUTHORIZED → RUNNING → SUCCEEDED | FAILED | UNKNOWN`

`UNKNOWN` is intentionally different from `FAILED`. It means AASM knows an attempt started but cannot prove whether the external system completed it. Automatically retrying such an operation can duplicate a real-world side effect.

## Idempotency

Every effect has an `idempotency_key`. Re-proposing the same key for one machine returns the original durable effect record instead of creating a second operation. Every retry receives the same key.

AASM prevents duplicate invocation after a recorded success. For systems that support provider-side idempotency, executors should also forward the AASM idempotency key to the provider. This combination provides the strongest practical duplicate protection.

## Crash semantics

A normal `AASMEngine.resume(machine_id, store)` is now **passive**: it reconstructs the run without reclassifying live effects. This matters for stateless HTTP/control-plane inspection, where another host may still be legitimately executing a `RUNNING` effect.

When a process actually died and its in-flight effects must be reconciled, use:

```python
engine = AASMEngine.resume(machine_id, store, recover_effects=True)
```

or `AASMEngine.recover_unfinished(store)`, which opts into effect recovery for unfinished runs.

That recovery path converts unresolved `RUNNING` effects to `UNKNOWN`. By default, `execute_effect()` refuses to retry an `UNKNOWN` effect. The caller must reconcile the external outcome using `reconcile_effect()` or explicitly opt into `retry_on_unknown` when the executor is known to be retry-safe.

This prevents both dangerous patterns:

1. external operation succeeds; the process dies before local success is recorded; restart blindly repeats the operation;
2. a healthy remote worker is still executing; a read-only dashboard/API request resumes the run and incorrectly declares its effect `UNKNOWN`.

## Retry semantics

`RetryPolicy` controls `max_attempts`, `retry_on_failure`, and `retry_on_unknown`. Failures are retryable only when explicitly configured. Unknown outcomes are stricter because they may already have succeeded externally.

## Current boundary

AASM persists effect intent, authorization, attempts, status, results, errors, evidence, and idempotency metadata. It does not claim that arbitrary external systems themselves are transactional. Exactly-once behavior across a network boundary requires either provider-side idempotency or reconciliation.
