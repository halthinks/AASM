# Fleet Provisioning and Live Execution Telemetry

AASM v0.17 connects the v0.16 fleet-admission decision to physical worker lifecycle **without turning a scheduling recommendation into deployment authority**.

## Separation of concerns

The control path is intentionally split:

1. `analyze_collaboration()` recommends useful concurrency.
2. `FleetControlPolicy` may enforce an admission limit on AASM task leases.
3. `plan_fleet_provisioning()` compares that target with registered ACTIVE workers.
4. `propose_provisioning()` creates a durable external `EffectSpec`.
5. A controller/human/policy must explicitly call `authorize_effect()`.
6. `execute_provisioning()` invokes a registered provider adapter through the normal AASM idempotent effect boundary.

A fleet recommendation never creates or destroys infrastructure by itself.

## Provisioning adapters

Provider integration implements:

```python
class ProvisioningAdapter(Protocol):
    def apply(self, request: ProvisioningRequest, idempotency_key: str) -> dict: ...
```

Adapters can target a local process supervisor, Kubernetes, a cloud VM service, a remote Codex host pool, or another execution environment. AASM does not assume credentials or provider semantics.

Use `ProvisioningRegistry` when the HTTP control plane should execute authorized provisioning effects. If the server has no registry/provider adapter, `/provisioning/{effect_id}/execute` fails closed.

Provisioned infrastructure is **not automatically registered as an AASM worker**. The actual worker process must connect and register/heartbeat. This prevents provider success from being confused with a healthy executor.

Drain requests prefer currently idle ACTIVE workers. After a successful drain effect, targeted registered workers transition to `DRAINING`; the provider adapter remains responsible for the external lifecycle action.

## Live telemetry

Remote workers automatically emit `STARTED`, `COMPLETED`, and `FAILED` telemetry around every lease. Custom workers/executors may additionally stream:

- `LOG`
- `PROGRESS`
- `ARTIFACT`
- `HEARTBEAT`

Telemetry records carry worker/task/lease identity, timestamps, optional duration, progress, metrics, messages, artifact references, and metadata such as `task_class`.

The telemetry ledger is bounded by `TelemetryPolicy.max_records`; it is an operator/control signal, not an unlimited log archive. Large logs/artifacts should live in an external store and be referenced by URI or stable artifact ID.

## Observed-duration feedback

Completed telemetry produces duration statistics by task and task class. When enabled, AASM injects observed mean duration into future runnable task demands before collaboration analysis. Explicit task estimates can opt out with `metadata.lock_estimated_duration=true`.

This creates a live feedback loop:

```text
worker completion
    -> observed duration
    -> critical-path / total-work estimate
    -> collaboration recommendation
    -> fleet admission limit
    -> optional authority-gated provisioning plan
```

Telemetry-driven recalculation occurs only after the lease has been durably completed, so the just-finished task is not accidentally counted as runnable during the refresh.

## Authority and safety

Provisioning remains an external side effect. It inherits AASM's effect guarantees:

- proposed before execution;
- explicit authorization required;
- stable idempotency key per request;
- no blind retry after UNKNOWN outcomes;
- durable execution/result/error provenance.

Provisioning authorization does not bypass credentials, cloud IAM, sandboxing, network policy, billing controls, or provider-specific safety requirements.

## Operator surfaces

Local CLI:

```bash
aasm telemetry MACHINE_ID --store runs.db
aasm provision-plan MACHINE_ID --store runs.db --provider my-provider --resource-id coding-pool
aasm provision-propose MACHINE_ID --store runs.db --request provision.json
```

Remote API/client exposes telemetry reporting/configuration plus provisioning status, plan, proposal, authorization, and provider execution when a registry is configured.

The Control Center shows live telemetry count/latest event/artifacts and provisioning pending/executed state separately from collaboration recommendation and fleet-admission enforcement.
