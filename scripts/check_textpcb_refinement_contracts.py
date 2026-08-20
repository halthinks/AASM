from __future__ import annotations

import hashlib
import json
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "src" / "aasm" / "textpcb_refinement.py"
REFINEMENT_RUNTIME = ROOT / "src" / "aasm" / "refinement_runtime.py"
FIXTURE = ROOT / "fixtures" / "textpcb" / "s5-refinement-qualification-fixtures.json"
S4_FIXTURE = ROOT / "fixtures" / "textpcb" / "s4-safety-governance-fixtures.json"
SCHEMA = ROOT / "schemas" / "textpcb-refinement-qualification.schema.json"
TEST = ROOT / "tests" / "test_textpcb_refinement.py"
SAFETY_WORKFLOW = ROOT / ".github" / "workflows" / "safety-governance.yml"

REQUIRED_DOMAINS = {
    "DRC_ERC",
    "SPICE",
    "EM",
    "THERMAL_PDN",
    "MECHANICAL_MANUFACTURING",
    "EXTERNAL_MEASUREMENT",
    "ARTIFACT_TOOL_FEEDBACK",
}
REQUIRED_CASES = {
    "drc-erc-governed-proposal",
    "spice-model-correction",
    "em-bound-tightening",
    "thermal-pdn-escalation",
    "mechanical-manufacturing-domain-restriction",
    "external-measurement-required-observation",
    "artifact-tool-feedback",
    "stale-revision-fails-closed",
    "producer-cannot-self-apply",
    "safety-floor-survives-refinement",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def main() -> None:
    source = MODULE.read_text(encoding="utf-8")
    runtime = REFINEMENT_RUNTIME.read_text(encoding="utf-8")
    tests = TEST.read_text(encoding="utf-8")
    safety_workflow = SAFETY_WORKFLOW.read_text(encoding="utf-8")
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    s4 = json.loads(S4_FIXTURE.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))

    Draft202012Validator.check_schema(schema)
    errors = sorted(Draft202012Validator(schema).iter_errors(fixture), key=lambda error: list(error.path))
    require(not errors, f"S5.6 fixture schema validation failed: {[error.message for error in errors]}")

    for token in (
        'TEXTPCB_REFINEMENT_QUALIFICATION_CONTRACT_ID = "aasm.textpcb.refinement-qualification.v1"',
        'TEXTPCB_REFINEMENT_GATE = "aasm/textpcb-refinement"',
        'TEXTPCB_REQUIRED_REFINEMENT_GATE = "aasm/refinement"',
        'TEXTPCB_REQUIRED_SAFETY_GATE = "aasm/safety-governance"',
        "class TextPCBEvaluatorResult",
        "RefinementProposal",
        "refinement_contract",
        '"evaluator_direct_problem_mutation": "FORBIDDEN"',
        '"evaluator_direct_artifact_acceptance": "FORBIDDEN"',
        '"runtime_admission": "QUALIFICATION_ONLY_NO_RUNTIME_SURFACE"',
    ):
        require(token in source, f"S5.6 TextPCB adapter missing required contract token: {token}")

    for forbidden in (
        "from .semantic_evolution import",
        "commit_problem_revision_transition(",
        "apply_refinement(",
        "authorize_scoped_request(",
        "execute_effect(",
        "class TextPCBRefinementRuntime",
        "class TextPCBRefinementRuntimeMixin",
    ):
        require(forbidden not in source, f"S5.6 TextPCB adapter illegally introduces mutation/authority/runtime behavior: {forbidden}")

    require(fixture["qualification_gate"] == "aasm/textpcb-refinement", "S5.6 qualification gate drift")
    require(fixture["required_refinement_gate"] == "aasm/refinement", "S5.6 must depend on generic refinement gate")
    require(fixture["required_safety_gate"] == "aasm/safety-governance", "S5.6 must depend on aggregate safety gate")
    require(fixture["runtime_admission"] == "QUALIFICATION_ONLY_NO_RUNTIME_SURFACE", "S5.6 may not create runtime admission")
    require(
        fixture["canonical_cycle"] == "DESIGN -> VERIFY -> BUILD/GENERATE -> OPERATE/OBSERVE -> LEARN -> REDESIGN",
        "S5.6 canonical refinement cycle drift",
    )

    supplied_fingerprint = fixture["suite_fingerprint"]
    canonical = dict(fixture)
    canonical.pop("suite_fingerprint")
    computed = hashlib.sha256(json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    require(computed == supplied_fingerprint, "S5.6 fixture suite fingerprint mismatch")

    domains = {case["domain"] for case in fixture["cases"]}
    ids = {case["fixture_id"] for case in fixture["cases"]}
    require(domains == REQUIRED_DOMAINS, f"S5.6 domain coverage mismatch: {sorted(domains)}")
    require(REQUIRED_CASES.issubset(ids), f"S5.6 permanent fixture cases missing: {sorted(REQUIRED_CASES - ids)}")
    require(all(case["forbidden_claims"] for case in fixture["cases"]), "S5.6 every fixture must declare forbidden claims")

    require(
        fixture["required_s4_safety_suite_fingerprint"] == s4["suite_fingerprint"],
        "S5.6 is not pinned to the permanent S4 TextPCB safety corpus",
    )
    require("aasm/safety-governance" in safety_workflow, "aggregate S4 safety workflow no longer publishes required gate")
    require("s4-safety-governance-fixtures.json" in safety_workflow, "aggregate safety workflow no longer runs permanent TextPCB corpus")

    for token in (
        'REFINEMENT_APPLY_CAPABILITY = "problem.refinement.apply"',
        "independent refinement validation cannot be performed by the proposal producer",
        "refinement producer/evaluator cannot directly apply its own delta",
        "commit_problem_revision_transition(",
    ):
        require(token in runtime, f"generic S5.1 runtime no longer guarantees required S5.6 seam: {token}")

    for token in (
        "INDEPENDENT_VALIDATOR_REQUIRED",
        "artifact_acceptance_claim",
        "stale-revision-fails-closed",
        "safety-floor-survives-refinement",
        "TEXTPCB_S4_SAFETY_SUITE_FINGERPRINT",
    ):
        require(token in tests, f"S5.6 adversarial test corpus missing required assertion: {token}")

    print("S5.6 TextPCB refinement qualification contracts: OK")


if __name__ == "__main__":
    main()
