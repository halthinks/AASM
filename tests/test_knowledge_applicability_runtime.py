from __future__ import annotations

from copy import deepcopy

import pytest

from aasm.cross_run_knowledge import CrossRunAdmissionCertificate, CrossRunKnowledgeEnvelope
from aasm.evidence import EvidenceRecord
from aasm.knowledge_applicability import (
    ApplicabilityCheck,
    ApplicabilityPredicateResult,
    KnowledgeApplication,
    KnowledgeItem,
    KnowledgeSelection,
    applicability_check_from_cross_run_certificate,
    knowledge_item_from_cross_run_envelope,
)
from aasm.knowledge_applicability_runtime import (
    KNOWLEDGE_APPLICATION_RECORD,
    KNOWLEDGE_DOCUMENT,
    KNOWLEDGE_RECORD_TYPE,
    KnowledgeApplicabilityRuntimeMixin,
    knowledge_document,
)
from aasm.model import ProblemSpec
from aasm.runtime_v56_foundation import AASMEngine as V56FoundationEngine
from aasm.semantic_result import semantic_fingerprint


class KnowledgeEngine(KnowledgeApplicabilityRuntimeMixin, V56FoundationEngine):
    pass


def _sha(label: str) -> str:
    return semantic_fingerprint({"fixture": label})


def _engine() -> KnowledgeEngine:
    return KnowledgeEngine(ProblemSpec("S5.4 governed knowledge applicability and application"))


def _support(engine: KnowledgeEngine):
    return {
        name: engine.add_evidence(EvidenceRecord("observation", name, source="test"))
        for name in ("source", "selection", "predicate-a", "predicate-b", "application", "cross-run")
    }


def _item(rows, *, predicates=("same-environment", "same-semantics")):
    return KnowledgeItem(
        "PROCEDURAL",
        {"rule": "prefer exact certified reuse before recomputation"},
        "root",
        "knowledge-source-1",
        _sha("source-object-v1"),
        ("root", "planning"),
        tuple(predicates),
        ("SEMANTIC_CHANGE", "ENVIRONMENT_CHANGE", "SOURCE_REVOCATION"),
        (rows["source"].evidence_id,),
        "",
        None,
        0.0,
        0.91,
        {"fixture": "s5.4"},
    )


def _selection(item, rows, *, target=None, scope="root"):
    return KnowledgeSelection(
        item.knowledge_id,
        item.fingerprint,
        scope,
        target or _sha("target-v1"),
        "semantic similarity plus exact source provenance",
        "retriever-a",
        (rows["selection"].evidence_id,),
        1,
        0.83,
    )


def _check(item, selection, rows, *, statuses=("PASS", "PASS")):
    supports = (rows["predicate-a"], rows["predicate-b"])
    results = tuple(
        ApplicabilityPredicateResult(
            predicate,
            status,
            f"{predicate} assessed {status.lower()}",
            (support.evidence_id,) if status != "INCONCLUSIVE" else (),
        )
        for predicate, status, support in zip(item.applicability_predicates, statuses, supports)
    )
    return ApplicabilityCheck(
        item.knowledge_id,
        item.fingerprint,
        selection.selection_id,
        selection.fingerprint,
        selection.target_scope_id,
        selection.target_semantic_fingerprint,
        results,
        "applicability-verifier-a",
        100.0,
        item.invalidation_triggers,
    )


def _record_chain(engine, rows, *, statuses=("PASS", "PASS")):
    item = _item(rows)
    item_record = engine.record_knowledge_item(item)
    selection = _selection(item, rows)
    selection_record = engine.record_knowledge_selection(selection)
    check = _check(item, selection, rows, statuses=statuses)
    check_record = engine.record_applicability_check(check)
    return item, item_record, selection, selection_record, check, check_record


def test_selection_is_not_applicability_or_authority():
    engine = _engine()
    rows = _support(engine)
    item = _item(rows)
    selection = _selection(item, rows)
    engine.record_knowledge_item(item)
    result = engine.record_knowledge_selection(selection)

    assert result["selection"]["applicability_claim"] == "NONE"
    assert result["selection"]["authority_claim"] == "NONE"
    report = engine.knowledge_applicability_history_report()
    assert report["valid"]
    assert report["applicability_checks"] == {}
    assert report["applications"] == {}
    assert not any(event.event_type == "authorized" for event in engine.events)


def test_applicable_check_requires_every_declared_predicate_and_evidence():
    engine = _engine()
    rows = _support(engine)
    item = _item(rows)
    selection = _selection(item, rows)
    engine.record_knowledge_item(item)
    engine.record_knowledge_selection(selection)

    missing = ApplicabilityCheck(
        item.knowledge_id,
        item.fingerprint,
        selection.selection_id,
        selection.fingerprint,
        selection.target_scope_id,
        selection.target_semantic_fingerprint,
        (ApplicabilityPredicateResult(item.applicability_predicates[0], "PASS", "only one predicate checked", (rows["predicate-a"].evidence_id,)),),
        "applicability-verifier-a",
        100.0,
        item.invalidation_triggers,
    )
    with pytest.raises(ValueError, match="assess every declared item predicate"):
        engine.record_applicability_check(missing)
    with pytest.raises(ValueError, match="requires Evidence"):
        ApplicabilityPredicateResult("same-environment", "PASS", "unsupported pass", ())


