from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import hashlib
from importlib.resources import files
import json
from pathlib import Path
from typing import Any

from .calculus import (
    ConflictRecord,
    DecisionRecord,
    ExplanationRecord,
    FairnessPolicy,
    LockRecord,
    ObligationRecord,
)
from .evidence import EvidenceRecord
from .graph import PlanEdge, PlanNode
from .model import MachineState, ProblemSpec
from .profile_packages import canonical_hash
from .research_profile import research_package, research_profile
from .runtime_v25 import AASMEngine
from .semantic_result import ProducerRef, SemanticResultEnvelope

CORPUS_ID = "aasm-research-corpus-v1"
REFERENCE_RESULT_ID = "result-aasm-research-synthesis-v1"


@dataclass
class ResearchDemoResult:
    engine: AASMEngine
    summary: dict[str, Any]
    artifact: dict[str, Any] | None = None
    output_files: dict[str, str] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "machine_id": self.engine.snapshot.machine_id,
            "summary": deepcopy(self.summary),
            "artifact": deepcopy(self.artifact),
            "output_files": deepcopy(self.output_files or {}),
        }


def _data_root():
    return files("aasm").joinpath("reference_data", "research")


def _read_json(name: str) -> dict[str, Any]:
    return json.loads(_data_root().joinpath(name).read_text(encoding="utf-8"))


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify_research_corpus() -> dict[str, Any]:
    """Verify every packaged research fixture against the source manifest."""

    manifest = _read_json("manifest.json")
    errors: list[str] = []
    verified: list[dict[str, Any]] = []
    if manifest.get("corpus_id") != CORPUS_ID:
        errors.append(
            f"unexpected corpus_id {manifest.get('corpus_id')!r}; expected {CORPUS_ID!r}"
        )
    if manifest.get("network_required") is not False:
        errors.append("reference corpus must not require network access")
    if manifest.get("model_key_required") is not False:
        errors.append("reference corpus must not require a model key")
    if manifest.get("synthetic") is not True:
        errors.append("reference corpus must remain explicitly synthetic")

    for row in manifest.get("files", []):
        name = str(row.get("path") or "")
        expected = str(row.get("sha256") or "")
        if not name or not expected:
            errors.append(f"invalid manifest file record: {row!r}")
            continue
        target = _data_root().joinpath(name)
        try:
            data = target.read_bytes()
        except FileNotFoundError:
            errors.append(f"missing corpus file: {name}")
            continue
        actual = _sha256(data)
        verified.append(
            {
                "path": name,
                "expected_sha256": expected,
                "actual_sha256": actual,
                "valid": actual == expected,
            }
        )
        if actual != expected:
            errors.append(f"corpus digest mismatch for {name}: {actual} != {expected}")

    return {
        "valid": not errors,
        "errors": errors,
        "corpus_id": manifest.get("corpus_id"),
        "manifest_sha256": _sha256(
            _data_root().joinpath("manifest.json").read_bytes()
        ),
        "verified_files": verified,
        "manifest": manifest,
    }


def load_research_corpus() -> dict[str, Any]:
    verification = verify_research_corpus()
    if not verification["valid"]:
        raise ValueError("invalid packaged research corpus: " + "; ".join(verification["errors"]))
    return {
        "manifest": verification["manifest"],
        "verification": verification,
        "question": _read_json("question.json"),
        "studies": {
            "alpha": _read_json("study_alpha.json"),
            "beta": _read_json("study_beta.json"),
            "gamma": _read_json("study_gamma.json"),
            "delta": _read_json("study_delta.json"),
        },
        "expected_synthesis": _read_json("expected_synthesis.json"),
    }


def _transition(engine: AASMEngine, target: MachineState, reason: str) -> None:
    if engine.state_value == target.value:
        return
    engine.transition(target, reason)


