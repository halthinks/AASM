# S5.5 Integrated Core/Conflict Pipeline Qualification

**Date:** 2026-08-20  
**Qualified implementation commit:** `f90ee58ee48c60f5315f787acdbf514abe7f8f76`  
**Gate:** `aasm/core-conflict`  
**Semantic contract:** `aasm.core-conflict.v1 / 0.1.0`  
**Runtime contract:** `aasm.core-conflict.runtime.v1 / 0.1.0`  
**Admission:** `PRE_ADMISSION_ONLY`

## Qualification result

**PASS.** The committed S5.5 corpus was independently replayed from byte-identical GitHub blobs after a qualification-discovered defect was repaired. The checker completed with:

```text
S5.5 integrated core/conflict contracts: OK
.........                                                                [100%]
9 passed in 0.04s
```

This record does not claim an observed GitHub Actions result. The connected GitHub interface did not surface push-triggered workflow status for the permanent gate, so qualification was independently replayed from the exact committed blobs instead of treating an unobservable workflow as success.

The permanent repository workflow remains `.github/workflows/core-conflict.yml` and repeats the same compile, schema, contract-checker, and adversarial-test gate under Python 3.11.

## Exact qualified blobs

The local qualification inputs were verified against Git object blob SHA-1 identities before the result was accepted:

| Repository path | Git blob SHA-1 |
| --- | --- |
| `src/aasm/core_conflict.py` | `1651ff2c5e8eaf48fc484de452da5c13d7c15004` |
| `src/aasm/core_conflict_runtime.py` | `f360877ff663afb3e3d899aae1e4c9bb23e99a4d` |
| `tests/test_core_conflict.py` | `8850568fb6e3e0a8f1fdabafe04eeeb893589205` |
| `scripts/check_core_conflict_contracts.py` | `96f6e9ea7117b575737374033c1b9090641da435` |
| `schemas/core-conflict.schema.json` | `82b32c7bc8448fe74574bd60c10f9c6aaa342e8d` |

## Commands replayed

```bash
python -m compileall -q \
  src/aasm/core_conflict.py \
  src/aasm/core_conflict_runtime.py \
  scripts/check_core_conflict_contracts.py \
  tests/test_core_conflict.py
python -m json.tool schemas/core-conflict.schema.json >/dev/null
python scripts/check_core_conflict_contracts.py
pytest -q tests/test_core_conflict.py
```

Independent replay environment: Python 3.13.5, pytest 9.0.2. The permanent GitHub qualification workflow pins Python 3.11.

## Defect discovered by qualification

The initial S5.5 implementation represented a budget-exhausted reduction as `BUDGET_LIMITED_PARTIAL` but constructed the `CoreClaim` without setting its `budget_exhausted` field. The committed adversarial corpus correctly rejected that contradiction.

The defect was repaired in `f90ee58ee48c60f5315f787acdbf514abe7f8f76` by constructing the claim with all four semantics aligned:

- `claim_kind = BUDGET_LIMITED_PARTIAL`;
- `established = true` for the bounded partial claim actually established by exhaustion;
- explicit Evidence IDs;
- `budget_exhausted = true`.

The complete qualification corpus then passed.

## Qualified semantic guarantees

The S5.5 foundation now demonstrates all of the following against the committed implementation:

1. External solver/reference identity is preserved through `RAW -> NORMALIZED -> REDUCED -> RECHECKED` lineage.
2. Problem revision and semantic fingerprint bindings remain exact across the pipeline.
3. A smaller-looking core does not self-upgrade into an irreducibility or minimum claim.
4. Budget exhaustion is represented explicitly as `BUDGET_LIMITED_PARTIAL`, never as minimum/minimum-weight proof.
5. `IRREDUCIBLE` requires an independent full conflict recheck plus one independent satisfiable single-removal recheck for every member.
6. `IRREDUCIBLE` does not imply `MINIMUM_CARDINALITY`.
7. `MINIMUM_CARDINALITY` requires an explicit exhaustive-smaller-cardinalities certificate bound to the same problem semantic fingerprint.
8. `MINIMUM_WEIGHT` is a separate claim requiring complete member weights, an explicit objective, and an explicit global-optimum certificate bound to the same problem semantic fingerprint.
9. Member identity drift and cross-fingerprint substitution fail closed.
10. Round-trip serialization preserves deterministic identity and fingerprint.
11. The runtime cannot dispatch effects, mutate the problem, mint a new Core/Conflict authority plane, or admit learned constraints by existence.
12. Reuse as cross-run knowledge remains subordinate to S5.4 applicability and existing AASM authority.

## Authority ceiling

Qualification preserves the runtime ceiling:

```text
solver output authority       = NONE
core claim self-upgrade       = NONE
learned-constraint admission  = NONE
knowledge reuse               = S5.4 applicability required
effect dispatch               = NONE
problem mutation              = NONE
runtime admission             = PRE_ADMISSION_ONLY
public admission              = PRE_ADMISSION_ONLY
```

S5.5 therefore closes the integrated core/conflict foundation without changing AASM's existing truth, authority, effect, or public-admission planes.
