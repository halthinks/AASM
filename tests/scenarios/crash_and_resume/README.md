# Crash and resume scenario

Acceptance property: a durable AASM run can be reconstructed from SQLite after the original engine instance disappears, with the same canonical derived state, and can continue through legal transitions.

Automated by `tests/test_persistence.py::test_sqlite_resume_after_engine_is_discarded`.
