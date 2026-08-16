from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from aasm import AASMEngine as ActiveEngine
from aasm.event_causality import (
    PORTABLE_U63_MAX,
    CausalEventIdentity,
    CausalRelation,
    event_causality_contract,
)
from aasm.event_causality_runtime import (
    EVENT_CAUSALITY_CAPABILITIES,
    event_causality_runtime_contract,
)
from aasm.evidence import EvidenceRecord
from aasm.external_machine import MachineBinding, MachineStateObservation
from aasm.external_machine_runtime import EXTERNAL_MACHINE_CAPABILITIES
from aasm.model import ProblemSpec
from aasm.observation_freshness import (
    ObservationFreshnessAssessment,
    observation_freshness_contract,
)
from aasm.observation_freshness_runtime import (
    OBSERVATION_FRESHNESS_CAPABILITIES,
    observation_freshness_runtime_contract,
)
from aasm.persistence.sqlite import SQLiteStore
from aasm.scoped_authority import Principal, ScopedAuthorityGrant, Workspace
from aasm.state_authority import StateClaim
from aasm.state_authority_runtime import STATE_AUTHORITY_CAPABILITIES
from aasm.typed_protocol import CapabilityContract


WORKSPACE = "workspace-a"
SCOPE = "root"
ROOT = "root"
SENSOR = "sensor-a"
ASSESSOR = "freshness-assessor"
OBSERVER_CAPABILITY = "machine.observe"
OPERATOR_CAPABILITY = "machine.operate"


TemporalEvidenceEngine = ActiveEngine


def _grant(engine, subject: str, *capabilities: str):
    return engine.admit_scoped_authority_grant(
        ScopedAuthorityGrant(subject, ROOT, WORKSPACE, SCOPE, tuple(capabilities))
    )


def bootstrapped_engine(*, store=None, grant_temporal=True):
    engine = TemporalEvidenceEngine(ProblemSpec("S3 causal freshness"), store=store)
    trust = engine.add_evidence(
        EvidenceRecord("trust_anchor", "S3 temporal fixture root", source="fixture.root-of-trust"),
        reason="S3 temporal fixture trust anchor",
    )
    engine.bootstrap_scoped_workspace(
        Principal(ROOT, "SYSTEM"), Workspace(WORKSPACE, ROOT), trust_anchor_evidence_id=trust.evidence_id
    )
    _grant(engine, ROOT, "identity.register")
    for principal_id in (SENSOR, ASSESSOR):
        engine.register_scoped_principal(
            Principal(principal_id, "SERVICE"), workspace_id=WORKSPACE, actor_principal_id=ROOT
        )
    engine.register_capability_contract(
        CapabilityContract(OBSERVER_CAPABILITY, "OBSERVER", "1.0.0"),
        authority_id="policy",
        authority_class="POLICY",
    )
    engine.register_capability_contract(
        CapabilityContract(OPERATOR_CAPABILITY, "OPERATOR", "1.0.0"),
        authority_id="policy",
        authority_class="POLICY",
    )
    _grant(engine, ROOT, EXTERNAL_MACHINE_CAPABILITIES["binding_register"])
    _grant(
        engine,
        SENSOR,
        STATE_AUTHORITY_CAPABILITIES["claim_observed"],
        EXTERNAL_MACHINE_CAPABILITIES["observation_record"],
    )
    if grant_temporal:
        _grant(engine, SENSOR, EVENT_CAUSALITY_CAPABILITIES["record"])
        _grant(
            engine,
            ASSESSOR,
            EVENT_CAUSALITY_CAPABILITIES["record"],
            EVENT_CAUSALITY_CAPABILITIES["relate"],
            OBSERVATION_FRESHNESS_CAPABILITIES["assess"],
        )
    return engine


