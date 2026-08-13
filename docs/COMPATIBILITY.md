# AASM Compatibility Policy

AASM is pre-1.0 experimental software. The project still declares a supported adoption surface so applications do not have to depend on every historical module or internal implementation detail.

## Current identities

| Identity | Current value |
|---|---|
| Package/runtime | `0.32.0` |
| Adoption contract | `aasm.adoption.v1 / 0.8.0` |
| Scope contract | `aasm.scopes.v1 / 0.1.0` |
| Trace contract | `aasm.trace.v1 / 0.1.0` |
| Semantic trace contract | `aasm.trace.semantic.v1 / 0.1.0` |
| LangGraph adapter | `aasm.langgraph.v1 / 0.1.0` |
| Adapter conformance | `aasm.adapter.conformance.v1 / 0.1.0` |
| Remote protocol | `aasm.remote.v1 / 0.19.0` |

A package release does not automatically require a remote-protocol change.

## Support classes

**SUPPORTED** — documented golden-path behavior declared by `aasm.adoption.v1`. Breaking changes require explicit versioning, changelog entries, tests, and migration/deprecation guidance when practical.

**EXPERIMENTAL** — available for evaluation but may change between pre-1.0 releases.

**INTERNAL** — no compatibility promise. Applications should not import versioned runtime internals, mutate snapshots directly, write AASM tables directly, or depend on undocumented event payload structure.

## Authority compatibility

The compatibility boundary is architectural as well as syntactic:

```text
public operation
  → existing event creation
  → existing production reducer
  → canonical snapshot
  → configured AASM store
```

Adapters, scopes, trace tools, and future semantic components must not become competing sources of canonical truth.

## Hierarchical scope compatibility

Historical flat calculus records remain valid as records in the canonical `root` scope. Explicit migration adds root metadata through ordinary runtime events; history is not rewritten.

## Trace compatibility

Trace projection is read-only. The trace contract requires:

- authoritative durable event input;
- preserved source order and event identity;
- explicit support classification;
- no silent dropping of unknown event types;
- no conversion of final snapshots into invented transition histories.

Semantic refinement is intentionally partial: events without an adequate witness are unsupported/inconclusive rather than guessed into proof.

## Release compatibility

A release is identified by its immutable tag, exact commit SHA, wheel/source-distribution SHA-256 values, and `release-manifest.json`. Existing version tags are never moved and existing release assets are never overwritten. Corrections require a new version.

The source distribution includes repository-level profiles, schemas, formal models, runbooks, workflows, examples, release scripts, and tests needed by the standalone source-package smoke gate.

## What this policy does not guarantee

Compatibility does not establish the truth of domain evidence, correctness of external services, physical accuracy of simulations, or safety of untrusted third-party code. Those require their own validation boundaries.