@pytest.mark.parametrize("statuses", [("FAIL", "PASS"), ("INCONCLUSIVE", "PASS")])
def test_inapplicable_and_inconclusive_checks_block_authorization(statuses):
    engine = _engine()
    rows = _support(engine)
    _, _, _, _, check, _ = _record_chain(engine, rows, statuses=statuses)
    assert check.status in {"INAPPLICABLE", "INCONCLUSIVE"}
    with pytest.raises(PermissionError, match="APPLICABILITY_NOT_CURRENT"):
        engine.authorize_knowledge_application(check.applicability_id, current_target_fingerprint=_sha("target-v1"), application_kind="PLANNING_GUIDANCE")


def test_target_semantic_drift_blocks_authorization_and_application():
    engine = _engine()
    rows = _support(engine)
    _, _, selection, _, check, _ = _record_chain(engine, rows)
    with pytest.raises(PermissionError, match="TARGET_SEMANTIC_FINGERPRINT_DRIFT"):
        engine.authorize_knowledge_application(check.applicability_id, current_target_fingerprint=_sha("target-v2"), application_kind="PLANNING_GUIDANCE")

    authorized = engine.authorize_knowledge_application(check.applicability_id, current_target_fingerprint=selection.target_semantic_fingerprint, application_kind="PLANNING_GUIDANCE")
    with pytest.raises(PermissionError, match="TARGET_SEMANTIC_FINGERPRINT_DRIFT"):
        engine.record_knowledge_application(authorized, current_target_fingerprint=_sha("target-v2"), application_evidence_ids=(rows["application"].evidence_id,), applied_by="planner-a")


def test_authorized_application_binds_existing_aasm_authority_event():
    engine = _engine()
    rows = _support(engine)
    item, _, selection, _, check, _ = _record_chain(engine, rows)
    authorized = engine.authorize_knowledge_application(check.applicability_id, current_target_fingerprint=selection.target_semantic_fingerprint, application_kind="PLANNING_GUIDANCE")
    result = engine.record_knowledge_application(authorized, current_target_fingerprint=selection.target_semantic_fingerprint, application_evidence_ids=(rows["application"].evidence_id,), applied_by="planner-a")
    application = KnowledgeApplication.from_dict(result["application"])

    assert application.authorization_id == authorized.authorization_id
    assert application.authority == authorized.authority
    assert application.knowledge_id == item.knowledge_id
    assert application.to_dict()["source_authority_inherited"] is False
    authorization_events = [event for event in engine.events if event.event_type == "authorized" and event.data.get("authorization_id") == authorized.authorization_id]
    assert len(authorization_events) == 1
    assert application.authorization_event_id == authorization_events[0].event_id
    assert engine.knowledge_applicability_history_report()["valid"]


def test_forged_application_without_canonical_authorized_event_is_rejected_by_projection():
    engine = _engine()
    rows = _support(engine)
    item, item_row, selection, selection_row, check, check_row = _record_chain(engine, rows)
    forged = KnowledgeApplication(
        item.knowledge_id,
        item.fingerprint,
        selection.selection_id,
        selection.fingerprint,
        check.applicability_id,
        check.fingerprint,
        selection.target_scope_id,
        selection.target_semantic_fingerprint,
        "PLANNING_GUIDANCE",
        "NONE",
        (rows["application"].evidence_id,),
        "auth-forged",
        "controller",
        _sha("forged-proposal"),
        "evt-forged",
        "attacker",
        101.0,
    )
    document = {"application": forged.to_dict()}
    engine.add_evidence(EvidenceRecord(
        "knowledge_governance",
        knowledge_document(document),
        source="test-forgery",
        derived_from=[item_row["evidence_id"], selection_row["evidence_id"], check_row["evidence_id"], rows["application"].evidence_id],
        metadata={KNOWLEDGE_RECORD_TYPE: KNOWLEDGE_APPLICATION_RECORD, "object_id": forged.application_id, KNOWLEDGE_DOCUMENT: document, "authority": "FORGED_METADATA_ONLY"},
    ))
    projection = engine.knowledge_applicability_history_report()
    assert not projection["valid"]
    assert any("KNOWLEDGE_APPLICATION_AUTHORIZED_EVENT_MISSING" in row["error"] for row in projection["issues"])


