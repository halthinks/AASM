# Changelog

All notable user-visible changes to AASM are documented here.

Detailed history through v0.27.0 is preserved in [`CHANGELOG_0.27_AND_EARLIER.md`](CHANGELOG_0.27_AND_EARLIER.md). History through v0.18 is also available separately in [`CHANGELOG_0.18_AND_EARLIER.md`](CHANGELOG_0.18_AND_EARLIER.md).

## [0.28.0] - 2026-08-11

AASM v0.28.0 adds clean distribution, immutable release evidence, a compatibility policy, and executable operator recovery procedures without introducing a parallel runtime. It carries forward the One-command local stack and Research Synthesis Hero Stack through the same `aasm.adoption.v1` path.

### Distribution and release integrity

- updated package metadata and public project URLs for `aasm-runtime`;
- added wheel and source-distribution structural verification;
- added clean-environment installation and installed-CLI smoke tests;
- added deterministic SHA-256 and JSON release manifests;
- added `release-history.json` for exact maintained historical release commits;
- added automatic immutable release tags and GitHub Releases through the GitHub Release API after CI and formal assurance pass;
- added explicit tag-target verification against the exact tested commit;
- added immutable wheel, source distribution, checksum, and manifest assets;
- added an externally gated PyPI Trusted Publisher job with no long-lived credential;
- added the `aasm/release` commit status;
- added release and compatibility documentation.

### Operator runbooks

- added `aasm runbook list`;
- added executable `aasm runbook RUNBOOK_ID` drills;
- added lease-loss recovery with stale ownership expiry and task reclaim;
- added additive requirement injection with selective impact and unrelated-work preservation;
- added learned no-good inspection with certificate and causal backjump checks;
- added quorum approval with denied under-approval and durable authorization;
- added safe replay and lineage-bearing fork verification;
- added explicit reconciliation of `UNKNOWN` external effects with unsafe retry blocked;
- added failed-history diagnosis against a copied stream without mutating canonical history;
- added one-page imperative documents and regression tests for every runbook.

### CI and formal contracts

- added a clean-wheel build/install job to ordinary CI;
- required release-history, wheel, source-distribution, installed-contract, and installed-runbook checks;
- extended formal workflow triggers and static contracts to release and runbook surfaces;
- retained Python 3.11–3.13, PostgreSQL, Docker Compose, Control Center JavaScript, TLA+, and SPIN gates.

### Compatibility

- package/runtime version is `0.28.0`;
- adoption contract is `aasm.adoption.v1 / 0.4.0`;
- remote protocol remains `aasm.remote.v1 / 0.19.0`;
- README keeps the current version, install path, runbooks, next release, and protocol boundary visible.
