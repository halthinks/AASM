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
    text = path.read_text(encoding="utf-8")
    missing = [token for token in tokens if token not in text]
    if missing:
        _fail(f"missing required source-contract tokens: {missing}", path=path)


def forbid(path: Path | str, tokens) -> None:
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

    require(root / "src/aasm/__init__.py", ["public_v56", "public_active"])
    require(root / "src/aasm/public_v56.py", [
        '__version__ = "0.56.1"',
        '"contract_version": "0.32.6"',
        'PUBLIC_RELEASE_STABILITY = "ACTIVE_DEVELOPMENT"',
        "physical_authority_runtime_contract",
    ])
    require(root / "src/aasm/public_active.py", [
        '"contract_version": "0.32.10"',
        "EFFECT_CAPABILITY_CONTRACT_ID",
        "PhysicalEffectAuthorityBinding",
        "STATE_CONFLICT_CONTRACT_ID",
        "StateConflict",
        "EVENT_CAUSALITY_CONTRACT_ID",
        "CausalEventIdentity",
        "CausalRelation",
        "OBSERVATION_FRESHNESS_CONTRACT_ID",
        "ObservationFreshnessAssessment",
        "physical_effect_integration_runtime_contract",
        "state_conflict_runtime_contract",
        "event_causality_runtime_contract",
        "observation_freshness_runtime_contract",
        '"physical_effect_integration"',
        '"state_conflict"',
        '"event_causality"',
        '"observation_freshness"',
    ])
    require(root / "src/aasm/runtime_v56_foundation.py", [
        "PhysicalEffectIntegrationBoundaryMixin",
        "PhysicalPreemptionRecoveryGuardMixin",
        "PhysicalControlFencingRuntimeMixin",
        "EffectCapabilityRevocationGuardMixin",
        "EffectCapabilityRuntimeMixin",
        "PhysicalAuthorityRuntimeMixin",
        "MachinePostconditionExecutionCorrelationMixin",
        "ObservationFreshnessRuntimeMixin",
        "EventCausalityRuntimeMixin",
        "StateConflictRuntimeMixin",
        "StateAuthorityRuntimeMixin",
        "V55FoundationEngine",
    ])
    require(root / "src/aasm/physical_effect_binding.py", [
        'PHYSICAL_EFFECT_AUTHORITY_BINDING_CONTRACT_ID = "aasm.effect.physical-authority-binding.v1"',
        '"authorization_recheck": "MANDATORY_AT_EXISTING_AUTHORIZE_EFFECT_BOUNDARY"',
        '"execution_recheck": "MANDATORY_AT_EXISTING_EXECUTE_EFFECT_BOUNDARY"',
        '"prior_use_validation_is_authorization": False',
        '"parallel_dispatcher": "NONE"',
    ])
    require(root / "src/aasm/physical_effect_integration_runtime.py", [
        'PHYSICAL_EFFECT_INTEGRATION_RUNTIME_CONTRACT_ID = "aasm.effect.physical-authority-integration.runtime.v1"',
        '"effect_authority": "EXISTING_V53_EFFECT_AUTHORIZE_AND_EFFECT_EXECUTE_REMAIN_REQUIRED"',
        '"machine_transition_binding": "MANDATORY_BEFORE_AUTHORIZATION_OR_NEW_DISPATCH"',
        '"task_lease": "EXISTING_V54_TASKLEASE_UNCHANGED"',
        '"ownership": "EXISTING_V54_EFFECT_OWNERSHIP_UNCHANGED"',
        '"unknown_and_reconciliation": "EXISTING_V54_UNKNOWN_AND_RECONCILIATION_UNCHANGED"',
    ])
    require(root / "src/aasm/physical_effect_integration_boundary.py", [
        "owner_worker_id: str | None = None",
        "task_lease_id: str | None = None",
        'boundary="EXECUTE"',
    ])
    require(root / "src/aasm/state_conflict.py", [
        'STATE_CONFLICT_CONTRACT_ID = "aasm.state.conflict.v1"',
        '"comparison": "EXACT_CANONICAL_PORTABLE_JSON_VALUE_PLUS_EXACT_REVISION_IDENTITY"',
        '"conflict_grants_fact_authority": False',
        '"conflict_grants_effect_authority": False',
        '"host_wall_clock_in_identity": False',
        '"parallel_truth_table": "NONE"',
    ])
    require(root / "src/aasm/state_conflict_runtime.py", [
        'STATE_CONFLICT_RUNTIME_CONTRACT_ID = "aasm.state.conflict.runtime.v1"',
        '"claim_source": "EXISTING_AASM_STATE_CLAIM_PROJECTION_ONLY"',
        '"authority": "EXISTING_AASM_SCOPED_AUTHORITY_ONLY"',
        '"observation_authority_elevation": "NONE"',
        '"parallel_dependency_graph": "NONE"',
    ])
    require(root / "src/aasm/event_causality.py", [
        'EVENT_CAUSALITY_CONTRACT_ID = "aasm.event.causality.v1"',
        "PORTABLE_U63_MAX = (1 << 63) - 1",
        '"local_event_identity": "NODE_ID_PLUS_BOOT_EPOCH_PLUS_MONOTONIC_LOCAL_SEQUENCE"',
        '"receipt_order_implies_source_order": False',
        '"host_wall_clock": "NOT_UNIVERSAL_TRUTH_AND_NEVER_IMPLICITLY_CAPTURED"',
        '"parallel_event_ledger": "NONE"',
    ])
    require(root / "src/aasm/event_causality_runtime.py", [
        'EVENT_CAUSALITY_RUNTIME_CONTRACT_ID = "aasm.event.causality.runtime.v1"',
        '"core_aasm_event_log": "UNCHANGED_AND_REMAINS_REPLAY_LEDGER"',
        '"same_node_boot_order": "SEQUENCE_DEFINES_LOCAL_ORDER_INDEPENDENT_OF_INGEST_ORDER"',
        '"authority": "EXISTING_AASM_SCOPED_AUTHORITY_ONLY"',
        '"parallel_event_ledger": "NONE"',
    ])
    require(root / "src/aasm/observation_freshness.py", [
        'OBSERVATION_FRESHNESS_CONTRACT_ID = "aasm.observation.freshness.v1"',
        '"reference_time": "EXPLICIT_INTEGER_NANOSECONDS_NEVER_IMPLICIT_HOST_NOW"',
        '"receipt_fallback": "OPTIONAL_AND_EXPLICITLY_MARKED_WEAKER_AGE_BASIS"',
        '"freshness_elevates_observation_authority": False',
        '"freshness_is_universal_admission": False',
    ])
    require(root / "src/aasm/observation_freshness_runtime.py", [
        'OBSERVATION_FRESHNESS_RUNTIME_CONTRACT_ID = "aasm.observation.freshness.runtime.v1"',
        '"observation_source": "EXISTING_MACHINE_STATE_OBSERVATION_ONLY"',
        '"causal_source": "EXACT_DURABLE_CAUSAL_EVENT_ID_AND_FINGERPRINT"',
        '"reference_time_source": "EXPLICIT_CALLER_POLICY_INPUT_NOT_HOST_NOW"',
        '"universal_admission": "NONE"',
    ])

    require(root / "src/aasm/public_v55.py", ['__version__ = "0.55.0"', '"contract_version": "0.31.0"'])
    require(root / "src/aasm/public_v54.py", ['__version__ = "0.54.0"', '"contract_version": "0.30.0"'])
    require(root / "src/aasm/semantic_evolution.py", [
        'EXTERNAL_REFERENCE_CONTRACT_ID = "aasm.external.reference.v1"',
        'PROBLEM_REVISION_CONTRACT_ID = "aasm.problem.revision.v1"',
        'PROBLEM_DELTA_CONTRACT_ID = "aasm.problem.delta.v1"',
    ])
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
        "check_physical_authority_contracts.py",
        "check_effect_capability_contracts.py",
        "check_physical_control_fencing_contracts.py",
        "check_physical_effect_integration_contracts.py",
        "check_state_conflict_contracts.py",
        "check_causal_freshness_contracts.py",
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
    ):
        require(root / "schemas" / schema, ['"$schema"', "2020-12"])

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

    require(root / ".github/workflows/v56.yml", [
        "AASM v0.56 Development Qualification",
        "check_physical_effect_integration_contracts.py",
        "tests/test_physical_effect_integration.py",
        "check_state_conflict_contracts.py",
        "tests/test_state_conflict.py",
        "check_causal_freshness_contracts.py",
        "tests/test_causal_freshness.py",
        "0.32.10",
        "context='aasm/v56'",
    ])
    require(root / ".github/workflows/effect-capability.yml", ["context='aasm/effect-capability'"])
    require(root / ".github/workflows/physical-control-fencing.yml", ["context='aasm/physical-control-fencing'"])
    require(root / ".github/workflows/physical-preemption-recovery.yml", ["context='aasm/physical-preemption-recovery'"])
    require(root / ".github/workflows/physical-effect-integration.yml", [
        "check_physical_effect_integration_contracts.py",
        "tests/test_physical_effect_integration.py",
        "context='aasm/physical-effect-integration'",
    ])
    require(root / ".github/workflows/physical-evidence.yml", [
        "check_state_conflict_contracts.py",
        "tests/test_state_conflict.py",
        "check_causal_freshness_contracts.py",
        "tests/test_causal_freshness.py",
        "context='aasm/physical-evidence'",
    ])
    require(root / ".github/workflows/release.yml", [
        "workflow_dispatch:",
        "confirm_release:",
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
        "check_version_policy.py",
        "release_manifest.py --check-file-list",
        "verify-github-release",
    ])
    forbid(root / ".github/workflows/release.yml", ["workflow_run:"])

    env = os.environ.copy()
    src = str(root / "src")
    env["PYTHONPATH"] = src if not env.get("PYTHONPATH") else src + os.pathsep + env["PYTHONPATH"]
    code = (
        "import aasm; "
        "r=aasm.validate_public_api_contract(); assert r['valid'], r; "
        "c=aasm.public_api_contract(); assert c['runtime_version']=='0.56.1'; "
        "assert c['contract_version']=='0.32.10'; "
        "assert 'physical_effect_integration' in c and 'state_conflict' in c and 'event_causality' in c and 'observation_freshness' in c"
    )
    completed = subprocess.run([sys.executable, "-c", code], cwd=root, env=env)
    if completed.returncode != 0:
        _fail("active public contract execution failed")

    print("0.56.1 development target + active adoption 0.32.10 + PR-3 + S3 conflict/causality/freshness source/release contracts: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