def _register_plan(engine: AASMEngine) -> None:
    nodes = [
        PlanNode(
            "source-alpha",
            "source_review",
            {"source": "study_alpha.json"},
            metadata={"corpus_id": CORPUS_ID},
        ),
        PlanNode(
            "source-beta",
            "source_review",
            {"source": "study_beta.json"},
            metadata={"corpus_id": CORPUS_ID},
        ),
        PlanNode(
            "source-gamma",
            "source_review",
            {"source": "study_gamma.json"},
            metadata={"corpus_id": CORPUS_ID},
        ),
        PlanNode(
            "resolve-contradiction",
            "contradiction_resolution",
            {"question": "Does one retrieval-only model explain all populations?"},
            metadata={"corpus_id": CORPUS_ID},
        ),
        PlanNode(
            "source-delta",
            "source_review",
            {"source": "study_delta.json"},
            metadata={"corpus_id": CORPUS_ID},
        ),
        PlanNode(
            "synthesize-report",
            "artifact",
            {"artifact": "final_synthesis.json"},
            metadata={"corpus_id": CORPUS_ID},
        ),
    ]
    for node in nodes:
        engine.plan_add_node(node)
    for edge in [
        PlanEdge("source-alpha", "resolve-contradiction"),
        PlanEdge("source-beta", "resolve-contradiction"),
        PlanEdge("source-gamma", "resolve-contradiction"),
        PlanEdge("resolve-contradiction", "source-delta"),
        PlanEdge("source-delta", "synthesize-report"),
    ]:
        engine.plan_add_edge(edge)


def _record_corpus_evidence(
    engine: AASMEngine,
    corpus: dict[str, Any],
) -> dict[str, str]:
    manifest = corpus["manifest"]
    verification = corpus["verification"]
    question = corpus["question"]
    studies = corpus["studies"]

    corpus_record = engine.add_evidence(
        EvidenceRecord(
            "observation",
            "The packaged synthetic research corpus passed its recorded SHA-256 manifest.",
            source="aasm.reference-data",
            confidence=1.0,
            evidence_id="E-corpus-verified",
            metadata={
                "evidence_type": "provenance_check",
                "corpus_id": manifest["corpus_id"],
                "manifest_sha256": verification["manifest_sha256"],
                "network_required": manifest["network_required"],
                "model_key_required": manifest["model_key_required"],
                "verified_files": verification["verified_files"],
            },
        ),
        reason="research corpus provenance verified",
    )
    question_record = engine.add_evidence(
        EvidenceRecord(
            "claim",
            question["question"],
            source="question.json",
            confidence=1.0,
            derived_from=[corpus_record.evidence_id],
            evidence_id="E-question",
            metadata={
                "evidence_type": "study_claim",
                "question_id": question["question_id"],
            },
        ),
        reason="research question recorded",
    )
    alpha = studies["alpha"]
    alpha_record = engine.add_evidence(
        EvidenceRecord(
            "observation",
            (
                "Alpha reports an 11.8-point delayed-retention benefit in novice "
                "learners under exposure-matched randomized conditions."
            ),
            source="study_alpha.json",
            confidence=1.0,
            supports=[question_record.evidence_id],
            derived_from=[corpus_record.evidence_id],
            evidence_id="E-alpha-result",
            metadata={
                "evidence_type": "study_result",
                "study": alpha,
                "plan_node_id": "source-alpha",
            },
        ),
        reason="alpha study result extracted",
    )
    beta = studies["beta"]
    beta_record = engine.add_evidence(
        EvidenceRecord(
            "observation",
            (
                "Beta reports a 10.6-point aggregate benefit, but the retrieval arm "
                "received 31 percent more study time and different feedback."
            ),
            source="study_beta.json",
            confidence=1.0,
            derived_from=[corpus_record.evidence_id],
            evidence_id="E-beta-method",
            metadata={
                "evidence_type": "study_method",
                "study": beta,
                "exposure_confounded": True,
                "plan_node_id": "source-beta",
            },
        ),
        reason="beta study method extracted",
    )
    gamma = studies["gamma"]
    gamma_record = engine.add_evidence(
        EvidenceRecord(
            "contradiction",
            (
                "Gamma's exposure-matched experienced-learner replication reports "
                "a 1.1-point effect with a confidence interval spanning zero, "
                "contradicting a universal retrieval-only model."
            ),
            source="study_gamma.json",
            confidence=1.0,
            contradicts=[question_record.evidence_id],
            derived_from=[corpus_record.evidence_id],
            evidence_id="E-gamma-result",
            metadata={
                "evidence_type": "contradiction",
                "study": gamma,
                "plan_node_id": "source-gamma",
            },
        ),
        reason="gamma contradiction recorded",
    )
    return {
        "corpus": corpus_record.evidence_id,
        "question": question_record.evidence_id,
        "alpha": alpha_record.evidence_id,
        "beta": beta_record.evidence_id,
        "gamma": gamma_record.evidence_id,
    }