def prepare_observation(
    engine,
    *,
    namespace="temperature.c",
    value=25.0,
    problem_revision="problem-r1",
    external_revision="device-r1",
    receipt_id="sample-1",
):
    binding = MachineBinding(
        WORKSPACE,
        SCOPE,
        f"machine-{external_revision}",
        "device-a",
        (namespace,),
        OBSERVER_CAPABILITY,
        OPERATOR_CAPABILITY,
        external_revision,
        problem_revision_id=problem_revision,
    )
    engine.register_machine_binding(binding, actor_principal_id=ROOT)
    claim = StateClaim(
        "OBSERVED",
        WORKSPACE,
        SCOPE,
        "device-a",
        namespace,
        value,
        SENSOR,
        problem_revision_id=problem_revision,
        external_revision_id=external_revision,
        metadata={"receipt_id": receipt_id},
    )
    engine.record_state_claim(claim, actor_principal_id=SENSOR)
    observation = MachineStateObservation(
        binding.binding_id,
        claim.claim_id,
        SENSOR,
        OBSERVER_CAPABILITY,
        external_revision,
        receipt_id=receipt_id,
    )
    engine.record_machine_state_observation(observation, actor_principal_id=SENSOR)
    return binding, claim, observation


def machine_event(
    observation: MachineStateObservation,
    claim: StateClaim,
    *,
    node_id="sensor-node-a",
    boot_epoch=1,
    sequence=0,
    source_time_ns=1_000,
    source_clock_id="device-monotonic",
    source_clock_quality="MONOTONIC_LOCAL",
    source_clock_uncertainty_ns=None,
    receipt_time_ns=1_050,
    receipt_clock_id="host-monotonic",
):
    return CausalEventIdentity(
        workspace_id=claim.workspace_id,
        scope_id=claim.scope_id,
        subject_id=claim.subject_id,
        node_id=node_id,
        boot_epoch=boot_epoch,
        sequence=sequence,
        event_kind="OBSERVATION_EMITTED",
        object_kind="MACHINE_STATE_OBSERVATION",
        object_id=observation.observation_id,
        source_time_ns=source_time_ns,
        source_clock_id=source_clock_id if source_time_ns is not None else "",
        source_clock_quality=source_clock_quality,
        source_clock_uncertainty_ns=source_clock_uncertainty_ns,
        receipt_time_ns=receipt_time_ns,
        receipt_clock_id=receipt_clock_id if receipt_time_ns is not None else "",
        problem_revision_id=claim.problem_revision_id,
        external_revision_id=claim.external_revision_id,
    )


def record_machine_event(engine, observation, claim, **kwargs):
    event = machine_event(observation, claim, **kwargs)
    result = engine.record_machine_observation_causal_event(
        observation.observation_id,
        event,
        actor_principal_id=SENSOR,
    )
    return event, result


def generic_event(
    *,
    node_id,
    boot_epoch,
    sequence,
    object_id,
    source_time_ns=None,
    receipt_time_ns=None,
):
    return CausalEventIdentity(
        WORKSPACE,
        SCOPE,
        "device-a",
        node_id,
        boot_epoch,
        sequence,
        "TEST_EVENT",
        "TEST_OBJECT",
        object_id,
        source_time_ns=source_time_ns,
        source_clock_id="local" if source_time_ns is not None else "",
        source_clock_quality="MONOTONIC_LOCAL" if source_time_ns is not None else "UNKNOWN",
        receipt_time_ns=receipt_time_ns,
        receipt_clock_id="host" if receipt_time_ns is not None else "",
    )


