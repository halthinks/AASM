# AASM v0.48.1 — Project-Wide Apache-2.0 Policy Correction

AASM v0.48.1 is a licensing-policy correction over v0.48.0. Runtime behavior and the v0.48 cross-run knowledge contracts are unchanged.

## Corrected licensing declaration

AASM's declared project license is **Apache License, Version 2.0 (`Apache-2.0`) across the project**.

The authoritative project declaration is `LICENSE_POLICY.md`:

> **AASM is Apache-2.0 across the project, including prior AASM versions to the extent AASM has the rights to relicense them. Previously granted MIT permissions remain valid for their recipients, but prior AASM versions are not designated MIT-only.**

Accordingly, prior AASM versions that were first distributed under MIT are **also offered under Apache-2.0** to the extent AASM has the necessary relicensing rights.

Previously granted MIT permissions remain valid for recipients who received those grants. v0.48.1 does not attempt to revoke them. Their continued validity is separate from AASM's project-wide Apache-2.0 licensing declaration.

Older archived copies may still physically contain the historical license file that was packaged when they were first distributed. That does not mean those AASM versions are MIT-only; `LICENSE_POLICY.md` provides the additional Apache-2.0 grant where AASM has the rights to do so.

## Packaging

Current distributions continue to carry:

```text
license expression: Apache-2.0
license files:       LICENSE, NOTICE
legacy classifier:   NONE
```

The release gate now additionally:

- requires `LICENSE_POLICY.md` and its project-wide Apache grant;
- requires explicit treatment of earlier MIT grants as surviving recipient permissions rather than an MIT-only version classification;
- rejects stale wording that calls v0.47.1 the first/only Apache release;
- rejects stale wording that says v0.47.0 remains an MIT-only distribution;
- preserves all existing Apache-2.0 / PEP 639 / `LICENSE` / `NOTICE` checks.

## Runtime and contract identity

```text
package/public surface:                    0.48.1
aasm.adoption.v1 /                         0.24.0
aasm.knowledge.cross-run.v1 /              0.1.0
aasm.knowledge.cross-run.admission.v1 /    0.1.0
aasm.principal.cross-run-map.v1 /          0.1.0
aasm.certification.v1 /                    0.2.0
aasm.sii.v1 /                              0.3.0
license:                                    Apache-2.0
runtime semantics:                          unchanged from v0.48.0
```

No cross-run admission, memory, reuse, SII, native solver, formal-verification, scheduler, persistence, authority, or replay semantics change in this patch.

Next: **v0.49.0 — Semantic Solver Release Candidate**.