def _register_decisions(
    engine: AASMEngine,
    evidence: dict[str, str],
) -> None:
    engine.register_decision(
        DecisionRecord(
            "D-question",
            "research.question",
            "retrieval-causal-question",
            kind="ROOT",
            evidence_ids=[evidence["question"]],
            pinned=True,
        )
    )
    engine.activate_decision("D-question")
    engine.register_decision(
        DecisionRecord(
            "D-corpus",
            "research.corpus",
            CORPUS_ID,
            kind="PINNED",
            parent_ids=["D-question"],
            evidence_ids=[evidence["corpus"]],
        )
    )
    engine.activate_decision("D-corpus")
    engine.register_decision(
        DecisionRecord(
            "D-model-retrieval-only",
            "synthesis.causal_model",
            "retrieval_only",
            kind="EXPLICIT",
            parent_ids=["D-question"],
            evidence_ids=[evidence["alpha"]],
            plan_node_ids=["resolve-contradiction"],
        )
    )
    engine.activate_decision("D-model-retrieval-only")
    engine.register_decision(
        DecisionRecord(
            "D-report-json",
            "report.format",
            "structured_json",
            kind="EXPLICIT",
            parent_ids=["D-question"],
            plan_node_ids=["synthesize-report"],
        )
    )
    engine.activate_decision("D-report-json")
    engine.register_decision(
        DecisionRecord(
            "D-subgroup-off",
            "synthesis.prior_knowledge_subgroup",
            False,
            kind="EXPLICIT",
            parent_ids=["D-question"],
            plan_node_ids=["source-delta"],
        )
    )
    engine.activate_decision("D-subgroup-off")


def _register_obligations(
    engine: AASMEngine,
    evidence: dict[str, str],
) -> None:
    obligations = [
        ObligationRecord(
            "O-corpus",
            "Verify the fixed corpus manifest before using any source.",
            required_evidence_types=["provenance_check"],
            evidence_ids=[evidence["corpus"]],
            plan_node_ids=["source-alpha"],
        ),
        ObligationRecord(
            "O-alpha",
            "Extract the matched-exposure novice result from Alpha.",
            required_evidence_types=["study_result"],
            evidence_ids=[evidence["alpha"]],
            plan_node_ids=["source-alpha"],
        ),
        ObligationRecord(
            "O-beta",
            "Assess whether Beta is confounded by unequal exposure time.",
            required_evidence_types=["study_method"],
            evidence_ids=[evidence["beta"]],
            plan_node_ids=["source-beta"],
        ),
        ObligationRecord(
            "O-gamma",
            "Evaluate the matched-exposure contradiction from Gamma.",
            required_evidence_types=["contradiction"],
            evidence_ids=[evidence["gamma"]],
            plan_node_ids=["source-gamma"],
        ),
        ObligationRecord(
            "O-resolve",
            "Resolve the population-level contradiction before committing a causal claim.",
            dependencies=["O-alpha", "O-beta", "O-gamma"],
            required_evidence_types=["contradiction", "resolution"],
            plan_node_ids=["resolve-contradiction"],
        ),
        ObligationRecord(
            "O-subgroup",
            "Analyze prior knowledge as an effect modifier when required.",
            activation_condition={
                "decision": {
                    "subject": "synthesis.prior_knowledge_subgroup",
                    "op": "EQ",
                    "value": True,
                }
            },
            dependencies=["O-resolve"],
            decision_dependencies=["D-subgroup-off"],
            required_evidence_types=["study_result"],
            plan_node_ids=["source-delta"],
        ),
        ObligationRecord(
            "O-steering",
            "Honor the mid-run requirement to report population limits explicitly.",
            activation_condition={
                "decision": {
                    "subject": "synthesis.prior_knowledge_subgroup",
                    "op": "EQ",
                    "value": True,
                }
            },
            dependencies=["O-resolve"],
            required_evidence_types=["resolution"],
            plan_node_ids=["source-delta"],
        ),
        ObligationRecord(
            "O-provenance",
            "Audit claim-level provenance for the final synthesis.",
            dependencies=["O-subgroup", "O-steering"],
            required_evidence_types=["provenance_check"],
            plan_node_ids=["synthesize-report"],
        ),
        ObligationRecord(
            "O-artifact",
            "Produce the final structured synthesis artifact.",
            dependencies=["O-provenance"],
            required_evidence_types=["resolution", "provenance_check"],
            plan_node_ids=["synthesize-report"],
        ),
    ]
    for obligation in obligations:
        engine.register_obligation(obligation)

    for obligation_id in ["O-corpus", "O-alpha", "O-beta", "O-gamma"]:
        engine.enable_obligation(obligation_id)
        engine.set_obligation_status(obligation_id, "IN_PROGRESS")
        engine.set_obligation_status(obligation_id, "VERIFYING")
        engine.set_obligation_status(
            obligation_id,
            "VERIFIED",
            evidence_ids=engine.calculus_report()["obligations"][obligation_id][
                "evidence_ids"
            ],
        )
        engine.set_obligation_status(
            obligation_id,
            "COMMITTED",
            evidence_ids=engine.calculus_report()["obligations"][obligation_id][
                "evidence_ids"
            ],
        )

    engine.lock_obligation(
        LockRecord(
            "L-subgroup-off",
            "O-subgroup",
            {
                "decision": {
                    "subject": "synthesis.prior_knowledge_subgroup",
                    "op": "EQ",
                    "value": False,
                }
            },
            "Prior-knowledge subgroup work is inactive under the initial model.",
            "D-subgroup-off",
            evidence_ids=[evidence["alpha"]],
        )
    )


