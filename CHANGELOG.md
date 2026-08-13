# Changelog

All notable user-visible changes to AASM are documented here.

Detailed history through v0.27.0 is preserved in [`CHANGELOG_0.27_AND_EARLIER.md`](CHANGELOG_0.27_AND_EARLIER.md). History through v0.18 is also available separately in [`CHANGELOG_0.18_AND_EARLIER.md`](CHANGELOG_0.18_AND_EARLIER.md).

## [0.31.0] - 2026-08-12

AASM v0.31.0 adds `aasm.scopes.v1 / 0.1.0` hierarchical decision scopes while retaining one authoritative machine and the existing event/reducer/store path.

### Hierarchical scopes

- permanent root scope plus strategy, architecture, implementation, workstream, and custom kinds;
- scope-local Decisions, Obligations, evidence, locks, conflicts, explanations, constraints, and fairness debt;
- explicit inheritance, isolation, override, and override-denial policy;
- validated acyclic cross-scope dependencies;
- causal cross-scope backjumping preserving unrelated sibling subtrees;
- scoped restart retaining parents, pinned decisions, evidence, and certified hard knowledge;
- atomic multi-scope candidate activation with final parent revalidation;
- explicit legacy-flat migration without rewriting historical events;
- Python, CLI, authenticated HTTP, Control Center, schemas, TLC, and SPIN surfaces.

### Compatibility

- package/runtime: `0.31.0`;
- adoption contract: `aasm.adoption.v1 / 0.7.0`;
- scope contract: `aasm.scopes.v1 / 0.1.0`;
- remote protocol remains `aasm.remote.v1 / 0.19.0`;
- next release: v0.32.0 Runtime/Formal Trace Conformance;
- roadmap now carries the Semantic Solver Program through v0.45.0.

## [0.30.0] - 2026-08-11

AASM v0.30.0 adds a framework-neutral Adapter Conformance Kit over the existing public API and event/reducer authority path.

### Adapter conformance

- added `aasm.adapter.conformance.v1 / 0.1.0`;
- advanced `aasm.adoption.v1` to `0.6.0`;
- retained `aasm.langgraph.v1 / 0.1.0` and `aasm.remote.v1 / 0.19.0`;
- added versioned capability and authority declarations;
- added success, contradiction, requirement-change, lease-loss, `UNKNOWN`-effect, restart, replay, and fork scenarios;
- added semantic-result and evidence-provenance checks;
- added durable-history and replay-versus-persisted-snapshot validation;
- added direct Store mutation auditing and duplicate-authority rejection;
- added explicit `PASS`, `FAIL`, and `INCONCLUSIVE` reports with finding codes, event references, coverage, audit detail, and SHA-256 fingerprint;
- added the reference `LangGraphConformanceDriver` and deliberately broken negative fixtures;
- added capability and report JSON schemas.

### Public operation

- added `aasm adapter-conformance` and `aasm adapter-conformance-list`;
- added authenticated `/adapter-conformance` and `/v1/conformance/adapters/{adapter_id}` endpoints;
- added an Adapter Conformance panel to the existing Control Center;
- added installed-wheel and hosted conformance CI gates;
- documented that `CONFORMANCE_HOOK_NOT_SANDBOX`: in-process auditing does not replace isolation for untrusted code.

### Correctness boundary

- no parallel runtime, reducer, scheduler, effect ledger, worker/lease system, event store, or persistence path was introduced;
- unsupported required scenarios are `INCONCLUSIVE`, never silently passed;
- an adapter can fail conformance even when its functional output appears correct;
- a pass applies to the exact declared driver versions and exercised bounded scenarios.

## [0.29.0] - 2026-08-11

AASM v0.29.0 adds the first thin framework adapter without changing the canonical event/reducer authority path. Existing LangGraph applications keep graph topology, routing, interrupts, checkpoint data, and domain state; AASM supplies durable decisions, obligations, evidence, effects, conflict learning, replay, and recovery underneath them.

### Thin LangGraph adapter

- added deterministic `configurable.thread_id` and optional run identity to AASM machine binding;
- added idempotent bind/resume and collision rejection for unrelated machines;
- added dependency-neutral sync and async node wrappers that preserve original state updates and `Command` objects;
- added selected decision, obligation, evidence, and effect mapping helpers;
- added `CONTINUE`, `REPAIR`, `BACKJUMP`, `PAUSE`, `RESTART`, and `FORK` recovery directives;
- kept LangGraph checkpoint state explicitly separate from AASM machine authority;
- added certified learned-no-good creation and causal backjump through existing calculus and assurance APIs;
- added a controlled ordinary-versus-AASM comparison graph demonstrating failed-assumption identification, unrelated-work preservation, learned-constraint reuse, exact replay, and provenance.