def test_causal_and_freshness_contracts_preserve_existing_event_truth_and_authority_planes():
    causal = event_causality_contract()
    causal_runtime = event_causality_runtime_contract()
    freshness = observation_freshness_contract()
    freshness_runtime = observation_freshness_runtime_contract()

    assert causal["local_event_identity"] == "NODE_ID_PLUS_BOOT_EPOCH_PLUS_MONOTONIC_LOCAL_SEQUENCE"
    assert causal["receipt_order_implies_source_order"] is False
    assert causal["host_wall_clock"] == "NOT_UNIVERSAL_TRUTH_AND_NEVER_IMPLICITLY_CAPTURED"
    assert causal["event_log_role"] == "CAUSAL_IDENTITY_OVER_EXISTING_DURABLE_OBJECTS_NOT_SECOND_AASM_EVENT_LEDGER"
    assert causal["parallel_event_ledger"] == "NONE"
    assert causal["relation_grants_fact_authority"] is False
    assert causal["relation_grants_effect_authority"] is False
    assert causal_runtime["core_aasm_event_log"] == "UNCHANGED_AND_REMAINS_REPLAY_LEDGER"
    assert causal_runtime["same_node_boot_order"] == "SEQUENCE_DEFINES_LOCAL_ORDER_INDEPENDENT_OF_INGEST_ORDER"
    assert causal_runtime["parallel_event_ledger"] == "NONE"

    assert freshness["reference_time"] == "EXPLICIT_INTEGER_NANOSECONDS_NEVER_IMPLICIT_HOST_NOW"
    assert freshness["receipt_fallback"] == "OPTIONAL_AND_EXPLICITLY_MARKED_WEAKER_AGE_BASIS"
    assert freshness["freshness_grants_fact_authority"] is False
    assert freshness["freshness_grants_effect_authority"] is False
    assert freshness["freshness_elevates_observation_authority"] is False
    assert freshness["freshness_is_universal_admission"] is False
    assert freshness_runtime["reference_time_source"] == "EXPLICIT_CALLER_POLICY_INPUT_NOT_HOST_NOW"
    assert freshness_runtime["parallel_observation_store"] == "NONE"
    assert freshness_runtime["parallel_truth_table"] == "NONE"


def test_causal_event_relation_and_freshness_objects_round_trip_and_validate_schemas():
    event = generic_event(node_id="n1", boot_epoch=1, sequence=4, object_id="obj-1", source_time_ns=100)
    event_copy = CausalEventIdentity.from_dict(event.to_dict())
    assert event_copy == event
    assert event_copy.fingerprint == event.fingerprint

    other = generic_event(node_id="n2", boot_epoch=1, sequence=7, object_id="obj-2", source_time_ns=110)
    relation = CausalRelation("ORDER_UNKNOWN", event.event_id, event.fingerprint, other.event_id, other.fingerprint)
    relation_copy = CausalRelation.from_dict(relation.to_dict())
    assert relation_copy == relation

    assessment = ObservationFreshnessAssessment(
        WORKSPACE, SCOPE, "device-a", "temperature.c",
        "observation-1", "a" * 64, "claim-1", "b" * 64,
        event.event_id, event.fingerprint, 1, 1, "problem-r1", "problem-r1",
        "device-r1", "device-r1", 150, "local", 100,
        age_basis="SOURCE_TIME", age_ns=50, status="FRESH",
    )
    assessment_copy = ObservationFreshnessAssessment.from_dict(assessment.to_dict())
    assert assessment_copy == assessment

    root = Path(__file__).resolve().parents[1] / "schemas"
    Draft202012Validator(json.loads((root / "causal-event.schema.json").read_text())).validate(event.to_dict())
    Draft202012Validator(json.loads((root / "causal-relation.schema.json").read_text())).validate(relation.to_dict())
    Draft202012Validator(json.loads((root / "observation-freshness.schema.json").read_text())).validate(assessment.to_dict())


def test_portable_integer_range_rejects_unbounded_python_only_values():
    with pytest.raises(ValueError, match="between"):
        generic_event(node_id="n", boot_epoch=1, sequence=PORTABLE_U63_MAX + 1, object_id="o")
    with pytest.raises(ValueError, match="between"):
        generic_event(node_id="n", boot_epoch=1, sequence=1, object_id="o", source_time_ns=PORTABLE_U63_MAX + 1)


def test_same_local_identity_cannot_be_reused_for_different_event_content():
    engine = bootstrapped_engine()
    first = generic_event(node_id="sensor-node", boot_epoch=1, sequence=8, object_id="object-a")
    second = generic_event(node_id="sensor-node", boot_epoch=1, sequence=8, object_id="object-b")
    assert first.event_id == second.event_id
    assert first.fingerprint != second.fingerprint
    engine.record_causal_event(first, actor_principal_id=ASSESSOR)
    with pytest.raises(ValueError, match="local identity collision"):
        engine.record_causal_event(second, actor_principal_id=ASSESSOR)