def _raise_and_learn_conflict(
    engine: AASMEngine,
    evidence: dict[str, str],
) -> dict[str, Any]:
    engine.enable_obligation("O-resolve")
    engine.set_obligation_status("O-resolve", "IN_PROGRESS")
    engine.set_obligation_status("O-resolve", "VERIFYING")
    engine.raise_conflict(
        ConflictRecord(
            "C-retrieval-only",
            "ASSUMPTION_CONFLICT",
            [evidence["alpha"], evidence["gamma"]],
            observed_at_obligation_id="O-resolve",
            implicated_decision_ids=["D-model-retrieval-only"],
            scope={"question_id": "retrieval-causal-question"},
        ),
        reason="matched-exposure contradiction invalidated the retrieval-only model",
    )
    engine.register_explanation(
        ExplanationRecord(
            "X-retrieval-only",
            "C-retrieval-only",
            [
                {
                    "subject": "synthesis.causal_model",
                    "op": "EQ",
                    "value": "retrieval_only",
                    "decision_id": "D-model-retrieval-only",
                }
            ],
            [evidence["alpha"], evidence["gamma"]],
            method="REPRODUCTION",
            status="VALIDATED",
            minimality="IRREDUCIBLE",
            certificate={
                "type": "fixed-corpus-reproduction",
                "corpus_id": CORPUS_ID,
                "sources": ["study_alpha.json", "study_gamma.json"],
            },
            scope={"question_id": "retrieval-causal-question"},
        ),
        reason="causal explanation linked to the retrieval-only decision",
    )
    learned = engine.learn_constraint(
        "X-retrieval-only",
        "LC-retrieval-only",
        strength="HARD",
        reason="retrieval-only no-good proposed under strict assurance",
    )
    if learned.get("strength") != "SOFT":
        raise AssertionError("strict assurance must stage learned knowledge as SOFT")
    engine.register_projection_certificate(
        "LC-retrieval-only",
        certificate_id="CERT-retrieval-only",
    )
    verification = engine.verify_projection_certificate("CERT-retrieval-only")
    if verification.get("valid") is not True:
        raise AssertionError("reference projection certificate must verify")
    hard = engine.promote_constraint_hard(
        "LC-retrieval-only",
        "CERT-retrieval-only",
    )
    return {"learned": learned, "hard": hard, "verification": verification}