### Adoption and inspection

- added `aasm.langgraph.v1 / 0.1.0`;
- advanced `aasm.adoption.v1` to `0.5.0`;
- retained `aasm.remote.v1 / 0.19.0`;
- added `langgraph-binding` CLI support;
- added `langgraph` and `integrations` inspection surfaces;
- added the adapted-run Control Center panel and existing authenticated inspection endpoint support;
- added binding and recovery JSON schemas, migration documentation, release notes, and a runnable example;
- added an optional `langgraph>=1.2,<2` dependency extra and real-framework CI job;
- kept core installation and imports independent of LangGraph.

### Correctness boundary

- no framework-private AASM truth or competing machine authority was introduced;
- no duplicate graph runtime, checkpoint store, scheduler, lease system, effect ledger, event store, or persistence path was added;
- wrappers call the original node and return its exact output;
- `PAUSE` records durable AASM authority but leaves interrupt/checkpoint control with LangGraph;
- adapter events are append-only provenance and replay through the existing reducer without mutating framework state.

## [0.28.2] - 2026-08-11

AASM v0.28.2 makes the source distribution self-contained and self-testing. It changes packaging and validation only; the deterministic runtime, `aasm.adoption.v1` authority boundary, and `aasm.remote.v1 / 0.19.0` protocol remain unchanged.

### Source-distribution integrity

- added `MANIFEST.in` covering repository contracts, profiles, schemas, formal models, runbooks, examples, workflows, scripts, and tests;
- added an extracted-sdist smoke test that runs without a Git checkout;
- added representative member checks for the complete source contract;
- added `build==1.5.0` to the contributor test extra so the source-package gate is reproducible;
- updated the public distribution contract to declare standalone source-distribution validation;
- kept release publication immutable: v0.28.1 assets are not overwritten.

## [0.28.1] - 2026-08-11

AASM v0.28.1 hardens release publication after exercising the real v0.28.0 workflow. It does not create a parallel runtime or change the `aasm.adoption.v1` authority boundary. The One-command local stack, Research Synthesis Hero Stack, and seven Operator runbooks continue through the existing event/reducer path.

### Reproducible packaging

- pinned setuptools `83.0.0` and wheel `0.47.0` in the isolated build system;
- pinned build `1.5.0` and twine `6.2.0` in CI and release publication;
- migrated to PEP 639 `license = "MIT"` and `license-files = ["LICENSE"]` metadata;
- derived `SOURCE_DATE_EPOCH` from the exact release commit and fixed `PYTHONHASHSEED=0`;
- required two independent builds to produce identical wheel and source-distribution hashes;
- retained clean-wheel installation plus installed adoption-contract and runbook smoke tests.

### Immutable publication

- established an explicit no-overwrite policy for versioned release assets;
- gated release on the exact `main` commit plus both `aasm/ci-summary` and `aasm/formal-assurance` success;
- removed tag-push and `--clobber` asset-overwrite paths;
- required existing tags to resolve to the exact recorded commit;
- required the complete GitHub asset set, byte counts, and SHA-256 digests to match local release files;
- added `historical-release-report.json` and included it in checksums and the release manifest;
- represented unavailable older refs as `PENDING_OWNER_PUBLICATION` instead of failing the current release or claiming they were published;
- added explicit release-hardening regression contracts.

### Planning

- expanded the execution roadmap through v0.34.0;
- made v0.29.0 the Thin LangGraph Adapter;
- planned adapter conformance, hierarchical decision scopes, runtime/formal trace conformance, signed provenance, and distributed recovery certification with explicit exit gates.

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
- retained Python 3.11->3.13, PostgreSQL, Docker Compose, Control Center JavaScript, TLA+, TLC, and SPIN gates.

### Compatibility

- package/runtime version is `0.28.0`;
- adoption contract is `aasm.adoption.v1 / 0.4.0`;
- remote protocol remains `aasm.remote.v1 / 0.19.0`;
- README keeps the current version, install path, runbooks, next release, and protocol boundary visible.
