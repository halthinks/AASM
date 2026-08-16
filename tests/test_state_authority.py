from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from aasm import AASMEngine, FactAuthority, StateClaim, state_authority_contract
from aasm.evidence import EvidenceRecord
from aasm.model import ProblemSpec
from aasm.persistence.sqlite import SQLiteStore
from aasm.scoped_authority import Principal, ScopedAuthorityGrant, Workspace
from aasm.state_authority_runtime import STATE_AUTHORITY_CAPABILITIES, state_authority_runtime_contract


def _grant(engine, subject: str, *capabilities: str, expires_at=None):
    return engine.admit_scoped_authority_grant(
        ScopedAuthorityGrant(
            subject,
            "root",
            "workspace-a",
            "root",
            tuple(capabilities),
            expires_at=expires_at,
        )
    )


def bootstrapped_engine(*, store=None, grant_state_authority: bool = True):
    engine = AASMEngine(ProblemSpec("governed state authority"), store=store)
    trust = engine.add_evidence(
        EvidenceRecord(
            kind="trust_anchor",
            statement="operator admitted workspace root identity",
            source="fixture.root-of-trust",
        ),
        reason="state authority fixture trust anchor",
    )
    engine.bootstrap_scoped_workspace(
        Principal("root", "SYSTEM"),
        Workspace("workspace-a", "root"),
        trust_anchor_evidence_id=trust.evidence_id,
    )
    _grant(engine, "root", "identity.register")
    engine.register_scoped_principal(
        Principal("sensor-a", "MACHINE"),
        workspace_id="workspace-a",
        actor_principal_id="root",
    )
    if grant_state_authority:
        _grant(
            engine,
            "root",
            STATE_AUTHORITY_CAPABILITIES["fact_authority_register"],
            STATE_AUTHORITY_CAPABILITIES["fact_authority_revoke"],
            STATE_AUTHORITY_CAPABILITIES["claim_desired"],
            STATE_AUTHORITY_CAPABILITIES["claim_predicted"],
        )
        _grant(
            engine,
            "sensor-a",
            STATE_AUTHORITY_CAPABILITIES["claim_observed"],
            STATE_AUTHORITY_CAPABILITIES["claim_authoritative"],
        )
    return engine


def observed_claim(*, value=21.5, namespace="temperature.c", external_revision_id="device-rev-1"):
    return StateClaim(
        "OBSERVED",
        "workspace-a",
        "root",
        "device-a",
        namespace,
        value,
        "sensor-a",
        external_revision_id=external_revision_id,
    )


def fact_authority(*, expires_at=None, namespace="temperature.c", external_revision_id="device-rev-1"):
    return FactAuthority(
        "workspace-a",
        "root",
        "device-a",
        namespace,
        "sensor-a",
        expires_at=expires_at,
        external_revision_id=external_revision_id,
    )


def authoritative_from(observed: StateClaim, *, value=None, namespace=None, external_revision_id=None):
    return StateClaim(
        "AUTHORITATIVE",
        observed.workspace_id,
        observed.scope_id,
        observed.subject_id,
        observed.state_namespace if namespace is None else namespace,
        observed.value if value is None else value,
        observed.source_principal_id,
        external_revision_id=(
            observed.external_revision_id if external_revision_id is None else external_revision_id
        ),
        source_claim_ids=(observed.claim_id,),
    )


def test_contract_separates_intent_prediction_observation_authority_and_effect_rights():
    contract = state_authority_contract()
    runtime = state_authority_runtime_contract()
    assert contract["claim_kinds"] == ["DESIRED", "PREDICTED", "OBSERVED", "AUTHORITATIVE"]
    assert contract["desired"] == "INTENT_ONLY_NEVER_OBSERVATION_OR_FACT_AUTHORITY"
    assert contract["predicted"] == "MODEL_EXPECTATION_ONLY_NEVER_OBSERVATION_OR_FACT_AUTHORITY"
    assert contract["observed"] == "EMPIRICAL_EVIDENCE_ONLY_NOT_AUTHORITATIVE_BY_EXISTENCE_OR_AGREEMENT"
    assert contract["authoritative"] == "EXPLICIT_MATCHING_FACT_AUTHORITY_AND_SOURCE_CLAIM_REQUIRED"
    assert contract["aggregation_grants_authority"] is False
    assert contract["fact_authority_grants_effect_authority"] is False
    assert contract["state_claim_grants_effect_authority"] is False
    assert runtime["parallel_truth_table"] == "NONE"
    assert runtime["machine_state_mutation"] == "NONE"
    assert runtime["effect_authority"] == "NONE"


