# Adapter Conformance Kit

AASM v0.30.0 adds a framework-neutral way to test whether an integration preserves the supported AASM authority boundary.

```text
adapter or framework
        ↓ explicit conformance driver
AASM public adoption surface
        ↓
existing event/reducer runtime
        ↓
existing Memory / SQLite / PostgreSQL stores
```

The kit does not replace the adapter, runtime, reducer, scheduler, effect ledger, worker/lease system, or database. It executes bounded scenarios and independently inspects what the canonical AASM history says happened.

## Quick start

Run every required scenario against the built-in LangGraph driver:

```bash
aasm adapter-conformance --adapter langgraph
```

Run one scenario while developing an adapter:

```bash
aasm adapter-conformance \
  --adapter langgraph \
  --scenario contradiction \
  --output conformance-report.json
```

List drivers and required scenarios:

```bash
aasm adapter-conformance-list
```

Python:

```python
from aasm import run_adapter_conformance

report = run_adapter_conformance("langgraph")
assert report.status == "PASS"
```

Authenticated HTTP:

```text
GET /adapter-conformance
GET /v1/conformance/adapters/langgraph
GET /v1/conformance/adapters/langgraph?scenario=success
```

The existing Control Center contains a **Run LangGraph conformance** action and renders the complete machine-readable report.

## Contract identity

```text
contract: aasm.adapter.conformance.v1
version:  0.1.0
```

This contract version is separate from:

```text
package/runtime:    aasm-runtime 0.30.0
adoption contract:  aasm.adoption.v1 / 0.6.0
LangGraph adapter:  aasm.langgraph.v1 / 0.1.0
remote protocol:    aasm.remote.v1 / 0.19.0
```

## Required scenarios

| Scenario | What the kit verifies |
|---|---|
| `success` | Original framework output survives; mandatory work reaches `COMMITTED`; evidence and a `PASS` semantic result retain producer/provenance links |
| `contradiction` | Evidence produces a conflict, explanation, independently verified hard no-good, causal backjump, unrelated-work preservation, and recurrence blocking |
| `requirement_change` | Selective steering identifies and pauses only the affected plan region and preserves unrelated completed work |
| `lease_loss` | Stale ownership expires, the task is reclaimed under a new lease, attempts advance, and the recovery lease completes |
| `unknown_effect` | A process-loss outcome becomes `UNKNOWN`, unsafe retry is blocked, and explicit reconciliation preserves one effect identity |
| `restart` | Speculative decisions are suspended while pinned decisions and certified hard knowledge survive |
| `replay` | Durable history verifies and reconstructs the exact persisted snapshot |
| `fork` | A new machine receives explicit source lineage and independently replayable history |

A driver that does not support a required scenario receives `INCONCLUSIVE`, not `PASS`.

## Result meanings

### `PASS`

Every selected scenario was declared supported and every authority, persistence, evidence, recovery, history, and replay check passed.

### `FAIL`

At least one exercised check failed. The report includes:

- finding code;
- severity;
- scenario;
- message;
- event ID when a durable event can identify the failure location;
- exact failed checks and supporting detail.

Representative finding codes include:

```text
DIRECT_STORAGE_WRITE
DUPLICATE_OR_BYPASSED_AUTHORITY
DURABLE_HISTORY_INVALID
REPLAY_MISMATCH
SCENARIO_CONTRACT_VIOLATION
DRIVER_EXCEPTION
```

### `INCONCLUSIVE`

The selected contract could not be established because a required capability or scenario was not exercised. It is not a pass and it does not imply that the adapter is unsafe.

## Capability declaration

A driver returns an `AdapterCapabilityDeclaration` before execution. It identifies:

```text
adapter identity and version
driver identity and version
supported scenarios
supported recovery actions
machine-truth authority
framework-state authority
decision authority
effect authority
worker/lease authority
recovery authority
direct-storage-write policy
duplicate-authority claims
public-API usage
```

A conforming declaration says:

```text
machine_truth_authority = AASM_EVENT_HISTORY
decision_authority = AASM
effect_authority = AASM
worker_lease_authority = AASM
recovery_authority = AASM
direct_storage_writes = false
duplicate_authorities = []
uses_public_aasm_api = true
```

Framework checkpoints, graph state, or UI state may remain authoritative for their own framework concerns. They may not become competing AASM machine truth.

## Driver protocol

A driver implements two methods:

```python
from aasm import (
    AdapterCapabilityDeclaration,
    AdapterConformanceContext,
    AdapterScenarioOutcome,
)

class MyDriver:
    def capability_declaration(self) -> AdapterCapabilityDeclaration:
        ...

    def run_scenario(
        self,
        scenario_id: str,
        context: AdapterConformanceContext,
    ) -> AdapterScenarioOutcome:
        ...
```

The context supplies:

- the current public `AASMEngine` implementation;
- an audited Store proxy;
- deterministic scenario and namespace identity;
- an explicit external-effect-executor operation for simulating durable effect ownership without misclassifying it as an adapter database bypass.

The outcome supplies observations. The kit does not trust those observations by themselves; it resumes the canonical machine, verifies durable history, compares replay and persistence, resolves evidence references, and runs scenario-specific checks.

## Persistence audit

`AuditedStore` records mutating Store calls and classifies whether they originated through the established AASM engine/runtime path or an explicitly authorized external-executor operation.

A direct call such as:

```python
context.store.save_effect(...)
```

from adapter code is reported as `DIRECT_STORAGE_WRITE`, even when the rest of the scenario appears functionally correct.

### Security boundary

```text
CONFORMANCE_HOOK_NOT_SANDBOX
```

The audit is an in-process diagnostic hook. Python code with deliberate access to private objects can evade in-process instrumentation. Run untrusted adapters in a separate process, container, VM, or host and combine this semantic conformance report with that isolation boundary.

## Report structure

The report contains:

```text
contract identity and version
adapter capability declaration
overall PASS | FAIL | INCONCLUSIVE
per-scenario checks and findings
machine IDs
replay and persisted snapshot hashes
history issue detail
evidence and semantic-result counts
coverage summary
mutation audit
report SHA-256 fingerprint
```

Schemas:

```text
schemas/adapter-capability.schema.json
schemas/adapter-conformance-report.schema.json
```

## Built-in LangGraph driver

`LangGraphConformanceDriver` exercises the thin v0.29 adapter through the same public methods used by applications. It does not add a test-only reducer, persistence path, effect ledger, scheduler, or recovery engine.

The reference driver covers all eight scenarios and is available under both aliases:

```text
langgraph
aasm.langgraph.v1
```

## Negative fixtures

The regression suite includes deliberately broken drivers that:

- write directly to the Store;
- claim framework checkpoint state as machine truth;
- omit a required scenario;
- tamper with persisted state outside the event history.

The kit must reject or mark each one inconclusive for the documented reason. This proves that the evaluator is capable of failing an adapter rather than merely approving the reference implementation.

## What a pass does not prove

A conformance pass does not prove:

- every possible code path in an adapter;
- correctness of an external service;
- truth of domain evidence;
- safety of untrusted code in the same process;
- behavior outside the declared versions and exercised scenarios.

It proves that the exact adapter driver and selected bounded scenarios preserved the declared AASM contract under the recorded test conditions.
