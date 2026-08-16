from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from aasm import AASMEngine as ActiveEngine
from aasm.evidence import EvidenceRecord
from aasm.model import ProblemSpec
from aasm.persistence.sqlite import SQLiteStore
from aasm.scoped_authority import Principal, ScopedAuthorityGrant, Workspace
from aasm.state_authority import FactAuthority, StateClaim
from aasm.state_authority_runtime import STATE_AUTHORITY_CAPABILITIES
from aasm.state_conflict import StateConflict, state_conflict_contract, state_conflict_reasons
from aasm.state_conflict_runtime import STATE_CONFLICT_CAPABILITIES, state_conflict_runtime_contract


WORKSPACE = "workspace-a"
SCOPE = "root"
ROOT = "root"
SENSOR = "sensor-a"
DETECTOR = "conflict-detector"


StateConflictEngine = ActiveEngine


def _grant(engine, subject: str, *capabilities: str):
    return engine.admit_scoped_authority_grant(
        ScopedAuthorityGrant(subject, ROOT, WORKSPACE, SCOPE, tuple(capabilities))
    )


def bootstrapped_engine(*, store=None, grant_conflict=True):
    engine = StateConflictEngine(ProblemSpec("S3 state conflict"), store=store)
    trust = engine.add_evidence(
        EvidenceRecord("trust_anchor", "S3 fixture root", source="fixture.root-of-trust"),
        reason="S3 state conflict trust anchor",
    )
    engine.bootstrap_scoped_workspace(
        Principal(ROOT, "SYSTEM"), Workspace(WORKSPACE, ROOT), trust_anchor_evidence_id=trust.evidence_id
    )
    _grant(engine, ROOT, "identity.register")
    for principal_id in (SENSOR, DETECTOR):
        engine.register_scoped_principal(
            Principal(principal_id, "SERVICE"), workspace_id=WORKSPACE, actor_principal_id=ROOT
        )
    _grant(
        engine,
        ROOT,
        STATE_AUTHORITY_CAPABILITIES["fact_authority_register"],
        STATE_AUTHORITY_CAPABILITIES["claim_desired"],
        STATE_AUTHORITY_CAPABILITIES["claim_predicted"],
    )
    _grant(
        engine,
        SENSOR,
        STATE_AUTHORITY_CAPABILITIES["claim_observed"],
        STATE_AUTHORITY_CAPABILITIES["claim_authoritative"],
    )
    if grant_conflict:
        _grant(engine, DETECTOR, STATE_CONFLICT_CAPABILITIES["record"])
    return engine


def _authority(engine, *, namespace="device.mode", problem_revision="problem-r1", external_revision="device-r1"):
    item = FactAuthority(
        WORKSPACE,
        SCOPE,
        "device-a",
        namespace,
        SENSOR,
        problem_revision_id=problem_revision,
        external_revision_id=external_revision,
    )
    engine.register_fact_authority(item, actor_principal_id=ROOT)
    return item


def _authoritative_actual(
    engine,
    value,
    *,
    namespace="device.mode",
    problem_revision="problem-r1",
    external_revision="device-r1",
):
    _authority(
        engine,
        namespace=namespace,
        problem_revision=problem_revision,
        external_revision=external_revision,
    )
    observed = StateClaim(
        "OBSERVED",
        WORKSPACE,
        SCOPE,
        "device-a",
        namespace,
        value,
        SENSOR,
        problem_revision_id=problem_revision,
        external_revision_id=external_revision,
    )
    engine.record_state_claim(observed, actor_principal_id=SENSOR)
    authoritative = StateClaim(
        "AUTHORITATIVE",
        WORKSPACE,
        SCOPE,
        "device-a",
        namespace,
        value,
        SENSOR,
        problem_revision_id=problem_revision,
        external_revision_id=external_revision,
        source_claim_ids=(observed.claim_id,),
    )
    engine.record_state_claim(authoritative, actor_principal_id=SENSOR)
    return observed, authoritative


def _desired(
    engine,
    value,
    *,
    namespace="device.mode",
    problem_revision="problem-r1",
    external_revision="device-r1",
):
    item = StateClaim(
        "DESIRED",
        WORKSPACE,
        SCOPE,
        "device-a",
        namespace,
        value,
        ROOT,
        problem_revision_id=problem_revision,
        external_revision_id=external_revision,
    )
    engine.record_state_claim(item, actor_principal_id=ROOT)
    return item


def _predicted(
    engine,
    value,
    *,
    namespace="device.mode",
    problem_revision="problem-r1",
    external_revision="device-r1",
):
    item = StateClaim(
        "PREDICTED",
        WORKSPACE,
        SCOPE,
        "device-a",
        namespace,
        value,
        ROOT,
        problem_revision_id=problem_revision,
        external_revision_id=external_revision,
    )
    engine.record_state_claim(item, actor_principal_id=ROOT)
    return item