def _backjump_and_steer(
    engine: AASMEngine,
    corpus: dict[str, Any],
) -> dict[str, Any]:
    before = engine.calculus_report()
    report_decision_before = before["decisions"]["D-report-json"]["status"]
    backjump = engine.backjump_conflict(
        "C-retrieval-only",
        explanation_id="X-retrieval-only",
        reason="causal backjump removed the contradicted retrieval-only model",
    )
    after = engine.calculus_report()
    if after["decisions"]["D-report-json"]["status"] != report_decision_before:
        raise AssertionError("unrelated report-format work was not preserved")
    repeat_blocked = False
    engine.register_decision(
        DecisionRecord(
            "D-model-retrieval-only-repeat",
            "synthesis.causal_model",
            "retrieval_only",
            parent_ids=["D-question"],
            plan_node_ids=["resolve-contradiction"],
        )
    )
    try:
        engine.activate_decision("D-model-retrieval-only-repeat")
    except ValueError as exc:
        if "hard constraints" not in str(exc):
            raise
        repeat_blocked = True
    if not repeat_blocked:
        raise AssertionError("learned no-good failed to block repeated retrieval-only model")

    steering = engine.user_interrupt(
        "Also report whether prior knowledge changes the effect.",
        metadata={
            "seed_nodes": ["source-delta"],
            "source": "reference-user",
            "requirement_id": "R-prior-knowledge",
        },
    )
    engine.register_decision(
        DecisionRecord(
            "D-subgroup-on",
            "synthesis.prior_knowledge_subgroup",
            True,
            parent_ids=["D-question"],
            plan_node_ids=["source-delta"],
        )
    )
    subgroup_activation = engine.activate_decision(
        "D-subgroup-on",
        supersede_decision_id="D-subgroup-off",
        reason="mid-run requirement activated prior-knowledge subgroup analysis",
    )
    delta = corpus["studies"]["delta"]
    delta_record = engine.add_evidence(
        EvidenceRecord(
            "observation",
            (
                "Delta reports a prespecified prior-knowledge interaction: a 9.4-point "
                "effect in novices and a 0.9-point effect in experienced learners."
            ),
            source="study_delta.json",
            confidence=1.0,
            supports=["E-alpha-result", "E-gamma-result"],
            derived_from=["E-corpus-verified"],
            evidence_id="E-delta-result",
            metadata={
                "evidence_type": "study_result",
                "study": delta,
                "plan_node_id": "source-delta",
                "requirement_id": "R-prior-knowledge",
            },
        ),
        reason="delta subgroup result extracted",
    )
    resolution = engine.add_evidence(
        EvidenceRecord(
            "claim",
            (
                "Prior knowledge modifies the retrieval-practice effect; matched-exposure "
                "benefit is supported for novices but not established for experienced learners."
            ),
            source="aasm.reference-synthesis",
            confidence=1.0,
            supports=["E-question"],
            derived_from=[
                "E-alpha-result",
                "E-beta-method",
                "E-gamma-result",
                delta_record.evidence_id,
            ],
            evidence_id="E-resolution",
            metadata={
                "evidence_type": "resolution",
                "active_model": "effect_modified_by_prior_knowledge",
                "rejected_model": "retrieval_only",
                "constraint_id": "LC-retrieval-only",
            },
        ),
        reason="research contradiction resolved",
    )
    engine.register_decision(
        DecisionRecord(
            "D-model-effect-modified",
            "synthesis.causal_model",
            "effect_modified_by_prior_knowledge",
            parent_ids=["D-question", "D-subgroup-on"],
            evidence_ids=[resolution.evidence_id],
            antecedent_constraint_ids=["LC-retrieval-only"],
            plan_node_ids=["resolve-contradiction", "source-delta"],
        )
    )
    engine.activate_decision(
        "D-model-effect-modified",
        reason="corrected causal model activated",
    )
    return {
        "backjump": backjump,
        "repeat_blocked": repeat_blocked,
        "steering": steering,
        "subgroup_activation": subgroup_activation,
        "resolution_evidence_id": resolution.evidence_id,
        "delta_evidence_id": delta_record.evidence_id,
    }


def _complete_obligation(
    engine: AASMEngine,
    obligation_id: str,
    evidence_ids: list[str],
) -> None:
    current = engine.calculus_report()["obligations"][obligation_id]["status"]
    if current in {"AVAILABLE", "BLOCKED", "NEEDS_REVALIDATION"}:
        engine.enable_obligation(obligation_id)
        current = "ENABLED"
    if current == "ENABLED":
        engine.set_obligation_status(obligation_id, "IN_PROGRESS")
        current = "IN_PROGRESS"
    if current == "IN_PROGRESS":
        engine.set_obligation_status(obligation_id, "VERIFYING")
        current = "VERIFYING"
    if current == "VERIFYING":
        engine.set_obligation_status(
            obligation_id,
            "VERIFIED",
            evidence_ids=evidence_ids,
        )
        current = "VERIFIED"
    if current == "VERIFIED":
        engine.set_obligation_status(
            obligation_id,
            "COMMITTED",
            evidence_ids=evidence_ids,
        )


