from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)

def text(path: str) -> str:
    target = ROOT / path
    require(target.exists(), f"missing required semantic projection public candidate file: {path}")
    return target.read_text(encoding="utf-8")

def main() -> None:
    candidate = text("src/aasm/public_active_semantic_projection.py")
    parent = text("src/aasm/public_active_engineering_rule.py")
    package_root = text("src/aasm/__init__.py")
    semantic = text("src/aasm/semantic_projection.py")
    tests = text("tests/test_semantic_projection_public_candidate.py")
    for token in (
        'PUBLIC_ADOPTION_CONTRACT_VERSION = "0.32.18"',
        'PARENT_PUBLIC_ADOPTION_CONTRACT_VERSION = "0.32.17"',
        'SEMANTIC_PROJECTION_PUBLIC_ADMISSION = "QUALIFIED_SEMANTIC_IR_ONLY"',
        '"semantic-projection"',
        '"runtime_admission"] = "PRE_ADMISSION_ONLY"',
        '"engine_state_integration"] = "NONE_SEMANTIC_IR_ONLY"',
        '"active_root_status"] = "CANDIDATE_UNTIL_PACKAGE_ROOT_SWITCH"',
        '"truth_authority": "NONE"', '"fact_authority": "NONE"', '"effect_authority": "NONE"',
        '"artifact_acceptance": "NONE"', '"entity_identity_authority": "NONE"', '"proof_authority": "NONE"',
        '"objective_preference": "NONE"', '"reuse_admission": "NONE"', '"runtime_execution": "NONE"',
        'def validate_public_api_contract()',
        'PUBLIC_API_CONTRACT["semantic_projection"] = _semantic',
        '"supported_imports": SUPPORTED_PUBLIC_IMPORTS',
    ):
        require(token in candidate, f"semantic projection public candidate missing token: {token}")
    for token in (
        "SEMANTIC_PROJECTION_CONTRACT_ID", "SEMANTIC_EQUIVALENCE_CONTRACT_ID", "INVARIANT_CONTRACT_ID",
        "InvariantRef", "SemanticSubjectRef", "SemanticProjectionDefinition", "SemanticProjectionResult",
        "SemanticEquivalenceAssessment", "assess_semantic_equivalence", "invariant_contract", "semantic_projection_contract",
    ):
        require(token in candidate, f"candidate public import missing: {token}")
    for token in (
        "class AASMEngine(", "FactAuthority(", "StateClaim(", "authorize_scoped_request(",
        ".authorize_effect(", ".execute_effect(", "dispatch_effect(", "register_projection(",
        "PROJECTION_REGISTRY =", "projection_registry[", "latest_projection", "current_projection_store",
        "PUBLIC_ADOPTION_STABILITY", "PUBLIC_ADOPTION_SUPPORT",
    ):
        require(token not in candidate, f"semantic projection public candidate violates source firewall: {token}")
    require('from . import public_active_engineering_rule as _base' in candidate, "candidate does not inherit qualified Rule public boundary")
    require('for _name in dir(_base):' in candidate, "candidate does not preserve complete qualified Rule public surface")
    require('AASMEngine = _base.AASMEngine' in candidate, "candidate forked the qualified Rule engine")
    require('PUBLIC_RELEASE_STABILITY = _base.PUBLIC_RELEASE_STABILITY' in candidate, "candidate does not preserve release stability vocabulary")
    require('SUPPORTED_ENGINE_METHODS = list(getattr(_base, "SUPPORTED_ENGINE_METHODS", []))' in candidate, "candidate changed engine method set")
    require('"contract_version": "0.32.17"' in parent, "Rule parent public adoption drifted")
    require('from .public_active_engineering_rule import *' in package_root, "active package root is not the qualified 0.32.17 Rule overlay")
    require("public_active_semantic_projection" not in package_root, "candidate activated before qualification")
    require('"public_admission": "PRE_ADMISSION_ONLY"' in semantic, "foundation semantic projection claim ceiling drifted")
    for token in (
        "test_semantic_projection_public_candidate_advances_only_candidate_overlay",
        "test_active_package_root_remains_03217_until_candidate_is_qualified",
        "test_semantic_projection_candidate_exposes_semantic_ir_without_runtime_methods",
        "test_semantic_projection_candidate_contract_preserves_claim_ceiling_and_invariant_classes",
        "test_semantic_projection_candidate_public_types_are_deterministic_and_relative_to_projection",
    ):
        require(token in tests, f"semantic projection public candidate corpus missing test: {token}")
    print("S4 semantic projection/equivalence public candidate contracts: PASS")

if __name__ == "__main__":
    main()
