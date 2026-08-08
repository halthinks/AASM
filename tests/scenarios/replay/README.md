# Deterministic replay scenario

Acceptance property: reducing the persisted event stream produces the same canonical machine snapshot as live execution for all state and metadata changes covered by the v0.2 event core.

Automated by `tests/test_persistence.py::test_memory_store_replay_matches_live_state`.
