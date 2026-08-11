# AASM v0.28.2 — Distribution Release Hardening

AASM v0.28.2 closes the packaging gap discovered during independent v0.28.1 verification.

## What changed

The published source distribution now includes the repository-level contracts its bundled tests inspect: profiles, schemas, formal models, runbooks, examples, GitHub workflows, release scripts, and the complete test suite.

CI extracts the built sdist into a clean directory and runs a standalone smoke test without a Git checkout. The smoke validates the public adoption contract, executes an operator runbook, and checks representative members from every contract-bearing directory.

## Compatibility boundary

```text
package/runtime:   aasm-runtime 0.28.2
adoption contract: aasm.adoption.v1 / 0.4.1
remote protocol:   aasm.remote.v1 / 0.19.0
```

The runtime reducer, persistence boundary, effects, workers, leases, conflict learning, replay, and Control Center remain on the existing implementation path.

The next release is **v0.29.0 — Thin LangGraph Adapter**.

## Carried-forward release integrity

v0.28.1 established reproducible double builds, exact asset read-back, no-overwrite publication, and `historical-release-report.json`. v0.28.2 retains every one of those controls while making the sdist independently testable.