def test_state_conflict_contract_is_evidence_only_and_portable():
    semantic = state_conflict_contract()
    runtime = state_conflict_runtime_contract()
    assert semantic["comparison"] == "EXACT_CANONICAL_PORTABLE_JSON_VALUE_PLUS_EXACT_REVISION_IDENTITY"
    assert semantic["quantity_tolerance"] == "RESERVED_FOR_S4_QUANTITY_SEMANTICS"
    assert semantic["history"] == "EXPECTATION_AND_ACTUAL_STATE_CLAIMS_REMAIN_UNCHANGED"
    assert semantic["actual_observation_authority"] == "PRESERVE_SOURCE_CLAIM_KIND_NEVER_ELEVATE_OBSERVED_TO_AUTHORITATIVE"
    assert semantic["conflict_grants_fact_authority"] is False
    assert semantic["conflict_grants_effect_authority"] is False
    assert semantic["conflict_mutates_machine_state"] is False
    assert semantic["conflict_mutates_state_claims"] is False
    assert semantic["host_wall_clock_in_identity"] is False
    assert semantic["python_object_identity_in_identity"] is False
    assert semantic["parallel_truth_table"] == "NONE"
    assert runtime["durability"] == "EXISTING_AASM_EVIDENCE_EVENT_REPLAY"
    assert runtime["claim_source"] == "EXISTING_AASM_STATE_CLAIM_PROJECTION_ONLY"
    assert runtime["authority"] == "EXISTING_AASM_SCOPED_AUTHORITY_ONLY"
    assert runtime["parallel_truth_table"] == "NONE"
    assert runtime["parallel_dependency_graph"] == "NONE"


def test_state_conflict_identity_round_trip_and_schema_are_deterministic():
    expected = StateClaim(
        "DESIRED", WORKSPACE, SCOPE, "device-a", "device.mode", {"mode": "ON", "limit": 4}, ROOT,
        problem_revision_id="problem-r1", external_revision_id="device-r1",
    )
    actual = StateClaim(
        "OBSERVED", WORKSPACE, SCOPE, "device-a", "device.mode", {"mode": "OFF", "limit": 4}, SENSOR,
        problem_revision_id="problem-r1", external_revision_id="device-r1",
    )
    item = StateConflict.from_claims(expected, actual)
    copy = StateConflict.from_dict(item.to_dict())
    assert copy == item
    assert copy.fingerprint == item.fingerprint
    assert copy.reasons == ("VALUE_MISMATCH",)
    schema = json.loads(
        (Path(__file__).resolve().parents[1] / "schemas" / "state-conflict.schema.json").read_text()
    )
    Draft202012Validator(schema).validate(item.to_dict())


def test_portable_value_comparison_uses_canonical_json_not_python_equality_or_mapping_order():
    expected_map = StateClaim(
        "PREDICTED", WORKSPACE, SCOPE, "device-a", "payload", {"a": 1, "b": [2, 3]}, ROOT
    )
    actual_same_map = StateClaim(
        "OBSERVED", WORKSPACE, SCOPE, "device-a", "payload", {"b": [2, 3], "a": 1}, SENSOR
    )
    assert state_conflict_reasons(expected_map, actual_same_map) == ()
    with pytest.raises(ValueError, match="do not conflict"):
        StateConflict.from_claims(expected_map, actual_same_map)

    expected_bool = StateClaim("PREDICTED", WORKSPACE, SCOPE, "device-a", "payload", True, ROOT)
    actual_int = StateClaim("OBSERVED", WORKSPACE, SCOPE, "device-a", "payload", 1, SENSOR)
    assert state_conflict_reasons(expected_bool, actual_int) == ("VALUE_MISMATCH",)

    nonfinite = StateClaim("OBSERVED", WORKSPACE, SCOPE, "device-a", "payload", float("nan"), SENSOR)
    with pytest.raises(ValueError, match="non-finite"):
        state_conflict_reasons(expected_bool, nonfinite)


def test_noncomparable_claim_context_is_rejected_not_laundered_into_conflict():
    expected = StateClaim("DESIRED", WORKSPACE, SCOPE, "device-a", "mode", "ON", ROOT)
    actual = StateClaim("OBSERVED", WORKSPACE, SCOPE, "device-b", "mode", "OFF", SENSOR)
    with pytest.raises(ValueError, match="subject_id mismatch"):
        state_conflict_reasons(expected, actual)


def test_durable_conflict_preserves_claims_authorities_effects_and_core_machine_state():
    engine = bootstrapped_engine()
    expected = _desired(engine, "ON")
    _, actual = _authoritative_actual(engine, "OFF")
    before_state = deepcopy(engine.snapshot.state)
    before_values = deepcopy(engine.calculus_report()["active_values"])
    before_authority = deepcopy(engine.state_authority_report())
    before_effects = deepcopy(engine.store.list_effects(engine.snapshot.machine_id))

    result = engine.record_state_conflict(
        expected.claim_id,
        actual.claim_id,
        actor_principal_id=DETECTOR,
        at_time=20.0,
    )
    assert result["conflict"]["reasons"] == ["VALUE_MISMATCH"]
    assert result["claim_mutation"] is False
    assert result["machine_state_mutation"] is False
    assert result["fact_authority_created"] is False
    assert result["effect_authority_granted"] is False
    assert result["observation_authority_elevated"] is False
    assert engine.state_authority_report() == before_authority
    assert engine.snapshot.state == before_state
    assert engine.calculus_report()["active_values"] == before_values
    assert engine.store.list_effects(engine.snapshot.machine_id) == before_effects
    assert engine.replay().canonical_hash() == engine.snapshot.canonical_hash()

    again = engine.record_state_conflict(
        expected.claim_id,
        actual.claim_id,
        actor_principal_id=DETECTOR,
        at_time=999.0,
    )
    assert again["already_recorded"] is True
    assert again["conflict"]["conflict_id"] == result["conflict"]["conflict_id"]
    assert again["conflict"]["fingerprint"] == result["conflict"]["fingerprint"]


