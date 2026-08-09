# Provider adapters, external artifacts, and execution controls

AASM v0.18 adds three operator-facing capabilities on top of the v0.17 physical-fleet/telemetry layer:

1. provider-specific provisioning adapters,
2. pluggable external text artifact/log backends,
3. durable worker lifecycle controls.

The authority boundary does not change.

## Provisioning adapters

A fleet recommendation does not create infrastructure. The path remains:

`collaboration evidence -> fleet admission -> provisioning plan -> EffectSpec -> explicit authorization -> provider adapter`

`CommandProvisioningAdapter` executes an argv list produced by caller-supplied code. It never invokes a shell string. Credentials, environment, network access, and deployment policy remain the responsibility of the process hosting the adapter.

`KubernetesScaleAdapter` is the first concrete provider adapter. It uses explicit `kubectl` argv calls to read the current replica count and scale a named workload. The provisioning request must contain `metadata.workload`; it may also set `metadata.kind` and `metadata.namespace`.

Because the Kubernetes adapter is called only from `execute_provisioning()`, it inherits the durable external-effect lifecycle. A proposed fleet effect must be authorized before the adapter can execute, and retries retain the same AASM idempotency key.

The adapter does not claim that a newly created replica is a healthy AASM worker. A physical worker becomes usable only after it connects to the control plane, registers, and heartbeats.

## External artifact backends

Large logs and artifacts should not be embedded indefinitely in the event-sourced machine snapshot. v0.18 adds an `ArtifactBackend` protocol and registry.

Two backends ship with the runtime:

- `MemoryArtifactBackend` for tests and short-lived integrations.
- `LocalDirectoryArtifactBackend` for persistent local text artifacts.

Both return stable artifact references. The local backend sanitizes namespace/name components and resolves every path beneath one configured root; path traversal outside that root is rejected.

`AASMEngine.store_text_artifact()` stores the content in the selected backend and persists only the reference and provenance in AASM. When worker/task/lease IDs are supplied, an `ARTIFACT` telemetry record is also emitted.

The remote control plane can expose configured artifact backends through `POST /v1/machines/{machine_id}/artifacts/text`. No backend is created implicitly; if the server has no `ArtifactBackendRegistry`, the endpoint fails closed.

The built-in v0.18 artifact contract is intentionally text-focused. Binary/object-store backends can implement the same ref-oriented pattern without making the core event log a blob store.

## Worker execution controls

v0.18 adds durable control actions:

- `DRAIN`: stop new task admission to the worker while allowing its active lease to finish.
- `RESUME`: return the worker to `ACTIVE` admission state.
- `OFFLINE`: stop new work and release that worker's active leases so ownership is not stranded.

Every action requires a worker ID, actor label, and reason. AASM records previous/new status plus any released lease IDs in `worker_control_history`.

These controls change AASM worker state. They do not terminate a VM, Kubernetes pod, or external process. Provider-side destruction remains a separately proposed and authorized provisioning effect.

CLI surfaces:

```bash
aasm execution-controls MACHINE_ID --store runs.db

aasm worker-control MACHINE_ID --store runs.db \
  --worker worker-7 \
  --action DRAIN \
  --actor operator \
  --reason "maintenance"

aasm artifacts MACHINE_ID --store runs.db --limit 50
```

Remote surfaces:

- `GET /v1/machines/{machine_id}/execution-controls`
- `POST /v1/machines/{machine_id}/workers/{worker_id}/control`
- `GET /v1/machines/{machine_id}/artifacts`
- `POST /v1/machines/{machine_id}/artifacts/text`

The Control Center exposes the same worker lifecycle controls behind the existing bearer-authenticated API boundary.
