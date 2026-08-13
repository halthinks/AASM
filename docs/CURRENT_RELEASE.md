# Current Release

This file is the release workflow's human-readable notes source for the package version currently on `main`.

## AASM v0.32.0 — Runtime/Formal Trace Conformance

AASM can now bind the production durable event stream to a versioned, lossless formal trace. Every event keeps its identity, order, raw payload, and SHA-256 digest. Unknown transitions remain explicitly unsupported; snapshot-only input is rejected; semantic witness failures point to exact source events.

See [`docs/RELEASE_0.32.md`](RELEASE_0.32.md) for the full release notes.
