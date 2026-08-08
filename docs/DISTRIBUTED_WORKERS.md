# Distributed Workers, Leases, and Quotas

AASM v0.7 turns the durable capability scheduler into an execution-coordination layer.

## Worker model

A `WorkerRecord` identifies an execution worker and links it to a durable `ResourceRecord`. Workers have lifecycle state (`ACTIVE`, `DRAINING`, `OFFLINE`, `STALE`), a heartbeat timeout, last-heartbeat time, and metadata.

## Lease lifecycle

`ACTIVE → COMPLETED | FAILED | RELEASED | EXPIRED`

A claim records task, worker, backing resource, demand, required capabilities, attempt number, acquisition/heartbeat/expiry times, and optional result/error metadata.

## Crash-safe claiming

For SQLite, AASM uses a dedicated `(machine_id, task_id)` task-claim reservation with a uniqueness constraint. Competing processes cannot both reserve the same unexpired task. Expired reservations can be reclaimed.

The event stream remains authoritative. After another process advances the machine, callers should resume from the durable store before continuing work from that process.

## Heartbeats and expiry

Workers heartbeat independently from task leases. Lease heartbeats extend expiry. `reap_stale_workers()` marks workers stale after their configured timeout and expires active leases they own so another worker can reclaim the work.

## Quotas

`QuotaPolicy` can scope limits to the whole machine, one worker, or one resource. It can cap active lease count, total leased capacity units, or both.

## Fork behavior

Worker, quota, and lease state is event-sourced in the machine snapshot. Historical forks therefore receive exactly the coordination state that existed at the fork event boundary. External execution is never replayed merely because control history was forked.
