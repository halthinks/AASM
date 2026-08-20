# S4.10 Exact-Head Qualification Recovery

**Purpose:** restore exact-head qualification after the S4.10 permanent safety-governance corpus was materialized by a GitHub Actions bot commit.

## Why this checkpoint exists

The S4.10 corpus and its aggregate workflow are present on `main`, but the final materialization/cleanup commit was authored by `github-actions[bot]`. GitHub intentionally does not recursively trigger ordinary `push` workflows from commits created with the repository `GITHUB_TOKEN`. As a result, the final S4.10 source head can contain successful child contexts while still lacking exact-head aggregate contexts that normally run on every direct `main` update.

This document is intentionally a documentation-only direct-main checkpoint. It changes no AASM semantic contract, runtime behavior, authority rule, effect lifecycle, Evidence rule, resource rule, package version, adoption contract, or release state. Its purpose is to create a normal direct-main head on which the complete push-triggered qualification graph can execute.

## Qualification requirements

S4.10 is **not** considered fully closed merely because its source files exist. The exact checkpoint head must independently show the required dedicated, cumulative, formal, release-contract, and aggregate contexts as successful, including at minimum:

- `aasm/safety-governance`
- `aasm/engineering-s4`
- `aasm/engineering-quantity`
- `aasm/engineering-rule`
- `aasm/engineering-semantic-projection`
- `aasm/engineering-uncertainty-scenario-trace`
- `aasm/engineering-degraded-operation`
- `aasm/engineering-risk-irreversibility`
- `aasm/engineering-obligation-phase`
- `aasm/engineering-safety-envelope-hybrid-state`
- `aasm/engineering-epistemic-debt-manual-override`
- all inherited authority/effect/evidence/state-machine gates required by the cumulative release graph
- cumulative release/public-contract checks
- `aasm/ci-summary`

Only after exact-head evidence is green may the roadmap treat S4.10 as GATED and advance implementation to S5.1 governed Refinement Proposal/Loop.

## Permanent invariant

Workflow-generated commits may materialize or normalize source, but **their existence is not qualification evidence**. Qualification attaches to the exact source head that passed the required gates.