def test_state_authority_objects_are_deterministic_and_schema_valid():
    authority = fact_authority(expires_at=10)
    authority_round_trip = FactAuthority.from_dict(authority.to_dict())
    assert authority_round_trip == authority
    assert authority_round_trip.fingerprint == authority.fingerprint

    observation = observed_claim()
    observation_round_trip = StateClaim.from_dict(observation.to_dict())
    assert observation_round_trip == observation
    assert observation_round_trip.fingerprint == observation.fingerprint

    root = Path(__file__).resolve().parents[1]
    authority_schema = json.loads((root / "schemas" / "fact-authority.schema.json").read_text())
    claim_schema = json.loads((root / "schemas" / "state-claim.schema.json").read_text())
    Draft202012Validator(authority_schema).validate(authority.to_dict())
    Draft202012Validator(claim_schema).validate(observation.to_dict())


def test_authoritative_claim_requires_explicit_source_claim_even_before_runtime_admission():
    with pytest.raises(ValueError, match="source_claim_id"):
        StateClaim(
            "AUTHORITATIVE",
            "workspace-a",
            "root",
            "device-a",
            "temperature.c",
            21.5,
            "sensor-a",
        )


def test_fact_authority_registration_is_fail_closed_and_denial_is_durable():
    engine = bootstrapped_engine(grant_state_authority=False)
    before = len(engine.snapshot.evidence["records"])
    with pytest.raises(PermissionError, match="state.fact-authority.register"):
        engine.register_fact_authority(
            fact_authority(),
            actor_principal_id="root",
        )
    after = len(engine.snapshot.evidence["records"])
    assert after == before + 1
    authority_report = engine.scoped_authority_report(workspace_id="workspace-a")
    assert any(
        row["request"]["capability"] == STATE_AUTHORITY_CAPABILITIES["fact_authority_register"]
        and row["decision"]["allowed"] is False
        for row in authority_report["decisions"].values()
    )
    assert engine.state_authority_report()["authorities"] == {}


def test_desired_predicted_and_observed_claims_do_not_mutate_core_machine_or_calculus_state():
    engine = bootstrapped_engine()
    before_machine_state = engine.snapshot.state
    before_active_values = deepcopy(engine.calculus_report()["active_values"])

    desired = StateClaim(
        "DESIRED",
        "workspace-a",
        "root",
        "device-a",
        "temperature.c",
        25.0,
        "root",
        external_revision_id="device-rev-1",
    )
    predicted = StateClaim(
        "PREDICTED",
        "workspace-a",
        "root",
        "device-a",
        "temperature.c",
        24.8,
        "root",
        source_claim_ids=(desired.claim_id,),
        external_revision_id="device-rev-1",
    )
    observation = observed_claim(value=21.5)

    engine.record_state_claim(desired, actor_principal_id="root")
    engine.record_state_claim(predicted, actor_principal_id="root")
    engine.record_state_claim(observation, actor_principal_id="sensor-a")

    report = engine.state_authority_report()
    assert {row["claim"]["claim_kind"] for row in report["claims"].values()} == {
        "DESIRED",
        "PREDICTED",
        "OBSERVED",
    }
    assert engine.snapshot.state == before_machine_state
    assert engine.calculus_report()["active_values"] == before_active_values
    assert report["machine_state_mutation"] == "NONE"
    assert report["effect_authority"] == "NONE"
    assert engine.replay().canonical_hash() == engine.snapshot.canonical_hash()


def test_observation_does_not_become_authoritative_without_matching_fact_authority():
    engine = bootstrapped_engine()
    observation = observed_claim()
    engine.record_state_claim(observation, actor_principal_id="sensor-a")
    target = authoritative_from(observation)
    with pytest.raises(PermissionError, match="no active matching fact authority"):
        engine.record_state_claim(target, actor_principal_id="sensor-a")
    report = engine.state_authority_report()
    assert [row["claim"]["claim_kind"] for row in report["claims"].values()] == ["OBSERVED"]


def test_two_agreeing_observations_do_not_vote_themselves_into_authority():
    engine = bootstrapped_engine()
    first = observed_claim(value=21.5)
    second = StateClaim(
        "OBSERVED",
        "workspace-a",
        "root",
        "device-a",
        "temperature.c",
        21.5,
        "sensor-a",
        source_claim_ids=(first.claim_id,),
        external_revision_id="device-rev-1",
        metadata={"independent_sample": 2},
    )
    engine.record_state_claim(first, actor_principal_id="sensor-a")
    engine.record_state_claim(second, actor_principal_id="sensor-a")
    report = engine.state_authority_report()
    assert len(report["claims"]) == 2
    assert all(row["claim"]["claim_kind"] == "OBSERVED" for row in report["claims"].values())
    assert not any(row["claim"]["claim_kind"] == "AUTHORITATIVE" for row in report["claims"].values())