def test_reboot_epoch_allows_sequence_reset_without_event_identity_collision():
    engine = bootstrapped_engine()
    before_reboot = generic_event(node_id="sensor-node", boot_epoch=1, sequence=0, object_id="before")
    after_reboot = generic_event(node_id="sensor-node", boot_epoch=2, sequence=0, object_id="after")
    assert before_reboot.event_id != after_reboot.event_id
    engine.record_causal_event(before_reboot, actor_principal_id=ASSESSOR)
    engine.record_causal_event(after_reboot, actor_principal_id=ASSESSOR)
    assert len(engine.event_causality_report()["events"]) == 2


def test_receipt_order_does_not_override_same_node_boot_source_sequence():
    engine = bootstrapped_engine()
    first = generic_event(node_id="sensor-node", boot_epoch=1, sequence=8, object_id="a", receipt_time_ns=200)
    second = generic_event(node_id="sensor-node", boot_epoch=1, sequence=9, object_id="b", receipt_time_ns=100)
    engine.record_causal_event(second, actor_principal_id=ASSESSOR)
    engine.record_causal_event(first, actor_principal_id=ASSESSOR)
    allowed = CausalRelation("HAPPENS_BEFORE", first.event_id, first.fingerprint, second.event_id, second.fingerprint)
    result = engine.record_causal_relation(allowed, actor_principal_id=ASSESSOR)
    assert result["relation"]["relation"] == "HAPPENS_BEFORE"
    assert first.receipt_time_ns > second.receipt_time_ns


def test_same_node_boot_relations_cannot_contradict_known_local_sequence():
    engine = bootstrapped_engine()
    first = generic_event(node_id="sensor-node", boot_epoch=1, sequence=8, object_id="a")
    second = generic_event(node_id="sensor-node", boot_epoch=1, sequence=9, object_id="b")
    engine.record_causal_event(first, actor_principal_id=ASSESSOR)
    engine.record_causal_event(second, actor_principal_id=ASSESSOR)
    reverse = CausalRelation("HAPPENS_BEFORE", second.event_id, second.fingerprint, first.event_id, first.fingerprint)
    with pytest.raises(ValueError, match="contradicts"):
        engine.record_causal_relation(reverse, actor_principal_id=ASSESSOR)
    concurrent = CausalRelation("CONCURRENT_WITH", first.event_id, first.fingerprint, second.event_id, second.fingerprint)
    with pytest.raises(ValueError, match="contradicts"):
        engine.record_causal_relation(concurrent, actor_principal_id=ASSESSOR)
    caused = CausalRelation("CAUSED_BY", second.event_id, second.fingerprint, first.event_id, first.fingerprint)
    assert engine.record_causal_relation(caused, actor_principal_id=ASSESSOR)["relation"]["relation"] == "CAUSED_BY"


def test_symmetric_relation_identity_is_canonical_across_argument_order():
    one = generic_event(node_id="n1", boot_epoch=1, sequence=1, object_id="a")
    two = generic_event(node_id="n2", boot_epoch=1, sequence=1, object_id="b")
    forward = CausalRelation("CONCURRENT_WITH", one.event_id, one.fingerprint, two.event_id, two.fingerprint)
    reverse = CausalRelation("CONCURRENT_WITH", two.event_id, two.fingerprint, one.event_id, one.fingerprint)
    assert forward == reverse
    assert forward.relation_id == reverse.relation_id
    assert forward.fingerprint == reverse.fingerprint