def test_verification_relief_requires_exact_authorized_proposal_and_does_not_mutate_verification():
    engine = _engine()
    rows = _support(engine)
    _, _, selection, _, check, _ = _record_chain(engine, rows)
    before = deepcopy(engine.snapshot.calculus)
    authorized = engine.authorize_knowledge_application(check.applicability_id, current_target_fingerprint=selection.target_semantic_fingerprint, application_kind="VERIFICATION_REUSE", verification_effect="REDUCE")
    assert authorized.proposal.reversible is False
    assert authorized.proposal.payload["verification_effect"] == "REDUCE"
    result = engine.record_knowledge_application(authorized, current_target_fingerprint=selection.target_semantic_fingerprint, application_evidence_ids=(rows["application"].evidence_id,), applied_by="controller")
    assert result["application"]["verification_effect"] == "REDUCE"
    assert engine.snapshot.calculus == before
    assert engine.knowledge_applicability_runtime_contract_report()["verification_mutation"] == "NONE"


def test_stale_or_invalidated_applicability_support_blocks_application():
    engine = _engine()
    rows = _support(engine)
    _, _, selection, _, check, _ = _record_chain(engine, rows)
    authorized = engine.authorize_knowledge_application(check.applicability_id, current_target_fingerprint=selection.target_semantic_fingerprint, application_kind="PLANNING_GUIDANCE")
    engine.invalidate_evidence(rows["predicate-a"].evidence_id, "predicate evidence superseded")
    current = engine.knowledge_applicability_current_report(check.applicability_id, current_target_fingerprint=selection.target_semantic_fingerprint)
    assert not current["current"]
    assert any("KNOWLEDGE_APPLICABILITY_EVIDENCE_STALE" in reason for reason in current["reasons"])
    with pytest.raises(PermissionError, match="APPLICABILITY_NOT_CURRENT"):
        engine.record_knowledge_application(authorized, current_target_fingerprint=selection.target_semantic_fingerprint, application_evidence_ids=(rows["application"].evidence_id,), applied_by="planner-a")


def test_cross_run_adapter_never_transfers_source_authority():
    engine = _engine()
    rows = _support(engine)
    envelope = CrossRunKnowledgeEnvelope(
        "source-run-a",
        "source-machine-a",
        "source-scope",
        "PROCEDURAL",
        {"rule": "reuse prior route ordering"},
        source_evidence_ids=("foreign-evidence-1",),
        source_authority_provenance={"authority": "foreign-controller"},
        applicability_scope_ids=("root",),
        created_at=10.0,
    )
    item = knowledge_item_from_cross_run_envelope(envelope, receiving_evidence_ids=(rows["cross-run"].evidence_id,))
    assert item.identity_payload()["source_authority_transfer"] == "NEVER"
    assert item.metadata["foreign_source_authority_provenance"]["authority"] == "foreign-controller"
    engine.record_knowledge_item(item)
    selection = KnowledgeSelection(item.knowledge_id, item.fingerprint, "root", _sha("cross-run-target"), "foreign knowledge retrieved as a candidate", "retriever-cross-run", (rows["selection"].evidence_id,))
    engine.record_knowledge_selection(selection)
    certificate = CrossRunAdmissionCertificate(envelope.envelope_id, envelope.fingerprint, "receiving-run-a", "root", "aasm.cross-run.validator", "0.1.0", {"all_receiving_checks": True}, (), True)
    check = applicability_check_from_cross_run_certificate(item, selection, certificate.to_dict(), evidence_ids=(rows["predicate-a"].evidence_id,), assessed_at=20.0)
    engine.record_applicability_check(check)
    assert not any(event.event_type == "authorized" for event in engine.events)
    authorized = engine.authorize_knowledge_application(check.applicability_id, current_target_fingerprint=selection.target_semantic_fingerprint, application_kind="PLANNING_GUIDANCE")
    assert authorized.authority != "foreign-controller"


def test_reassessment_requires_invalidation_of_prior_applicability_evidence():
    engine = _engine()
    rows = _support(engine)
    item, _, selection, _, check, check_row = _record_chain(engine, rows)
    replacement = ApplicabilityCheck(
        item.knowledge_id,
        item.fingerprint,
        selection.selection_id,
        selection.fingerprint,
        selection.target_scope_id,
        selection.target_semantic_fingerprint,
        (
            ApplicabilityPredicateResult(item.applicability_predicates[0], "FAIL", "environment drift observed", (rows["predicate-a"].evidence_id,)),
            ApplicabilityPredicateResult(item.applicability_predicates[1], "PASS", "semantic structure remains compatible", (rows["predicate-b"].evidence_id,)),
        ),
        "applicability-verifier-b",
        200.0,
        item.invalidation_triggers,
    )
    with pytest.raises(ValueError, match="ACTIVE_SELECTION_CONFLICT"):
        engine.record_applicability_check(replacement)
    engine.invalidate_evidence(check_row["evidence_id"], "reassessment required")
    recorded = engine.record_applicability_check(replacement)
    assert recorded["applicability"]["status"] == "INAPPLICABLE"
    projection = engine.knowledge_applicability_history_report()
    assert projection["applicability_checks"][check.applicability_id]["active"] is False
    assert projection["applicability_checks"][replacement.applicability_id]["active"] is True
