from __future__ import annotations

from pathlib import Path
import os
import subprocess
import sys
import tomllib


def _fail(message: str, *, path: Path | None = None) -> None:
    location = f" file={path}" if path is not None else ""
    safe = message.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    print(f"::error{location}::{safe}", file=sys.stderr)
    raise SystemExit(message)


def require(path: Path | str, tokens) -> None:
    path = Path(path)
    if not path.exists():
        _fail("required file is missing", path=path)
    value = path.read_text(encoding="utf-8")
    missing = [token for token in tokens if token not in value]
    if missing:
        _fail(f"missing required source-contract tokens: {missing}", path=path)


def forbid(path: Path | str, tokens) -> None:
    path = Path(path)
    value = path.read_text(encoding="utf-8")
    present = [token for token in tokens if token in value]
    if present:
        _fail(f"forbidden stale/release-overclaim text: {present}", path=path)


def run_script(root: Path, name: str) -> None:
    env = os.environ.copy()
    src = str(root / "src")
    env["PYTHONPATH"] = src if not env.get("PYTHONPATH") else src + os.pathsep + env["PYTHONPATH"]
    completed = subprocess.run([sys.executable, str(root / "scripts" / name)], cwd=root, env=env)
    if completed.returncode != 0:
        _fail(f"nested source-contract checker failed: {name}", path=root / "scripts" / name)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    with (root / "pyproject.toml").open("rb") as handle:
        project = tomllib.load(handle)["project"]

    if str(project["version"]) != "0.56.1":
        _fail(f"unexpected development package target: {project['version']}", path=root / "pyproject.toml")
    if project.get("license") != "Apache-2.0":
        _fail("active license must remain Apache-2.0", path=root / "pyproject.toml")
    if set(project.get("license-files", [])) != {"LICENSE", "NOTICE", "LICENSE_POLICY.md"}:
        _fail("license file set drift", path=root / "pyproject.toml")

    # Additive adoption lineage. Package SemVer and adoption versions remain independent.
    require(root / "src/aasm/__init__.py", [
        "public_v56",
        "public_active",
        "public_active_entity_evolution",
        "public_active_engineering_quantity",
        "public_active_engineering_rule",
        "public_active_semantic_projection",
        "public_active_uncertainty_scenario_trace",
        "from .public_active_uncertainty_scenario_trace import *",
    ])
    require(root / "src/aasm/public_v56.py", [
        '__version__ = "0.56.1"',
        '"contract_version": "0.32.6"',
        'PUBLIC_RELEASE_STABILITY = "ACTIVE_DEVELOPMENT"',
    ])
    require(root / "src/aasm/public_active.py", ['"contract_version": "0.32.14"'])
    require(root / "src/aasm/public_active_entity_evolution.py", ['"contract_version": "0.32.15"'])
    require(root / "src/aasm/public_active_engineering_quantity.py", ['"contract_version": "0.32.16"'])
    require(root / "src/aasm/public_active_engineering_rule.py", ['"contract_version": "0.32.17"'])
    require(root / "src/aasm/public_active_semantic_projection.py", [
        'PUBLIC_ADOPTION_CONTRACT_VERSION = "0.32.18"',
        'PARENT_PUBLIC_ADOPTION_CONTRACT_VERSION = "0.32.17"',
        'SEMANTIC_PROJECTION_PUBLIC_ADMISSION = "QUALIFIED_SEMANTIC_IR_ONLY"',
        '"runtime_admission"] = "PRE_ADMISSION_ONLY"',
        '"engine_state_integration"] = "NONE_SEMANTIC_IR_ONLY"',
    ])
    require(root / "src/aasm/public_active_uncertainty_scenario_trace.py", [
        'PUBLIC_ADOPTION_CONTRACT_VERSION = "0.32.19"',
        'PARENT_PUBLIC_ADOPTION_CONTRACT_VERSION = "0.32.18"',
        'UNCERTAINTY_SCENARIO_TRACE_PUBLIC_ADMISSION = "QUALIFIED_SEMANTIC_IR_ONLY"',
        'PUBLIC_API_CONTRACT["uncertainty"]',
        'PUBLIC_API_CONTRACT["scenario"]',
        'PUBLIC_API_CONTRACT["trace_property"]',
        '"active_root_status"] = "ACTIVE_QUALIFIED_PUBLIC_ROOT"',
        '"runtime_admission"] = "PRE_ADMISSION_ONLY"',
        '"engine_state_integration"] = "NONE_SEMANTIC_IR_ONLY"',
        'AASMEngine = _base.AASMEngine',
    ])

    # S4.4 foundation is semantic IR/evaluation only and must reuse existing substrates.
    require(root / "src/aasm/uncertainty_scenario_trace.py", [
        'UNCERTAINTY_CONTRACT_ID = "aasm.uncertainty.v1"',
        'SCENARIO_CONTRACT_ID = "aasm.scenario.v1"',
        'TRACE_PROPERTY_CONTRACT_ID = "aasm.trace-property.v1"',
        'TRACE_PROPERTY_ASSESSMENT_CONTRACT_ID = "aasm.trace-property.assessment.v1"',
        'TRACE_INVARIANT_CLASSIFICATION = "DYNAMIC_KERNEL"',
        '"DISTINCT_FROM_AASM_NUMERIC_TOLERANCE_V1_ACCEPTANCE_POLICY"',
        '"DISTINCT_FROM_SEMANTIC_RESULT_CONFIDENCE_NO_INFERENCE_OR_COERCION"',
        '"EXISTING_AASM_TRACE_V1_AUTHORITATIVE_DURABLE_EVENT_HISTORY"',
        '"EXISTING_PROJECT_TRACE_FUNCTION_UNCHANGED"',
        '"scenario_activation": "NONE_FOUNDATION_ONLY"',
        '"parallel_uncertainty_registry": "NONE"',
        '"parallel_scenario_registry": "NONE"',
        '"parallel_trace_store": "NONE"',
        '"parallel_property_registry": "NONE"',
        '"runtime_admission": "PRE_ADMISSION_ONLY"',
        '"public_admission": "PRE_ADMISSION_ONLY"',
    ])

    # Pre-admission engineering IR is not runtime engine state.
    forbid(root / "src/aasm/runtime_v56_foundation.py", [
        "EngineeringRule",
        "from .rule",
        "SemanticProjectionDefinition",
        "from .semantic_projection",
        "UncertaintySpec",
        "ScenarioBinding",
        "TraceProperty",
        "from .uncertainty_scenario_trace",
    ])

    # Detailed contracts remain delegated to the independently maintained source checkers.
    for script in (
        "check_v52_contracts.py",
        "check_v53_contracts.py",
        "check_v53_solver_learning_contracts.py",
        "check_v54_contracts.py",
        "check_v55_discrete_ir.py",
        "check_v55_scheduling_ir.py",
        "check_v55_continuous_ir.py",
        "check_v55_decision_vector.py",
        "check_v55_semantic_archive.py",
        "check_v56_solver_outcome.py",
        "check_v561_provenance.py",
        "check_state_authority_contracts.py",
        "check_external_machine_contracts.py",
        "check_machine_transition_contracts.py",
        "check_machine_postcondition_contracts.py",
        "check_physical_authority_contracts.py",
        "check_effect_capability_contracts.py",
        "check_physical_control_fencing_contracts.py",
        "check_physical_effect_integration_contracts.py",
        "check_state_conflict_contracts.py",
        "check_causal_freshness_contracts.py",
        "check_identity_calibration_trust_contracts.py",
        "check_execution_environment_contracts.py",
        "check_observation_processing_contracts.py",
        "check_artifact_lineage_contracts.py",
        "check_entity_evolution_contracts.py",
        "check_quantity_contracts.py",
        "check_quantity_public.py",
        "check_rule_contracts.py",
        "check_rule_public.py",
        "check_semantic_projection_contracts.py",
        "check_semantic_projection_public.py",
        "check_uncertainty_scenario_trace_contracts.py",
        "check_uncertainty_scenario_trace_public.py",
    ):
        run_script(root, script)

    for schema in (
        "fact-authority.schema.json",
        "state-claim.schema.json",
        "machine-binding.schema.json",
        "machine-state-observation.schema.json",
        "machine-transition.schema.json",
        "machine-postcondition-verification.schema.json",
        "authority-domain.schema.json",
        "authority-lease.schema.json",
        "effect-capability.schema.json",
        "effect-capability-use.schema.json",
        "authority-preemption.schema.json",
        "physical-effect-authority-binding.schema.json",
        "state-conflict.schema.json",
        "causal-event.schema.json",
        "causal-relation.schema.json",
        "observation-freshness.schema.json",
        "physical-identity.schema.json",
        "calibration.schema.json",
        "calibration-revocation.schema.json",
        "source-trust.schema.json",
        "source-trust-revocation.schema.json",
        "execution-environment.schema.json",
        "execution-environment-binding.schema.json",
        "observation-lifecycle.schema.json",
        "observation-fusion.schema.json",
        "observation-disposition.schema.json",
        "artifact-revision.schema.json",
        "entity-evolution.schema.json",
        "quantity.schema.json",
        "rule.schema.json",
        "semantic-projection.schema.json",
        "uncertainty.schema.json",
        "scenario.schema.json",
        "trace-property.schema.json",
    ):
        require(root / "schemas" / schema, ['"$schema"', "2020-12"])

    # Development/release truth remains explicit.
    require(root / "README.md", [
        "Current release — v0.56.0",
        "Next release / cumulative release:** v0.56.1",
        "package / public surface: 0.56.0",
    ])
    require(root / "docs/CURRENT_RELEASE.md", [
        "AASM v0.56.0",
        "Latest immutable published release",
        "Current development target on `main`:** 0.56.1",
        "latest published package: 0.56.0",
    ])
    require(root / "docs/RELEASE_0.56.1.md", [
        "Development Candidate",
        "UNRELEASED DEVELOPMENT TARGET",
        "published release: v0.56.0",
    ])
    forbid(root / "docs/RELEASE_0.56.1.md", ["targeted for v0.56.2", "Next cumulative release: **v0.56.2"])
    require(root / "docs/VERSIONING.md", [
        "Package SemVer identifies deliberately published AASM distributions",
        "Git SHA",
        "New implementation modules must use stable semantic names",
    ])

    # Cumulative and dedicated qualification must exercise the exact active surface.
    require(root / ".github/workflows/v56.yml", [
        "AASM v0.56 Development Qualification",
        "check_artifact_lineage_contracts.py",
        "check_entity_evolution_contracts.py",
        "check_quantity_contracts.py",
        "check_quantity_public.py",
        "check_rule_contracts.py",
        "check_rule_public.py",
        "check_semantic_projection_contracts.py",
        "check_semantic_projection_public.py",
        "check_uncertainty_scenario_trace_contracts.py",
        "check_uncertainty_scenario_trace_public.py",
        "tests/test_uncertainty_scenario_trace_foundation.py",
        "tests/test_uncertainty_scenario_trace_public.py",
        "0.32.19",
        "context='aasm/v56'",
    ])
    require(root / ".github/workflows/engineering-s4.yml", [
        "check_semantic_projection_public.py",
        "check_uncertainty_scenario_trace_contracts.py",
        "check_uncertainty_scenario_trace_public.py",
        "tests/test_uncertainty_scenario_trace_public.py",
        "context='aasm/engineering-s4'",
    ])
    require(root / ".github/workflows/engineering-uncertainty-scenario-trace.yml", [
        "check_uncertainty_scenario_trace_contracts.py",
        "tests/test_uncertainty_scenario_trace_foundation.py",
        "context='aasm/engineering-uncertainty-scenario-trace'",
    ])
    require(root / ".github/workflows/engineering-uncertainty-scenario-trace-public.yml", [
        "check_uncertainty_scenario_trace_contracts.py",
        "check_uncertainty_scenario_trace_public.py",
        "tests/test_uncertainty_scenario_trace_public.py",
        "context='aasm/engineering-uncertainty-scenario-trace-public'",
    ])

    release_contexts = (
        "aasm/v56-provenance",
        "aasm/state-authority",
        "aasm/external-machine",
        "aasm/machine-transition",
        "aasm/machine-postcondition",
        "aasm/physical-authority",
        "aasm/effect-capability",
        "aasm/physical-control-fencing",
        "aasm/physical-preemption-recovery",
        "aasm/physical-effect-integration",
        "aasm/physical-evidence",
        "aasm/identity-calibration-trust",
        "aasm/execution-environment",
        "aasm/observation-epistemics",
        "aasm/artifact-lineage",
        "aasm/entity-evolution",
        "aasm/engineering-quantity",
        "aasm/engineering-rule",
        "aasm/engineering-semantic-projection",
        "aasm/engineering-semantic-projection-public",
        "aasm/engineering-uncertainty-scenario-trace",
        "aasm/engineering-uncertainty-scenario-trace-public",
        "aasm/engineering-s4",
    )
    require(root / ".github/workflows/release.yml", [
        "workflow_dispatch:",
        "confirm_release:",
        *release_contexts,
        "check_version_policy.py",
        "release_manifest.py --check-file-list",
        "verify-github-release",
    ])
    forbid(root / ".github/workflows/release.yml", ["workflow_run:"])

    # Execute the active public contract from source, not from textual inference.
    sys.path.insert(0, str(root / "src"))
    import aasm
    from aasm import public_v56

    report = aasm.validate_public_api_contract()
    if not report.get("valid"):
        _fail(f"active public contract invalid: {report}")
    contract = aasm.public_api_contract()
    if aasm.__version__ != "0.56.1" or contract.get("runtime_version") != "0.56.1":
        _fail("active runtime version drift")
    if contract.get("contract_version") != "0.32.19" or contract.get("parent_contract_version") != "0.32.18":
        _fail("active public adoption lineage drift")
    if aasm.AASMEngine is not public_v56.AASMEngine:
        _fail("semantic public overlays forked the active engine")

    for key in (
        "physical_effect_integration",
        "state_conflict",
        "event_causality",
        "observation_freshness",
        "physical_identity",
        "calibration",
        "source_trust",
        "execution_environment",
        "observation_processing",
        "artifact_lineage",
        "entity_evolution",
        "engineering_quantity",
        "engineering_rule",
        "semantic_projection",
        "uncertainty",
        "scenario",
        "trace_property",
    ):
        if key not in contract:
            _fail(f"active public contract missing cumulative surface: {key}")

    quantity = contract["engineering_quantity"]
    rule = contract["engineering_rule"]
    projection = contract["semantic_projection"]
    uncertainty = contract["uncertainty"]
    scenario = contract["scenario"]
    trace_property = contract["trace_property"]
    if quantity.get("contract_id") != "aasm.quantity.v1" or quantity.get("runtime_admission") != "PRE_ADMISSION_ONLY":
        _fail("Quantity public/runtime boundary drift")
    if rule.get("contract_id") != "aasm.rule.v1" or rule.get("runtime_admission") != "PRE_ADMISSION_ONLY":
        _fail("Rule public/runtime boundary drift")
    if projection.get("contract_id") != "aasm.semantic.projection.v1" or projection.get("runtime_admission") != "PRE_ADMISSION_ONLY":
        _fail("Projection public/runtime boundary drift")
    if uncertainty.get("contract_id") != "aasm.uncertainty.v1" or uncertainty.get("runtime_admission") != "PRE_ADMISSION_ONLY":
        _fail("Uncertainty public/runtime boundary drift")
    if scenario.get("contract_id") != "aasm.scenario.v1" or scenario.get("runtime_admission") != "PRE_ADMISSION_ONLY":
        _fail("Scenario public/runtime boundary drift")
    if trace_property.get("contract_id") != "aasm.trace-property.v1" or trace_property.get("runtime_admission") != "PRE_ADMISSION_ONLY":
        _fail("TraceProperty public/runtime boundary drift")

    for name, value in (("projection", projection), ("uncertainty", uncertainty), ("scenario", scenario), ("trace_property", trace_property)):
        ceiling = value.get("public_claim_ceiling") or {}
        if any(item != "NONE" for item in ceiling.values()):
            _fail(f"{name} public claim ceiling drift")
    if uncertainty.get("parallel_uncertainty_registry") != "NONE" or uncertainty.get("current_uncertainty_pointer") != "NONE":
        _fail("uncertainty parallel-plane drift")
    if scenario.get("parallel_scenario_registry") != "NONE" or scenario.get("hidden_current_scenario") != "NONE" or scenario.get("scenario_activation") != "NONE_FOUNDATION_ONLY":
        _fail("scenario parallel-plane/activation drift")
    if trace_property.get("parallel_trace_store") != "NONE" or trace_property.get("parallel_property_registry") != "NONE" or trace_property.get("static_constraint_lowering") != "NONE":
        _fail("trace-property parallel-plane/lowering drift")
    if trace_property.get("trace_projection") != "EXISTING_PROJECT_TRACE_FUNCTION_UNCHANGED" or trace_property.get("invariant_classification") != "DYNAMIC_KERNEL":
        _fail("trace-property substrate/classification drift")

    semantic_prefixes = (
        "rule_",
        "semantic_projection_",
        "semantic_equivalence_",
        "uncertainty_",
        "scenario_",
        "trace_property_",
    )
    if any(name.startswith(semantic_prefixes) for name in aasm.SUPPORTED_ENGINE_METHODS):
        _fail("pre-admission semantic IR leaked into engine method surface")

    print("0.56.1 development target + active adoption 0.32.19 + PR-3 + S3 + S4 through Uncertainty/Scenario/Trace-Property source/release contracts: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