def test_machine_observation_causal_event_requires_exact_existing_object_and_revision():
    engine = bootstrapped_engine()
    _, claim, observation = prepare_observation(engine)
    valid = machine_event(observation, claim)
    wrong_object = CausalEventIdentity.from_dict({**valid.to_dict(), "object_id": "other", "event_id": ""})
    with pytest.raises(ValueError, match="exact durable machine state observation"):
        engine.record_machine_observation_causal_event(
            observation.observation_id, wrong_object, actor_principal_id=SENSOR
        )
    wrong_revision = CausalEventIdentity.from_dict({**valid.to_dict(), "external_revision_id": "device-r2", "event_id": ""})
    with pytest.raises(ValueError, match="external revision"):
        engine.record_machine_observation_causal_event(
            observation.observation_id, wrong_revision, actor_principal_id=SENSOR
        )
    result = engine.record_machine_observation_causal_event(
        observation.observation_id, valid, actor_principal_id=SENSOR
    )
    assert result["fact_authority_created"] is False
    assert result["effect_authority_granted"] is False
    assert result["machine_state_mutated"] is False


def test_source_time_freshness_uses_explicit_clock_and_does_not_elevate_observation():
    engine = bootstrapped_engine()
    _, claim, observation = prepare_observation(engine)
    event, _ = record_machine_event(engine, observation, claim, source_time_ns=1_000, receipt_time_ns=1_050)
    before_claim = deepcopy(engine.state_claim_report(claim.claim_id))
    result = engine.assess_machine_observation_freshness(
        observation.observation_id,
        event.event_id,
        actor_principal_id=ASSESSOR,
        expected_boot_epoch=1,
        reference_time_ns=1_100,
        reference_clock_id="device-monotonic",
        max_age_ns=200,
        expected_problem_revision_id="problem-r1",
        expected_external_revision_id="device-r1",
    )
    assessment = result["assessment"]
    assert assessment["status"] == "FRESH"
    assert assessment["age_basis"] == "SOURCE_TIME"
    assert assessment["age_ns"] == 100
    assert assessment["reasons"] == []
    assert result["fact_authority_created"] is False
    assert result["effect_authority_granted"] is False
    assert result["observation_authority_elevated"] is False
    assert result["universal_admission_granted"] is False
    assert engine.state_claim_report(claim.claim_id) == before_claim
    assert engine.state_claim_report(claim.claim_id)["claim"]["claim_kind"] == "OBSERVED"


def test_age_over_policy_is_stale():
    engine = bootstrapped_engine()
    _, claim, observation = prepare_observation(engine)
    event, _ = record_machine_event(engine, observation, claim, source_time_ns=1_000)
    result = engine.assess_machine_observation_freshness(
        observation.observation_id, event.event_id,
        actor_principal_id=ASSESSOR,
        expected_boot_epoch=1,
        reference_time_ns=1_500,
        reference_clock_id="device-monotonic",
        max_age_ns=200,
    )
    assert result["assessment"]["status"] == "STALE"
    assert "MAX_AGE_EXCEEDED" in result["assessment"]["reasons"]


def test_boot_epoch_mismatch_is_stale_even_when_age_is_recent():
    engine = bootstrapped_engine()
    _, claim, observation = prepare_observation(engine)
    event, _ = record_machine_event(engine, observation, claim, boot_epoch=1, source_time_ns=1_000)
    result = engine.assess_machine_observation_freshness(
        observation.observation_id, event.event_id,
        actor_principal_id=ASSESSOR,
        expected_boot_epoch=2,
        reference_time_ns=1_010,
        reference_clock_id="device-monotonic",
        max_age_ns=100,
    )
    assert result["assessment"]["status"] == "STALE"
    assert "BOOT_EPOCH_MISMATCH" in result["assessment"]["reasons"]


def test_textpcb_style_recent_drc_observation_is_stale_when_project_revision_advanced():
    engine = bootstrapped_engine()
    _, claim, observation = prepare_observation(
        engine,
        namespace="board.drc.summary",
        value={"drc": "PASS", "unresolved": 0},
        problem_revision="pcb-problem-r17",
        external_revision="textpcb-project-r42",
    )
    event, _ = record_machine_event(
        engine,
        observation,
        claim,
        node_id="textpcb-project-engine",
        source_time_ns=9_990,
        source_clock_id="textpcb-monotonic",
        receipt_time_ns=9_995,
        receipt_clock_id="host-monotonic",
    )
    result = engine.assess_machine_observation_freshness(
        observation.observation_id, event.event_id,
        actor_principal_id=ASSESSOR,
        expected_boot_epoch=1,
        reference_time_ns=10_000,
        reference_clock_id="textpcb-monotonic",
        max_age_ns=100,
        expected_problem_revision_id="pcb-problem-r17",
        expected_external_revision_id="textpcb-project-r43",
    )
    assessment = result["assessment"]
    assert assessment["age_ns"] == 10
    assert assessment["status"] == "STALE"
    assert "EXTERNAL_REVISION_MISMATCH" in assessment["reasons"]
    assert "textpcb" not in assessment["contract_id"].lower()
    assert engine.machine_state_observation_report(observation.observation_id)["observation"]["external_revision_id"] == "textpcb-project-r42"