def _finish_reference_run(
    engine: AASMEngine,
    corpus: dict[str, Any],
    recovery: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    resolution_id = recovery["resolution_evidence_id"]
    delta_id = recovery["delta_evidence_id"]
    _complete_obligation(
        engine,
        "O-resolve",
        ["E-gamma-result", resolution_id],
    )
    _complete_obligation(engine, "O-subgroup", [delta_id])
    _complete_obligation(engine, "O-steering", [resolution_id])

    provenance = engine.add_evidence(
        EvidenceRecord(
            "observation",
            "Every final claim is linked to active packaged evidence and the resolved causal model.",
            source="aasm.reference-synthesis",
            confidence=1.0,
            derived_from=[
                "E-corpus-verified",
                "E-alpha-result",
                "E-beta-method",
                "E-gamma-result",
                delta_id,
                resolution_id,
            ],
            evidence_id="E-final-provenance",
            metadata={
                "evidence_type": "provenance_check",
                "question_id": "retrieval-causal-question",
                "constraint_id": "LC-retrieval-only",
                "certificate_id": "CERT-retrieval-only",
            },
        ),
        reason="final claim-level provenance verified",
    )
    _complete_obligation(engine, "O-provenance", [provenance.evidence_id])

    expected = corpus["expected_synthesis"]
    calculus = engine.calculus_report()
    artifact = {
        "artifact_id": expected["artifact_id"],
        "schema_version": 1,
        "synthetic": True,
        "corpus_id": CORPUS_ID,
        "question": corpus["question"]["question"],
        "conclusion": expected["conclusion"],
        "active_causal_model": calculus["active_values"]["synthesis.causal_model"],
        "rejected_model": expected["rejected_model"],
        "population_limits": {
            "novice": "matched-exposure benefit supported",
            "experienced": "benefit not established by the fixed corpus",
            "mixed_population": "aggregate estimate can be distorted by exposure imbalance and effect modification",
        },
        "claim_provenance": {
            "matched_exposure_novice_benefit": ["E-alpha-result", "E-delta-result"],
            "unequal_exposure_confounds_aggregate_effect": ["E-beta-method"],
            "experienced_population_contradiction": ["E-gamma-result", "E-delta-result"],
            "effect_modification_resolution": ["E-resolution"],
        },
        "machine_provenance": {
            "machine_id": engine.snapshot.machine_id,
            "profile_id": "aasm.research-synthesis",
            "profile_version": "1.0.0",
            "constraint_id": "LC-retrieval-only",
            "certificate_id": "CERT-retrieval-only",
            "conflict_id": "C-retrieval-only",
            "explanation_id": "X-retrieval-only",
            "backjump_target": recovery["backjump"]["backjump"]["pivot_decision_id"],
            "steering_requirement_id": "R-prior-knowledge",
            "event_sequence_before_artifact": engine.current_sequence(),
        },
    }
    artifact["sha256"] = canonical_hash(artifact)
    final_result = engine.record_semantic_result(
        SemanticResultEnvelope(
            REFERENCE_RESULT_ID,
            ProducerRef(
                "tool",
                "aasm.reference-synthesis",
                version="1.0.0",
                authority="DETERMINISTIC_FIXTURE",
            ),
            [
                "retrieval-causal-question",
                "C-retrieval-only",
                "LC-retrieval-only",
            ],
            "PASS",
            "The fixed corpus was synthesized after a learned no-good and causal backjump.",
            claims=[
                {
                    "claim": artifact["conclusion"],
                    "evidence_ids": sorted(
                        set(
                            evidence_id
                            for ids in artifact["claim_provenance"].values()
                            for evidence_id in ids
                        )
                    ),
                }
            ],
            observations=[
                {
                    "repeat_blocked": recovery["repeat_blocked"],
                    "unrelated_report_decision_preserved": (
                        engine.calculus_report()["decisions"]["D-report-json"]["status"]
                        == "ACTIVE"
                    ),
                    "steering_affected_nodes": recovery["steering"]["impact"][
                        "affected_nodes"
                    ],
                    "steering_preserved_nodes": recovery["steering"]["impact"][
                        "unaffected_nodes"
                    ],
                }
            ],
            evidence=[
                {"evidence_id": evidence_id}
                for evidence_id in expected["required_evidence_ids"]
            ],
            artifacts=[
                {
                    "artifact_id": artifact["artifact_id"],
                    "sha256": artifact["sha256"],
                    "kind": "synthesis_report",
                }
            ],
            confidence=1.0,
            scope={"corpus_id": CORPUS_ID},
            metadata={"offline": True, "synthetic": True},
        ),
        reason="known-good research synthesis semantic result recorded",
    )
    _complete_obligation(
        engine,
        "O-artifact",
        [resolution_id, provenance.evidence_id],
    )

    for node_id in [
        "source-alpha",
        "source-beta",
        "source-gamma",
        "resolve-contradiction",
        "source-delta",
        "synthesize-report",
    ]:
        engine.plan_update_node(
            node_id,
            {"status": "complete", "owner": "aasm.reference-synthesis"},
            reason="research synthesis plan node completed",
        )
        if node_id not in engine.snapshot.visited:
            engine.plan_mark_visited(node_id)

    _transition(engine, MachineState.OBSERVE, "reference synthesis executed")
    _transition(engine, MachineState.VERIFY, "reference synthesis evidence observed")
    _transition(engine, MachineState.COMPLETE, "known-good reference synthesis verified")

    history = engine.check_durable_history(persist=True)
    if not history["valid"]:
        raise AssertionError(f"reference history verification failed: {history['issues']}")
    replayed = engine.replay()
    if replayed.canonical_hash() != engine.snapshot.canonical_hash():
        raise AssertionError("full replay did not reconstruct the final snapshot")
    if artifact["active_causal_model"] != expected["active_causal_model"]:
        raise AssertionError("final causal model differs from expected synthesis")
    if artifact["conclusion"] != expected["conclusion"]:
        raise AssertionError("final conclusion differs from expected synthesis")

    return artifact, {"semantic_result": final_result, "history_check": history}


def _write_outputs(
    output_dir: str | Path,
    engine: AASMEngine,
    summary: dict[str, Any],
    artifact: dict[str, Any] | None,
) -> dict[str, str]:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    paths: dict[str, str] = {}
    values = {
        "run_summary.json": summary,
        "machine_export.json": engine.export(),
    }
    if artifact is not None:
        values["final_synthesis.json"] = artifact
        checks = engine.assurance_report()
        history_rows = checks.get("history_checks") or []
        values["history_check.json"] = history_rows[-1] if history_rows else checks
    for name, value in values.items():
        path = root / name
        path.write_text(
            json.dumps(value, indent=2, sort_keys=True, default=str) + "\n",
            encoding="utf-8",
        )
        paths[name] = str(path)
    machine_id_path = root / "machine_id.txt"
    machine_id_path.write_text(engine.snapshot.machine_id + "\n", encoding="utf-8")
    paths["machine_id.txt"] = str(machine_id_path)
    commands_path = root / "replay_commands.txt"
    commands_path.write_text(
        "\n".join(
            [
                f"aasm inspect {engine.snapshot.machine_id} --store YOUR_STORE --surface summary",
                f"aasm inspect {engine.snapshot.machine_id} --store YOUR_STORE --surface causal",
                f"aasm history-check {engine.snapshot.machine_id} --store YOUR_STORE --no-persist",
                f"aasm replay {engine.snapshot.machine_id} --store YOUR_STORE",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    paths["replay_commands.txt"] = str(commands_path)
    return paths


def run_research_synthesis_demo(
    *,
    store=None,
    mode: str = "complete",
    output_dir: str | Path | None = None,
    machine_id: str | None = None,
) -> ResearchDemoResult:
    """Run the canonical offline research-synthesis trajectory.

    ``mode='setup'`` creates the bound machine, fixed plan, initial model,
    obligations, evidence, and conditional lock without triggering the known
    contradiction. ``mode='complete'`` executes the complete deterministic
    conflict-learning, steering, backjump, replay, and artifact trajectory.
    """

    if mode not in {"setup", "complete"}:
        raise ValueError("research demo mode must be setup or complete")
    corpus = load_research_corpus()
    problem = ProblemSpec(
        corpus["question"]["question"],
        objective={
            "artifact": "structured causal synthesis",
            "known_good_fixture": True,
        },
        constraints=[
            {"offline": True},
            {"corpus_id": CORPUS_ID},
            {"claim_level_provenance": True},
        ],
        invariants=[
            {"no_unresolved_mandatory_obligations_at_completion": True},
            {"hard_knowledge_requires_certificate": True},
        ],
        acceptance_tests=[
            {"active_causal_model": "effect_modified_by_prior_knowledge"},
            {"learned_constraint": "LC-retrieval-only"},
            {"exact_replay": True},
        ],
        features={
            "dependency_graph": True,
            "branching_choices": True,
            "evidence_conflict": True,
            "offline_reference_application": True,
        },
    )
    engine = AASMEngine(problem, store=store, machine_id=machine_id)
    engine.bind_profile(
        research_profile(),
        package=research_package(),
        configuration={
            "corpus_id": CORPUS_ID,
            "offline": True,
            "mode": mode,
            "manifest_sha256": corpus["verification"]["manifest_sha256"],
        },
        actor="research-owner",
        reason="research synthesis hero profile bound",
    )
    engine.configure_calculus_fairness(
        FairnessPolicy(20, 20, 10, 5, "BLOCK_PLANNING", 1),
        reason="research synthesis fairness configured",
    )
    _transition(engine, MachineState.FORMALIZE, "research question formalized")
    _transition(engine, MachineState.CLASSIFY, "fixed corpus and causal question classified")
    engine.classify()
    _transition(engine, MachineState.PLAN, "research synthesis plan selected")
    _register_plan(engine)
    evidence = _record_corpus_evidence(engine, corpus)
    _register_decisions(engine, evidence)
    _register_obligations(engine, evidence)
    _transition(engine, MachineState.SELECT, "initial research model selected")

    setup_summary = {
        "runtime_version": "0.26.0",
        "scenario": "research-synthesis",
        "mode": mode,
        "machine_id": engine.snapshot.machine_id,
        "state": engine.state_value,
        "corpus_id": CORPUS_ID,
        "corpus_valid": corpus["verification"]["valid"],
        "profile": engine.profile_report(),
        "active_model": engine.calculus_report()["active_values"],
        "locked_obligations": sorted(
            obligation_id
            for obligation_id, row in engine.calculus_report()["obligations"].items()
            if row.get("status") == "LOCKED"
        ),
        "next": (
            "Run the completed reference trajectory to observe contradiction, "
            "learning, steering, causal backjump, and replay."
        ),
    }
    if mode == "setup":
        paths = (
            _write_outputs(output_dir, engine, setup_summary, None)
            if output_dir is not None
            else {}
        )
        return ResearchDemoResult(engine, setup_summary, output_files=paths)

    _transition(engine, MachineState.EXECUTE, "fixed research corpus processed")
    learned = _raise_and_learn_conflict(engine, evidence)
    recovery = _backjump_and_steer(engine, corpus)
    artifact, completion = _finish_reference_run(engine, corpus, recovery)
    final_calculus = engine.calculus_report()
    summary = {
        "runtime_version": "0.26.0",
        "scenario": "research-synthesis",
        "mode": mode,
        "machine_id": engine.snapshot.machine_id,
        "state": engine.state_value,
        "corpus_id": CORPUS_ID,
        "corpus_valid": corpus["verification"]["valid"],
        "profile_id": engine.profile_report()["binding"]["profile_id"],
        "active_model": final_calculus["active_values"],
        "conflict_id": "C-retrieval-only",
        "conflict_status": final_calculus["conflicts"]["C-retrieval-only"]["status"],
        "learned_constraint_id": "LC-retrieval-only",
        "learned_constraint_strength": final_calculus["constraints"]["LC-retrieval-only"]["strength"],
        "certificate_id": "CERT-retrieval-only",
        "certificate_verified": learned["verification"]["valid"],
        "backjump_target": recovery["backjump"]["backjump"]["pivot_decision_id"],
        "invalidated_decisions": recovery["backjump"]["backjump"]["invalidated_decision_ids"],
        "repeat_failed_model_blocked": recovery["repeat_blocked"],
        "unrelated_report_decision_preserved": (
            final_calculus["decisions"]["D-report-json"]["status"] == "ACTIVE"
        ),
        "steering_affected_nodes": recovery["steering"]["impact"]["affected_nodes"],
        "steering_preserved_nodes": recovery["steering"]["impact"]["unaffected_nodes"],
        "broken_lock_ids": recovery["subgroup_activation"]["broken_lock_ids"],
        "mandatory_obligations": {
            obligation_id: row["status"]
            for obligation_id, row in final_calculus["obligations"].items()
            if row.get("mandatory", True)
        },
        "history_check_valid": completion["history_check"]["valid"],
        "replay_snapshot_hash": completion["history_check"][
            "reconstructed_snapshot_hash"
        ],
        "persisted_snapshot_hash": completion["history_check"][
            "persisted_snapshot_hash"
        ],
        "artifact_id": artifact["artifact_id"],
        "artifact_sha256": artifact["sha256"],
        "event_count": len(engine.events),
    }
    paths = (
        _write_outputs(output_dir, engine, summary, artifact)
        if output_dir is not None
        else {}
    )
    return ResearchDemoResult(engine, summary, artifact, paths)
