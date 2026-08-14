# AASM v0.47.1 — Apache-2.0 License Transition

AASM v0.47.1 is a patch release over v0.47.0. It does not change the governed SII runtime, solver portfolio, authority semantics, certification behavior, replay semantics, or public adoption contract.

## Change

The active project and distribution license changes from MIT to Apache License 2.0.

```text
package: 0.47.1
adoption: aasm.adoption.v1 / 0.23.0
certification: aasm.certification.v1 / 0.2.0
SII: aasm.sii.v1 / 0.3.0
license: Apache-2.0
```

The patch includes:

- the standard Apache License 2.0 text in `LICENSE`;
- `NOTICE` with AASM attribution;
- SPDX package metadata `Apache-2.0`;
- the Apache OSI classifier;
- both `LICENSE` and `NOTICE` declared as package license files;
- `NOTICE` included in source distributions;
- contribution terms updated to Apache-2.0;
- release/source gates that verify the active license and packaged attribution files.

## Historical release integrity

The existing `v0.47.0` release is not rewritten. Its published artifacts remain the original MIT-licensed distribution. v0.47.1 is the first Apache-2.0 AASM release.

## Runtime invariants unchanged

```text
UTILITY MAY BUY COMPUTE / SEARCH / CONTEXT.
UTILITY NEVER BUYS TRUTH / STATE AUTHORITY / SELF VERIFICATION.
REQUIRED VERIFICATION IS NEVER REDUCED BY SII.
```

All v0.47.0 solver, SII, formal-verification, memory, reuse, persistence, scheduler, and replay contracts remain unchanged.