def test_source_clock_mismatch_without_fallback_is_unknown():
    engine = bootstrapped_engine()
    _, claim, observation = prepare_observation(engine)
    event, _ = record_machine_event(engine, observation, claim, source_time_ns=1_000, receipt_time_ns=1_050)
    result = engine.assess_machine_observation_freshness(
        observation.observation_id, event.event_id,
        actor_principal_id=ASSESSOR,
        expected_boot_epoch=1,
        reference_time_ns=1_100,
        reference_clock_id="host-monotonic",
        max_age_ns=200,
        allow_receipt_time_fallback=False,
    )
    assessment = result["assessment"]
    assert assessment["status"] == "UNKNOWN"
    assert assessment["age_basis"] == "UNRESOLVED"
    assert "SOURCE_CLOCK_MISMATCH" in assessment["reasons"]
    assert "AGE_UNRESOLVED" in assessment["reasons"]


def test_receipt_fallback_is_explicitly_marked_and_can_be_fresh():
    engine = bootstrapped_engine()
    _, claim, observation = prepare_observation(engine)
    event, _ = record_machine_event(
        engine, observation, claim,
        source_time_ns=1_000,
        source_clock_id="device-monotonic",
        source_clock_quality="UNSYNCHRONIZED",
        receipt_time_ns=1_050,
        receipt_clock_id="host-monotonic",
    )
    result = engine.assess_machine_observation_freshness(
        observation.observation_id, event.event_id,
        actor_principal_id=ASSESSOR,
        expected_boot_epoch=1,
        reference_time_ns=1_100,
        reference_clock_id="host-monotonic",
        max_age_ns=100,
        minimum_source_clock_quality="MONOTONIC_LOCAL",
        allow_receipt_time_fallback=True,
    )
    assessment = result["assessment"]
    assert assessment["status"] == "FRESH"
    assert assessment["age_basis"] == "RECEIPT_TIME"
    assert assessment["age_ns"] == 50
    assert "RECEIPT_FALLBACK_USED" in assessment["reasons"]
    assert "CLOCK_QUALITY_INSUFFICIENT" in assessment["reasons"]


def test_clock_uncertainty_policy_can_force_unknown_or_fallback():
    engine = bootstrapped_engine()
    _, claim, observation = prepare_observation(engine)
    event, _ = record_machine_event(
        engine, observation, claim,
        source_time_ns=1_000,
        source_clock_quality="TRACEABLE",
        source_clock_uncertainty_ns=50,
        receipt_time_ns=1_010,
        receipt_clock_id="host-monotonic",
    )
    unknown = engine.assess_machine_observation_freshness(
        observation.observation_id, event.event_id,
        actor_principal_id=ASSESSOR,
        expected_boot_epoch=1,
        reference_time_ns=1_020,
        reference_clock_id="device-monotonic",
        max_age_ns=100,
        minimum_source_clock_quality="SYNCHRONIZED",
        max_source_clock_uncertainty_ns=10,
    )
    assert unknown["assessment"]["status"] == "UNKNOWN"
    assert "CLOCK_UNCERTAINTY_EXCEEDED" in unknown["assessment"]["reasons"]


