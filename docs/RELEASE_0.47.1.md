# AASM v0.47.1 — Apache-2.0 License Transition

AASM v0.47.1 is a licensing/packaging patch over v0.47.0. It does not change the governed SII runtime, solver portfolio, authority semantics, certification behavior, replay semantics, or public adoption contract.

## Change

The AASM project-wide declared license is Apache License 2.0.

```text
package: 0.47.1
adoption: aasm.adoption.v1 / 0.23.0
certification: aasm.certification.v1 / 0.2.0
SII: aasm.sii.v1 / 0.3.0
license: Apache-2.0
```

The patch introduced:

- the standard Apache License 2.0 text in `LICENSE`;
- `NOTICE` with AASM attribution;
- PEP 639/SPDX package metadata `Apache-2.0`;
- no legacy `License :: ...` classifier, matching the current setuptools PEP 639 requirements;
- both `LICENSE` and `NOTICE` declared as package license files;
- `NOTICE` included in source distributions;
- contribution terms aligned to Apache-2.0;
- release/source gates that verify the active license, reject legacy license classifiers, and verify packaged attribution files.

## Project-wide relicensing declaration

AASM does **not** designate v0.47.1 as the first or only Apache-2.0 point in the project's history.

To the extent AASM has the legal right to relicense the relevant material, prior AASM versions—including versions first distributed under MIT—are **also offered under Apache-2.0** under the project-wide declaration in `LICENSE_POLICY.md`.

Earlier MIT grants already received by users remain valid. That is a surviving permission for those recipients, not a statement that earlier AASM versions are MIT-only.

In short:

```text
AASM project-wide declared license  = Apache-2.0
prior versions                      = also offered under Apache-2.0 where AASM has relicensing rights
previously granted MIT permissions  = remain valid for recipients
prior AASM versions                 != MIT-only
```

## Runtime invariants unchanged

```text
UTILITY MAY BUY COMPUTE / SEARCH / CONTEXT.
UTILITY NEVER BUYS TRUTH / STATE AUTHORITY / SELF VERIFICATION.
REQUIRED VERIFICATION IS NEVER REDUCED BY SII.
```

All v0.47.0 solver, SII, formal-verification, memory, reuse, persistence, scheduler, and replay contracts remain unchanged.

See `LICENSE`, `NOTICE`, and `LICENSE_POLICY.md` for the current AASM licensing declaration.
