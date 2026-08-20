#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def require(path: str, *tokens: str) -> None:
    value = text(path)
    missing = [token for token in tokens if token not in value]
    if missing:
        raise SystemExit(f"{path} missing S5.5 contract tokens: {missing}")


def forbid(path: str, *tokens: str) -> None:
    value = text(path)
    found = [token for token in tokens if token in value]
    if found:
        raise SystemExit(f"{path} violates S5.5 authority/claim firewalls: {found}")


def main() -> None:
    semantic = "src/aasm/core_conflict.py"
    runtime = "src/aasm/core_conflict_runtime.py"
    tests = "tests/test_core_conflict.py"
    require(
        semantic,
        'CORE_CONFLICT_CONTRACT_ID = "aasm.core-conflict.v1"',
        '"RAW", "NORMALIZED", "REDUCED", "RECHECKED"',
        '"IRREDUCIBLE"',
        '"MINIMUM_CARDINALITY"',
        '"MINIMUM_WEIGHT"',
        '"BUDGET_LIMITED_PARTIAL"',
        "class CoreMember",
        "class CoreProvenance",
        "class ConflictCore",
        "class CoreRecheck",
        "external_reference_id",
        "problem_semantic_fingerprint",
    )
    require(
        runtime,
        'CORE_CONFLICT_RUNTIME_CONTRACT_ID = "aasm.core-conflict.runtime.v1"',
        '"core_claim_self_upgrade": "NONE"',
        '"knowledge_reuse": "S5.4_APPLICABILITY_REQUIRED"',
        '"effect_dispatch": "NONE"',
        '"problem_mutation": "NONE"',
        "capture_raw_core",
        "normalize_core",
        "reduce_core",
        "certify_irreducible",
        "certify_minimum_cardinality",
        "certify_minimum_weight",
        "No ordering is used to infer stronger guarantees",
    )
    forbid(
        runtime,
        "execute_effect(",
        "commit_problem_revision_transition(",
        "class CoreAuthority",
        "class ConflictAuthority",
        "minimum = irreducible",
    )
    require(
        tests,
        "test_smaller_core_is_not_automatically_irreducible_or_minimum",
        "test_budget_exhaustion_is_partial_not_minimum",
        "test_irreducible_requires_independent_full_and_every_single_removal_recheck",
        "test_irreducible_does_not_imply_minimum_cardinality",
        "test_minimum_cardinality_requires_same_semantic_fingerprint_certificate",
        "test_minimum_weight_is_independent_claim_with_explicit_objective_and_certificate",
        "test_cross_revision_or_member_identity_drift_fails_closed",
    )
    schema = json.loads((ROOT / "schemas/core-conflict.schema.json").read_text(encoding="utf-8"))
    expected = {"CORE_MEMBER", "CORE_PROVENANCE", "CONFLICT_CORE", "CORE_RECHECK"}
    actual = set(schema["properties"]["record_type"]["enum"])
    if actual != expected:
        raise SystemExit(f"unexpected S5.5 schema record types: {sorted(actual)}")
    print("S5.5 integrated core/conflict contracts: OK")


if __name__ == "__main__":
    main()