def test_negative_age_is_unknown_not_fresh():
    engine = bootstrapped_engine()
    _, claim, observation = prepare_observation(engine)
    event, _ = record_machine_event(engine, observation, claim, source_time_ns=2_000)
    result = engine.assess_machine_observation_freshness(
        observation.observation_id, event.event_id,
        actor_principal_id=ASSESSOR,
        expected_boot_epoch=1,
        reference_time_ns=1_999,
        reference_clock_id="device-monotonic",
        max_age_ns=100,
    )
    assert result["assessment"]["status"] == "UNKNOWN"
    assert "NEGATIVE_AGE" in result["assessment"]["reasons"]
    assert result["assessment"]["age_ns"] is None


def test_freshness_requires_scoped_assessor_authority():
    engine = bootstrapped_engine(grant_temporal=False)
    _grant(engine, SENSOR, EVENT_CAUSALITY_CAPABILITIES["record"])
    _, claim, observation = prepare_observation(engine)
    event, _ = record_machine_event(engine, observation, claim)
    with pytest.raises(PermissionError, match="observation.freshness.assess"):
        engine.assess_machine_observation_freshness(
            observation.observation_id, event.event_id,
            actor_principal_id=ASSESSOR,
            expected_boot_epoch=1,
            reference_time_ns=1_100,
            reference_clock_id="device-monotonic",
            max_age_ns=200,
        )


def test_same_freshness_request_is_idempotent_across_different_authority_context_times():
    engine = bootstrapped_engine()
    _, claim, observation = prepare_observation(engine)
    event, _ = record_machine_event(engine, observation, claim)
    kwargs = dict(
        actor_principal_id=ASSESSOR,
        expected_boot_epoch=1,
        reference_time_ns=1_100,
        reference_clock_id="device-monotonic",
        max_age_ns=200,
    )
    first = engine.assess_machine_observation_freshness(observation.observation_id, event.event_id, at_time=5.0, **kwargs)
    second = engine.assess_machine_observation_freshness(observation.observation_id, event.event_id, at_time=500.0, **kwargs)
    assert second["already_assessed"] is True
    assert second["assessment"]["assessment_id"] == first["assessment"]["assessment_id"]
    assert second["assessment"]["fingerprint"] == first["assessment"]["fingerprint"]


def test_sqlite_restart_reconstructs_causal_event_relation_and_freshness_without_drift(tmp_path: Path):
    path = tmp_path / "causal-freshness.db"
    store = SQLiteStore(str(path))
    engine = bootstrapped_engine(store=store)
    machine_id = engine.snapshot.machine_id
    _, claim, observation = prepare_observation(engine)
    event, event_result = record_machine_event(engine, observation, claim)
    assessment = engine.assess_machine_observation_freshness(
        observation.observation_id, event.event_id,
        actor_principal_id=ASSESSOR,
        expected_boot_epoch=1,
        reference_time_ns=1_100,
        reference_clock_id="device-monotonic",
        max_age_ns=200,
    )
    extra = generic_event(node_id="observer-b", boot_epoch=1, sequence=0, object_id="external-b")
    engine.record_causal_event(extra, actor_principal_id=ASSESSOR)
    relation = CausalRelation("ORDER_UNKNOWN", event.event_id, event.fingerprint, extra.event_id, extra.fingerprint)
    relation_result = engine.record_causal_relation(relation, actor_principal_id=ASSESSOR)
    before_hash = engine.snapshot.canonical_hash()
    store.close()

    reopened = SQLiteStore(str(path))
    resumed = TemporalEvidenceEngine.resume(machine_id, reopened)
    assert resumed.causal_event_report(event.event_id)["event"]["fingerprint"] == event.fingerprint
    assert resumed.causal_relation_report(relation.relation_id)["relation"]["fingerprint"] == relation.fingerprint
    assert resumed.observation_freshness_assessment_report(assessment["assessment"]["assessment_id"])["assessment"]["fingerprint"] == assessment["assessment"]["fingerprint"]
    assert resumed.snapshot.canonical_hash() == before_hash
    assert resumed.replay().canonical_hash() == resumed.snapshot.canonical_hash()
    assert event_result["fact_authority_created"] is False
    assert relation_result["effect_authority_granted"] is False
    reopened.close()
