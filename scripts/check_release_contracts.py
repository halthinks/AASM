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


def require(path, tokens):
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    missing = [token for token in tokens if token not in text]
    if missing:
        _fail(f"missing required source-contract tokens: {missing}", path=path)


def forbid(path, tokens):
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    present = [token for token in tokens if token in text]
    if present:
        _fail(f"forbidden stale/release-overclaim text: {present}", path=path)


def run_script(root: Path, name: str) -> None:
    env = os.environ.copy()
    src = str(root / "src")
    env["PYTHONPATH"] = src if not env.get("PYTHONPATH") else src + os.pathsep + env["PYTHONPATH"]
    completed = subprocess.run([sys.executable, str(root / "scripts" / name)], cwd=root, env=env)
    if completed.returncode != 0:
        _fail(f"nested source-contract checker failed: {name}", path=root / "scripts" / name)


def main():
    root = Path(__file__).resolve().parents[1]
    with (root / "pyproject.toml").open("rb") as handle:
        project = tomllib.load(handle)["project"]

    if str(project["version"]) != "0.56.1":
        _fail(f"unexpected development package target: {project['version']}", path=root / "pyproject.toml")
    if project.get("license") != "Apache-2.0":
        _fail("active license must remain Apache-2.0", path=root / "pyproject.toml")
    if set(project.get("license-files", [])) != {"LICENSE", "NOTICE", "LICENSE_POLICY.md"}:
        _fail("license file set drift", path=root / "pyproject.toml")

    require(root / "src/aasm/__init__.py", ["public_v56"])
    require(root / "src/aasm/public_v56.py", [
        '__version__ = "0.56.1"',
        '"contract_version": "0.32.5"',
        'PUBLIC_RELEASE_STABILITY = "ACTIVE_DEVELOPMENT"',
        "SOLVER_OUTCOME_V2_CONTRACT_ID",
        "SOLVER_RUNTIME_PROVENANCE_CONTRACT_ID",
        "SOLVER_EXECUTION_PROFILE_CONTRACT_ID",
        "SolverRuntimeProvenance",
        "solver_provenance_runtime_contract",
        '"interrupted_provenance_v2": "DORMANT_NON_AUTHORITATIVE_NOT_EXPOSED"',
        "FACT_AUTHORITY_CONTRACT_ID",
        "STATE_CLAIM_CONTRACT_ID",
        "FactAuthority",
        "StateClaim",
        "state_authority_runtime_contract",
        "MACHINE_BINDING_CONTRACT_ID",
        "MACHINE_STATE_OBSERVATION_CONTRACT_ID",
        "MachineBinding",
        "MachineStateObservation",
        "external_machine_runtime_contract",
        "MACHINE_TRANSITION_CONTRACT_ID",
        "MachineTransitionIntent",
        "machine_transition_runtime_contract",
        "MACHINE_POSTCONDITION_VERIFICATION_CONTRACT_ID",
        "MachinePostconditionVerification",
        "machine_postcondition_runtime_contract",
    ])
    require(root / "src/aasm/runtime_v56_foundation.py", [
        "MachinePostconditionExecutionCorrelationMixin",
        "MachinePostconditionRuntimeMixin",
        "MachineTransitionRuntimeMixin",
        "ExternalMachineRuntimeMixin",
        "StateAuthorityRuntimeMixin",
        "SolverProvenanceRuntimeMixin",
        "SolverOutcomeV2RuntimeMixin",
        "V55FoundationEngine",
    ])
    require(root / "src/aasm/solver_outcome_v2.py", [
        'SOLVER_OUTCOME_V2_CONTRACT_ID = "aasm.solver.outcome.v2"',
        '"authoritative_detailed_status": "normalized_status"',
        '"legacy_projection": "V2_TO_V1_ONE_WAY_EXPLICITLY_LOSSY_WHERE_REQUIRED"',
        '"truth_authority": "NONE"',
    ])
    require(root / "src/aasm/provider_status_v2.py", [
        'PROVIDER_STATUS_MAP_CONTRACT_ID = "aasm.solver.provider-status-map.v1"',
        '"fuzzy_matching": "FORBIDDEN"',
        '"substring_inference": "FORBIDDEN"',
    ])
    require(root / "src/aasm/solver_provenance.py", [
        'SOLVER_EXECUTION_PROFILE_CONTRACT_ID = "aasm.solver.execution-profile.v1"',
        'SOLVER_RUNTIME_PROVENANCE_CONTRACT_ID = "aasm.solver.runtime-provenance.v1"',
        'SOLVER_PROFILE_EVALUATION_CONTRACT_ID = "aasm.solver.profile-evaluation.v1"',
        '"effective_options": "ADAPTER_OBSERVED_ACTUAL_CONFIGURATION_REQUIRED"',
        '"worker_thread_counts": "FIRST_CLASS_EXPLICIT_OR_UNKNOWN"',
        '"reproducibility": "NOT_CLAIMED_BY_PROVENANCE_ALONE"',
        '"truth_authority": "NONE"',
        '"policy_authority": "NONE"',
    ])
    require(root / "src/aasm/_runtime_v56_provenance.py", [
        'SOLVER_PROVENANCE_RUNTIME_CONTRACT_ID = "aasm.solver.runtime-provenance.runtime.v1"',
        '"effective_configuration_source": "AASM_PROVIDER_ADAPTER_OBSERVATION_NOT_CALLER_ASSERTION"',
        '"parallel_provenance_table": "NONE"',
        '"provenance_grants_reproducibility": False',
        "record_convex_solver_runtime_provenance",
        "evaluate_solver_runtime_profile",
    ])
    require(root / "src/aasm/solver_execution_observation.py", [
        "aasm.optimization.pysat-cadical",
        "aasm.optimization.ortools-cp-sat",
        "aasm.optimization.highs",
        "aasm.optimization.cvxpy",
        "UNAVAILABLE_FROM_CURRENT_ADAPTER",
        "BACKEND_SPECIFIC_NOT_EXPOSED_BY_CURRENT_CVXPY_ADAPTER",
    ])
    require(root / "src/aasm/state_authority.py", [
        'FACT_AUTHORITY_CONTRACT_ID = "aasm.fact.authority.v1"',
        'STATE_CLAIM_CONTRACT_ID = "aasm.state.claim.v1"',
        '"aggregation_grants_authority": False',
        '"fact_authority_grants_effect_authority": False',
        '"machine_state_mutation": "NONE_BY_THIS_CONTRACT"',
    ])
    require(root / "src/aasm/state_authority_runtime.py", [
        'STATE_AUTHORITY_RUNTIME_CONTRACT_ID = "aasm.state.authority.runtime.v1"',
        '"parallel_truth_table": "NONE"',
        '"machine_state_mutation": "NONE"',
        '"effect_authority": "NONE"',
        "authorize_scoped_request",
        "add_evidence_guarded",
    ])
    require(root / "src/aasm/external_machine.py", [
        'MACHINE_BINDING_CONTRACT_ID = "aasm.machine.binding.v1"',
        'MACHINE_STATE_OBSERVATION_CONTRACT_ID = "aasm.machine.state-observation.v1"',
        '"binding_grants_fact_authority": False',
        '"binding_grants_effect_authority": False',
        '"external_state_table": "NONE"',
        '"postcondition_achievement_claim": "NOT_YET_CLAIMED_PR2C"',
    ])
    require(root / "src/aasm/external_machine_runtime.py", [
        'EXTERNAL_MACHINE_RUNTIME_CONTRACT_ID = "aasm.machine.external.runtime.v1"',
        '"state_observation_source": "EXISTING_PR1_DURABLE_OBSERVED_STATE_CLAIM"',
        '"effect_dispatch": "NONE"',
        '"executor_invocation": "NONE"',
        '"machine_state_mutation": "NONE"',
        "capability_report",
        "state_claim_report",
        "authorize_scoped_request",
    ])
    require(root / "src/aasm/external_machine_transition.py", [
        'MACHINE_TRANSITION_CONTRACT_ID = "aasm.machine.transition.v1"',
        '"expected_prestate": "EXACT_DURABLE_AUTHORITATIVE_STATE_CLAIMS_REQUIRED"',
        '"target_state": "EXACT_DURABLE_DESIRED_STATE_CLAIMS_REQUIRED"',
        '"effect_proposal": "EXISTING_AASM_PROPOSE_EFFECT_AND_EFFECT_INTENT_ONLY"',
        '"parallel_dispatcher": "NONE"',
        '"command_success_is_achievement": False',
        '"postcondition_verification": "NOT_IMPLEMENTED_PR2B_RESERVED_FOR_PR2C"',
    ])
    require(root / "src/aasm/external_machine_transition_runtime.py", [
        'MACHINE_TRANSITION_RUNTIME_CONTRACT_ID = "aasm.machine.transition.runtime.v1"',
        '"effect_proposal_path": "EXISTING_AASM_PROPOSE_EFFECT_ONLY"',
        '"effect_dispatch": "NOT_PERFORMED_USE_EXISTING_EXECUTE_EFFECT"',
        '"effect_ownership": "NOT_CREATED_BY_THIS_RUNTIME"',
        '"transition_status_store": "NONE_DERIVE_FROM_EXISTING_EFFECT_RECORD"',
        "self.propose_effect(",
        "_authorize_external_machine_action(",
    ])
    require(root / "src/aasm/external_machine_postcondition.py", [
        'MACHINE_POSTCONDITION_VERIFICATION_CONTRACT_ID = "aasm.machine.postcondition-verification.v1"',
        '"effect_status_requirement": "EXISTING_AASM_EFFECT_MUST_BE_SUCCEEDED"',
        '"unknown_effect": "BLOCKED_USE_EXISTING_EFFECT_RECONCILIATION"',
        '"achieved_source": "PR1_DURABLE_AUTHORITATIVE_STATE_CLAIMS_ONLY"',
        '"observation_correlation": "PR2A_MACHINE_STATE_OBSERVATION_CORRELATION_ID_MUST_EQUAL_EXISTING_EFFECT_EXECUTION_ID"',
        '"comparison": "EXACT_CANONICAL_VALUE_EQUALITY_ONLY_NO_TOLERANCE_IN_THIS_FOUNDATION"',
        '"effect_success_is_achievement": False',
        '"verification_mints_fact_authority": False',
        '"verification_mints_state_claim": False',
        '"verification_mutates_effect_outcome": False',
        '"parallel_truth_table": "NONE"',
        '"parallel_effect_lifecycle": "NONE"',
        '"freshness_semantics": "NOT_YET_CLAIMED_PR4"',
        '"calibration_semantics": "NOT_YET_CLAIMED_PR4"',
    ])
    require(root / "src/aasm/external_machine_postcondition_runtime.py", [
        'MACHINE_POSTCONDITION_RUNTIME_CONTRACT_ID = "aasm.machine.postcondition-verification.runtime.v1"',
        '"effect_source": "EXISTING_AASM_EFFECT_RECORD_ONLY"',
        '"transition_source": "EXISTING_PR2B_MACHINE_TRANSITION_ONLY"',
        '"achieved_source": "EXISTING_PR1_AUTHORITATIVE_STATE_CLAIMS_ONLY"',
        '"observation_source": "EXISTING_PR2A_MACHINE_STATE_OBSERVATIONS_ONLY"',
        '"effect_status_mutation": "NONE"',
        '"state_claim_creation": "NONE"',
        '"fact_authority_creation": "NONE"',
        '"machine_state_mutation": "NONE"',
        '"parallel_effect_lifecycle": "NONE"',
        "self.store.load_effect(",
        "machine_transition_report",
        "machine_state_observation_report",
        "state_claim_report",
    ])
    require(root / "src/aasm/external_machine_postcondition_execution_correlation.py", [
        "effect.status == EffectStatus.UNKNOWN.value",
        "effect.status != EffectStatus.SUCCEEDED.value",
        "effect.execution_id",
        "observation.correlation_id != execution_id",
    ])

    for schema in (
        "solver-outcome-v2.schema.json",
        "provider-status-map.schema.json",
        "solver-execution-profile.schema.json",
        "solver-runtime-provenance.schema.json",
        "solver-profile-evaluation.schema.json",
        "fact-authority.schema.json",
        "state-claim.schema.json",
        "machine-binding.schema.json",
        "machine-state-observation.schema.json",
        "machine-transition.schema.json",
        "machine-postcondition-verification.schema.json",
    ):
        require(root / "schemas" / schema, ['"$schema"', "2020-12"])

    require(root / "src/aasm/public_v55.py", ['__version__ = "0.55.0"', '"contract_version": "0.31.0"'])
    require(root / "src/aasm/public_v54.py", ['__version__ = "0.54.0"', '"contract_version": "0.30.0"'])
    require(root / "src/aasm/semantic_evolution.py", [
        'EXTERNAL_REFERENCE_CONTRACT_ID = "aasm.external.reference.v1"',
        'PROBLEM_REVISION_CONTRACT_ID = "aasm.problem.revision.v1"',
        'PROBLEM_DELTA_CONTRACT_ID = "aasm.problem.delta.v1"',
    ])
    require(root / "src/aasm/solver_formulation.py", ['SOLVER_FORMULATION_CONTRACT_ID = "aasm.solver.formulation.v1"'])
    require(root / "src/aasm/solver_learning.py", ['"truth_authority": "NONE"', '"policy_authority": "NONE"'])

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
    ):
        run_script(root, script)

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
        "CVXPY",
        "published release:       0.56.0",
    ])
    forbid(root / "docs/RELEASE_0.56.1.md", ["targeted for v0.56.2", "Next cumulative release: **v0.56.2"])

    require(root / "docs/VERSIONING.md", [
        "Package SemVer identifies deliberately published AASM distributions",
        "Git SHA",
        "New implementation modules must use stable semantic names",
    ])
    require(root / ".github/workflows/v56.yml", [
        "AASM v0.56 Development Qualification",
        "0.56.1",
        "check_v561_provenance.py",
        "tests/test_v561_solver_provenance_real.py",
        "check_machine_postcondition_contracts.py",
        "tests/test_machine_postcondition.py",
        "context='aasm/v56'",
    ])
    require(root / ".github/workflows/v561.yml", [
        "AASM 0.56.1 Execution Provenance Qualification",
        "context='aasm/v56-provenance'",
    ])
    require(root / ".github/workflows/state-authority.yml", [
        "State Authority",
        "check_state_authority_contracts.py",
        "tests/test_state_authority.py",
        "context='aasm/state-authority'",
    ])
    require(root / ".github/workflows/external-machine.yml", [
        "External Machine Binding",
        "check_external_machine_contracts.py",
        "tests/test_external_machine.py",
        "context='aasm/external-machine'",
    ])
    require(root / ".github/workflows/machine-transition.yml", [
        "Machine Transition Proposal",
        "check_machine_transition_contracts.py",
        "tests/test_machine_transition.py",
        "context='aasm/machine-transition'",
    ])
    require(root / ".github/workflows/machine-postcondition.yml", [
        "Machine Postcondition Verification",
        "check_machine_postcondition_contracts.py",
        "tests/test_machine_postcondition.py",
        "context='aasm/machine-postcondition'",
    ])
    require(root / ".github/workflows/release.yml", [
        "workflow_dispatch:",
        "confirm_release:",
        "aasm/v56-provenance",
        "aasm/state-authority",
        "aasm/external-machine",
        "aasm/machine-transition",
        "aasm/machine-postcondition",
        "check_version_policy.py",
        "release_manifest.py --check-file-list",
        "verify-github-release",
    ])
    forbid(root / ".github/workflows/release.yml", ["workflow_run:"])

    print("0.56.1 development-target contracts + adoption 0.32.5 + v0.56.0 published identity: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
