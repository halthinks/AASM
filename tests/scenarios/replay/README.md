# Replay and fork acceptance scenario

AASM can reconstruct a historical snapshot at an exact durable event sequence and create a new machine from that boundary.

The fork has a new machine ID and an explicit `metadata.lineage` record containing the source machine, source sequence, and source event ID. External effects are not copied or re-executed by default.
