import json
from pathlib import Path

from jsonschema import Draft202012Validator

from aasm.effects import (
    EFFECT_GOVERNANCE_CONTRACT_VERSION,
    EFFECT_INTENT_CONTRACT_ID,
    EFFECT_OWNERSHIP_CONTRACT_ID,
    EffectIntent,
    EffectOutcome,
    EffectOwnership,
    EffectReconciliation,
    EffectRecord,
    EffectSpec,
    effect_governance_contract,
)
from aasm.persistence.effect_serde import effect_from_dict, effect_to_dict


def test_all_json_schemas_parse():
    root = Path(__file__).resolve().parents[1]
    for path in (root / "schemas").glob("*.json"):
        data = json.loads(path.read_text())
        assert data["$schema"].startswith("https://json-schema.org/")


def test_v54_effect_intent_ownership_and_unknown_reconciliation_round_trip():
    spec = EffectSpec("external-write", {"value": 1}, idempotency_key="stable-key", effect_id="effect-fixture")
    intent = EffectIntent.from_spec(
        spec,
        workspace_id="workspace-a",
        scope_id="scope-a",
        resource_reservation_ids=("reservation-b", "reservation-a", "reservation-a"),
        proposer_principal_id="principal-proposer",
    )
    assert intent.resource_reservation_ids == ("reservation-a", "reservation-b")
    assert EffectIntent.from_dict(intent.to_dict()) == intent

    ownership = EffectOwnership(
        effect_id=spec.effect_id,
        intent_id=intent.intent_id,
        execution_id="execution-1",
        owner_worker_id="worker-1",
        workspace_id="workspace-a",
        scope_id="scope-a",
        authority_decision_evidence_id="evidence-authority-1",
        resource_reservation_ids=intent.resource_reservation_ids,
        task_lease_id="lease-1",
        owner_principal_id="principal-worker",
    )
    assert EffectOwnership.from_dict(ownership.to_dict()) == ownership

    reconciliation = EffectReconciliation(
        effect_id=spec.effect_id,
        outcome=EffectOutcome.UNKNOWN.value,
        ownership_id=ownership.ownership_id,
        reconciled_by_principal_id="principal-controller",
        authority_decision_evidence_id="evidence-reconcile-1",
        evidence_ids=("evidence-observation-1",),
    )
    assert reconciliation.retry_blocked is True
    assert EffectReconciliation.from_dict(reconciliation.to_dict()) == reconciliation

    record = EffectRecord(
        "machine-1",
        spec,
        intent=intent.to_dict(),
        ownership=ownership.to_dict(),
        reconciliation=reconciliation.to_dict(),
    )
    encoded = effect_to_dict(record)
    decoded = effect_from_dict(encoded)
    assert effect_to_dict(decoded) == encoded

    root = Path(__file__).resolve().parents[1]
    schema = json.loads((root / "schemas" / "effect.schema.json").read_text())
    Draft202012Validator(schema).validate(encoded)


def test_v54_effect_foundation_preserves_legacy_effect_records():
    legacy = {
        "machine_id": "machine-legacy",
        "spec": {
            "effect_type": "legacy",
            "payload": {},
            "idempotency_key": "legacy-key",
            "preconditions": [],
            "postconditions": [],
            "retry_policy": {"max_attempts": 1, "retry_on_failure": False, "retry_on_unknown": False},
            "reversible": False,
            "compensation": None,
            "effect_id": "effect-legacy",
        },
        "status": "PROPOSED",
        "attempts": 0,
        "authorization_id": None,
        "authority": None,
        "execution_id": None,
        "result": None,
        "error": None,
        "evidence": [],
        "created_at": 1.0,
        "updated_at": 1.0,
    }
    record = effect_from_dict(legacy)
    assert record.intent is None
    assert record.ownership is None
    assert record.reconciliation is None


def test_v54_effect_governance_contract_reuses_existing_planes():
    contract = effect_governance_contract()
    assert contract["intent_contract_id"] == EFFECT_INTENT_CONTRACT_ID
    assert contract["ownership_contract_id"] == EFFECT_OWNERSHIP_CONTRACT_ID
    assert contract["contract_version"] == EFFECT_GOVERNANCE_CONTRACT_VERSION
    assert contract["existing_effect_execution"] == "REUSED_NEVER_REPLACED"
    assert contract["task_lease"] == "EXISTING_AASM_TASKLEASE_ONLY"
    assert contract["truth_authority"] == "EXISTING_AASM_POLICY_ONLY"