def test_observed_only_actual_can_be_recorded_without_authority_elevation():
    engine = bootstrapped_engine()
    expected = _desired(engine, 5, namespace="rail.voltage")
    observed = StateClaim(
        "OBSERVED", WORKSPACE, SCOPE, "device-a", "rail.voltage", 4, SENSOR,
        problem_revision_id="problem-r1", external_revision_id="device-r1",
    )
    engine.record_state_claim(observed, actor_principal_id=SENSOR)
    before_authorities = set(engine.state_authority_report()["authorities"])
    result = engine.record_state_conflict(
        expected.claim_id,
        observed.claim_id,
        actor_principal_id=DETECTOR,
    )
    assert result["conflict"]["actual_claim_kind"] == "OBSERVED"
    assert result["observation_authority_elevated"] is False
    assert set(engine.state_authority_report()["authorities"]) == before_authorities


def test_conflict_recording_requires_existing_scoped_authority():
    engine = bootstrapped_engine(grant_conflict=False)
    expected = _desired(engine, "ON")
    _, actual = _authoritative_actual(engine, "OFF")
    with pytest.raises(PermissionError, match="state.conflict.record"):
        engine.record_state_conflict(
            expected.claim_id,
            actual.claim_id,
            actor_principal_id=DETECTOR,
        )
    assert engine.state_conflicts_report()["conflicts"] == {}


def test_textpcb_style_out_of_band_project_revision_is_a_generic_revision_conflict():
    engine = bootstrapped_engine()
    predicted = _predicted(
        engine,
        {"drc": "PASS", "unresolved": 0},
        namespace="board.drc.summary",
        problem_revision="pcb-problem-r17",
        external_revision="textpcb-project-r42",
    )
    _, actual = _authoritative_actual(
        engine,
        {"drc": "PASS", "unresolved": 0},
        namespace="board.drc.summary",
        problem_revision="pcb-problem-r17",
        external_revision="textpcb-project-r43",
    )
    result = engine.record_state_conflict(
        predicted.claim_id,
        actual.claim_id,
        actor_principal_id=DETECTOR,
        reason="TextPCB-style out-of-band project revision detected",
    )
    conflict = result["conflict"]
    assert conflict["reasons"] == ["EXTERNAL_REVISION_MISMATCH"]
    assert conflict["expectation_external_revision_id"] == "textpcb-project-r42"
    assert conflict["actual_external_revision_id"] == "textpcb-project-r43"
    assert conflict["state_namespace"] == "board.drc.summary"
    assert "textpcb" not in conflict["contract_id"].lower()
    assert engine.state_claim_report(predicted.claim_id)["claim"]["external_revision_id"] == "textpcb-project-r42"
    assert engine.state_claim_report(actual.claim_id)["claim"]["external_revision_id"] == "textpcb-project-r43"


def test_problem_revision_mismatch_is_durable_even_when_values_match():
    engine = bootstrapped_engine()
    expected = _predicted(engine, "PASS", problem_revision="problem-r1")
    _, actual = _authoritative_actual(engine, "PASS", problem_revision="problem-r2")
    result = engine.record_state_conflict(
        expected.claim_id,
        actual.claim_id,
        actor_principal_id=DETECTOR,
    )
    assert result["conflict"]["reasons"] == ["PROBLEM_REVISION_MISMATCH"]


def test_sqlite_restart_reconstructs_conflict_from_existing_evidence_without_identity_drift(tmp_path: Path):
    path = tmp_path / "state-conflict.db"
    store = SQLiteStore(str(path))
    engine = bootstrapped_engine(store=store)
    machine_id = engine.snapshot.machine_id
    expected = _desired(engine, "ON")
    _, actual = _authoritative_actual(engine, "OFF")
    recorded = engine.record_state_conflict(
        expected.claim_id,
        actual.claim_id,
        actor_principal_id=DETECTOR,
        at_time=20.0,
    )
    conflict_id = recorded["conflict"]["conflict_id"]
    fingerprint = recorded["conflict"]["fingerprint"]
    before_hash = engine.snapshot.canonical_hash()
    store.close()

    reopened = SQLiteStore(str(path))
    resumed = StateConflictEngine.resume(machine_id, reopened)
    report = resumed.state_conflict_report(conflict_id)
    assert report["conflict"]["fingerprint"] == fingerprint
    assert resumed.snapshot.canonical_hash() == before_hash
    assert resumed.replay().canonical_hash() == resumed.snapshot.canonical_hash()
    reopened.close()
