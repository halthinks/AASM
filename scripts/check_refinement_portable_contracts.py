from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "src" / "aasm" / "refinement_portable.py"
SCHEMA = ROOT / "schemas" / "refinement-portable-boundary.schema.json"
TEST = ROOT / "tests" / "test_refinement_portable.py"
REFINEMENT_RUNTIME = ROOT / "src" / "aasm" / "refinement_runtime.py"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def main() -> None:
    source = MODULE.read_text(encoding="utf-8")
    tests = TEST.read_text(encoding="utf-8")
    runtime = REFINEMENT_RUNTIME.read_text(encoding="utf-8")
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)

    for token in (
        'REFINEMENT_PORTABLE_BOUNDARY_CONTRACT_ID = "aasm.refinement.portable-boundary.v1"',
        'REFINEMENT_PORTABLE_BOUNDARY_GATE = "aasm/refinement"',
        "class PortableRevisionRef",
        "class PortableProblemTransitionRef",
        "class PortableRefinementBoundary",
        "def project_portable_refinement_boundary",
        '"embedded_engines": []',
        '"authority_claim": "NONE"',
        '"s6_relationship": "REFERENCE_ABI_ONLY_MACHINE_IR_AND_PORTABLE_REDUCER_BEGIN_IN_S6"',
    ):
        require(token in source, f"S5.7 portable refinement contract missing required token: {token}")

    for forbidden in (
        "from .solver",
        "from .effects",
        "from .effect_",
        "from .scoped_authority",
        "from .semantic_evolution import",
        "commit_problem_revision_transition(",
        "authorize_scoped_request(",
        "apply_refinement(",
        "execute_effect(",
        "OpenAI",
        "Anthropic",
        "KiCad",
        "ngspice",
    ):
        require(forbidden not in source, f"S5.7 portable boundary embeds forbidden engine/authority behavior: {forbidden}")

    for engine in ("LLM", "SOLVER", "CAD", "SPICE", "EM", "PHYSICS"):
        require(f'"{engine}"' in source, f"S5.7 portable boundary must explicitly exclude {engine}")

    for field in (
        '"revision_refs"',
        '"proposal_ids"',
        '"validation_ids"',
        '"application_ids"',
        '"termination_ids"',
        '"evidence_ids"',
        '"obligation_ids"',
        '"conflict_ids"',
        '"core_ids"',
        '"transition_refs"',
    ):
        require(field in source and field in SCHEMA.read_text(encoding="utf-8"), f"S5.7 portable field missing: {field}")

    require('"additionalProperties": false' in SCHEMA.read_text(encoding="utf-8"), "S5.7 schema must fail closed on unknown payload fields")
    require('"embedded_engines": {"const": []}' in SCHEMA.read_text(encoding="utf-8"), "S5.7 schema must forbid embedded engines")
    require('"authority_claim": {"const": "NONE"}' in SCHEMA.read_text(encoding="utf-8"), "S5.7 schema must forbid transported authority")

    for token in (
        "solver_model",
        "cad_geometry",
        "solver_payload",
        "scope_filter_prevents_cross_scope_refinement_leakage",
        "cannot carry authority",
        "cannot embed execution engines",
        "REFERENCE_ABI_ONLY_MACHINE_IR_AND_PORTABLE_REDUCER_BEGIN_IN_S6",
    ):
        require(token in tests, f"S5.7 adversarial test corpus missing required assertion: {token}")

    for token in (
        "def project_refinement_evidence",
        '"parallel_refinement_store": "NONE"',
        '"parallel_revision_system": "NONE"',
        '"parallel_authority_plane": "NONE"',
    ):
        require(token in runtime, f"S5.7 parent refinement runtime seam drifted: {token}")

    print("S5.7 portable refinement boundary contracts: OK")


if __name__ == "__main__":
    main()