def test_authoritative_claim_requires_matching_active_fact_authority_and_observed_source():
    engine = bootstrapped_engine()
    authority = fact_authority()
    registered = engine.register_fact_authority(authority, actor_principal_id="root")
    assert registered["authority"]["authority_id"] == authority.authority_id

    observation = observed_claim()
    engine.record_state_claim(observation, actor_principal_id="sensor-a")
    target = authoritative_from(observation)
    result = engine.record_state_claim(target, actor_principal_id="sensor-a")
    assert result["fact_authority_id"] == authority.authority_id
    assert engine.state_claim_report(target.claim_id)["claim"]["claim_kind"] == "AUTHORITATIVE"
    assert engine.replay().canonical_hash() == engine.snapshot.canonical_hash()


def test_authoritative_claim_rejects_non_observed_source_and_context_or_revision_laundering():
    engine = bootstrapped_engine()
    engine.register_fact_authority(fact_authority(), actor_principal_id="root")

    desired = StateClaim(
        "DESIRED",
        "workspace-a",
        "root",
        "device-a",
        "temperature.c",
        21.5,
        "root",
        external_revision_id="device-rev-1",
    )
    engine.record_state_claim(desired, actor_principal_id="root")
    forged = StateClaim(
        "AUTHORITATIVE",
        "workspace-a",
        "root",
        "device-a",
        "temperature.c",
        21.5,
        "sensor-a",
        source_claim_ids=(desired.claim_id,),
        external_revision_id="device-rev-1",
    )
    with pytest.raises(ValueError, match="OBSERVED source"):
        engine.record_state_claim(forged, actor_principal_id="sensor-a")

    observation = observed_claim()
    engine.record_state_claim(observation, actor_principal_id="sensor-a")
    wrong_namespace = authoritative_from(observation, namespace="pressure.kpa")
    with pytest.raises(ValueError, match="source state claim context"):
        engine.record_state_claim(wrong_namespace, actor_principal_id="sensor-a")

    wrong_revision = authoritative_from(observation, external_revision_id="device-rev-2")
    with pytest.raises(ValueError, match="external revision mismatch"):
        engine.record_state_claim(wrong_revision, actor_principal_id="sensor-a")


def test_expired_and_revoked_fact_authority_fail_closed():
    engine = bootstrapped_engine()
    expiring = fact_authority(expires_at=5)
    engine.register_fact_authority(expiring, actor_principal_id="root", at_time=1)
    observation = observed_claim()
    engine.record_state_claim(observation, actor_principal_id="sensor-a", at_time=1)
    with pytest.raises(PermissionError, match="no active matching fact authority"):
        engine.record_state_claim(authoritative_from(observation), actor_principal_id="sensor-a", at_time=5)
    assert engine.state_authority_report(at_time=5)["authorities"][expiring.authority_id]["status"] == "EXPIRED"

    active = fact_authority(namespace="humidity.relative", external_revision_id="device-rev-1")
    engine.register_fact_authority(active, actor_principal_id="root", at_time=1)
    humidity = observed_claim(value=40.0, namespace="humidity.relative")
    engine.record_state_claim(humidity, actor_principal_id="sensor-a", at_time=1)
    revoked = engine.revoke_fact_authority(active.authority_id, actor_principal_id="root", at_time=2)
    assert revoked["already_revoked"] is False
    assert engine.state_authority_report(at_time=3)["authorities"][active.authority_id]["status"] == "REVOKED"
    with pytest.raises(PermissionError, match="no active matching fact authority"):
        engine.record_state_claim(authoritative_from(humidity), actor_principal_id="sensor-a", at_time=3)


def test_claim_source_principal_cannot_be_impersonated_by_another_actor():
    engine = bootstrapped_engine()
    observation = observed_claim()
    with pytest.raises(PermissionError, match="actor must equal source_principal_id"):
        engine.record_state_claim(observation, actor_principal_id="root")
    assert engine.state_authority_report()["claims"] == {}


def test_sqlite_restart_reconstructs_state_authority_only_from_existing_evidence_history(tmp_path: Path):
    path = tmp_path / "state-authority.db"
    store = SQLiteStore(str(path))
    engine = bootstrapped_engine(store=store)
    machine_id = engine.snapshot.machine_id
    authority = fact_authority()
    engine.register_fact_authority(authority, actor_principal_id="root")
    observation = observed_claim()
    engine.record_state_claim(observation, actor_principal_id="sensor-a")
    target = authoritative_from(observation)
    engine.record_state_claim(target, actor_principal_id="sensor-a")
    before = engine.state_authority_report()
    before_hash = engine.snapshot.canonical_hash()
    store.close()

    reopened = SQLiteStore(str(path))
    resumed = AASMEngine.resume(machine_id, reopened)
    after = resumed.state_authority_report()
    assert after["authorities"] == before["authorities"]
    assert after["claims"] == before["claims"]
    assert resumed.snapshot.canonical_hash() == before_hash
    assert resumed.replay().canonical_hash() == resumed.snapshot.canonical_hash()
    reopened.close()
