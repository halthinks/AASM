from __future__ import annotations

from dataclasses import replace
from typing import Any

from . import certification as _base
from .advanced_optimization import default_advanced_providers, reference_advanced_problems
from .model import ProblemSpec
from .runtime_v47 import AASMEngine
from .sii import StructuredProposal
from .sii_governance import SIIPrincipalBinding, governed_sii_contract


CERTIFICATION_CONTRACT_ID = _base.CERTIFICATION_CONTRACT_ID
CERTIFICATION_CONTRACT_VERSION = "0.2.0"
CERTIFICATION_STATUSES = _base.CERTIFICATION_STATUSES
CERTIFICATION_TARGET_IDS = (
    "reference-domains",
    "solver-reuse",
    "truth-memory",
    "formal-verification",
    "sii-governance",
)
CERTIFICATION_TARGET_ALIASES = {"sii-preview": "sii-governance"}
CertificationCheck = _base.CertificationCheck
CertificationReport = _base.CertificationReport


def certification_contract() -> dict[str, Any]:
    contract = _base.certification_contract()
    contract.update({
        "contract_version": CERTIFICATION_CONTRACT_VERSION,
        "targets": list(CERTIFICATION_TARGET_IDS),
        "target_aliases": dict(CERTIFICATION_TARGET_ALIASES),
        "sii_graduation": "GOVERNED_V047_ENFORCEMENT_REQUIRED",
        "overall_status_includes": "GOVERNED_SII",
    })
    return contract


def _check(check_id: str, passed: bool, statement: str, *, evidence=(), detail=None):
    return CertificationCheck(check_id, "PASS" if passed else "FAIL", statement, tuple(evidence), dict(detail or {}))


def _governed_sii(target_id: str = "sii-governance") -> CertificationReport:
    engine = AASMEngine(ProblemSpec("v0.47 governed SII certification"))
    installed = engine.install_default_sii_scoring_policy(authority_id="policy", authority_class="POLICY")
    reasoner_binding = engine.bind_sii_principal(SIIPrincipalBinding("cert-reasoner", "PROPOSER", can_propose=True), authority_id="policy", authority_class="POLICY")
    meter_binding = engine.bind_sii_principal(SIIPrincipalBinding("cert-meter", "VERIFIER", can_measure=True), authority_id="policy", authority_class="POLICY")
    registered = engine.register_sii_proposer(principal_id="cert-reasoner", name="cert reasoner", kind="llm", provider="fixture", model_id="model-a")
    proposer_id = registered["identity"]["proposer_id"]
    checks = []

    contract = governed_sii_contract()
    checks.append(_check(
        "measurement-principal-authority-binding",
        contract["measurement_identity_binding"] == "RESOLVED_FROM_DURABLE_PRINCIPAL_BINDING",
        "measurement authority is resolved from a durable policy-admitted principal binding",
        evidence=(meter_binding["evidence_id"],),
    ))
    checks.append(_check(
        "versioned-scoring-policy-active",
        installed["policy"]["version"] == "1.0.0" and engine.sii_governance_report()["active_policy_id"] == installed["policy"]["policy_id"],
        "a versioned durable scoring policy is admitted and active before resource allocation",
        evidence=(installed["admission"]["evidence_id"], installed["activation"]["evidence_id"]),
    ))

    proposal = StructuredProposal(proposer_id, "candidate", "root", {"strategy": "reuse-first"}, .7)
    submitted = engine.submit_sii_proposal(proposal)
    try:
        engine.measure_sii_outcome(proposal.proposal_id, measured_by_principal_id="forged-meter", disposition="INCONCLUSIVE", verification_verdict="INCONCLUSIVE")
        forged_meter_rejected = False
    except KeyError:
        forged_meter_rejected = True
    checks.append(_check(
        "caller-authority-spoof-rejected",
        forged_meter_rejected,
        "an unbound caller cannot self-assert VERIFIER/POLICY/CONTROLLER measurement authority",
        evidence=(submitted["proposal_evidence_id"],),
    ))
    measured = engine.measure_sii_outcome(proposal.proposal_id, measured_by_principal_id="cert-meter", disposition="INCONCLUSIVE", verification_verdict="INCONCLUSIVE")
    resource = measured["resource_lease"]
    checks.append(_check(
        "resource-lease-never-grants-authority",
        resource["authority_class"] == "PROPOSER" and resource["direct_truth_promotion"] is False and resource["direct_state_mutation"] is False and resource["self_verification"] is False,
        "governed resource utility never grants epistemic/state authority",
        evidence=(measured["outcome_evidence_id"],),
    ))

    engine.install_default_advanced_optimization_capabilities(authority_id="policy", authority_class="POLICY")
    for provider in default_advanced_providers():
        engine.register_advanced_optimization_provider_runtime(provider, authority_id="policy", authority_class="POLICY")
    oversized = replace(reference_advanced_problems()["INCREMENTAL_SAT"], conflict_budget=999_999, decision_budget=999_999)
    requested = engine.request_sii_advanced_optimization(proposer_id, oversized, timeout_ms=999_999)
    effective = requested["effective_problem"]
    queued = next(row for row in engine.snapshot.resources["tasks"] if row["task_id"] == requested["task"]["task_id"])
    checks.append(_check(
        "resource-lease-native-solver-enforcement",
        effective["conflict_budget"] == 10_000 and effective["decision_budget"] == 20_000 and requested["request"]["timeout_ms"] == 15_000,
        "tier-one SII limits are compiled into native incremental-SAT conflict/decision/time budgets",
        evidence=(requested["resource_lease_evidence_id"], requested["enforcement_evidence_id"]),
        detail={"effective_problem": effective, "timeout_ms": requested["request"]["timeout_ms"]},
    ))
    checks.append(_check(
        "resource-lease-scheduler-enforcement",
        queued["priority"] == 40 and queued["metadata"]["sii_resource_lease_id"] == requested["resource_lease"]["lease_id"] and queued["metadata"]["authority_reward"] == "NEVER",
        "SII scheduler priority and lease provenance are attached to the ordinary AASM TaskDemand/TaskLease path",
        evidence=(requested["enforcement_evidence_id"],),
    ))
    checks.append(_check(
        "mandatory-verification-not-reduced",
        contract["mandatory_verification"] == "NEVER_REDUCED_BY_SII",
        "SII cannot remove or cap verification already required by AASM policy; discretionary formal work is a separate path",
    ))
    checks.append(_check(
        "replay-preserves-governed-sii",
        engine.replay().canonical_hash() == engine.snapshot.canonical_hash(),
        "governed principal/policy/lease/enforcement records preserve exact event-sourced replay",
        evidence=(reasoner_binding["evidence_id"], meter_binding["evidence_id"]),
    ))

    return CertificationReport(
        target_id,
        tuple(checks),
        scope="GOVERNED_V047_SII_GRADUATION",
        notes=(
            "This certifies deterministic AASM governance/enforcement behavior, not arbitrary external answer quality.",
            "The historical sii-preview target is retained as an alias to this governed graduation check.",
        ),
    )


def _base_target(target_id: str) -> CertificationReport:
    report = _base.run_certification(target_id)["targets"][0]
    checks = tuple(CertificationCheck(**row) for row in report["checks"])
    return CertificationReport(report["target_id"], checks, scope=report.get("scope", "DETERMINISTIC_AASM_CONTRACT_BEHAVIOR"), notes=tuple(report.get("notes") or ()))


def run_certification(target_id: str | None = None) -> dict[str, Any]:
    resolved = CERTIFICATION_TARGET_ALIASES.get(target_id, target_id) if target_id is not None else None
    if resolved is not None and resolved not in CERTIFICATION_TARGET_IDS:
        raise ValueError(f"unknown certification target: {target_id}")
    selected = [resolved] if resolved else list(CERTIFICATION_TARGET_IDS)
    reports = []
    for name in selected:
        report = _governed_sii(target_id or name) if name == "sii-governance" else _base_target(name)
        reports.append(report.to_dict())
    status_counts = {status: sum(1 for report in reports if report["status"] == status) for status in CERTIFICATION_STATUSES}
    overall_status = "FAIL" if status_counts["FAIL"] else ("INCONCLUSIVE" if status_counts["INCONCLUSIVE"] else "PASS")
    core_reports = [report for report in reports if report["target_id"] not in {"sii-governance", "sii-preview"}]
    core_status = "PASS"
    if any(report["status"] == "FAIL" for report in core_reports): core_status = "FAIL"
    elif any(report["status"] == "INCONCLUSIVE" for report in core_reports): core_status = "INCONCLUSIVE"
    return {
        "contract": certification_contract(),
        "status": overall_status,
        "core_status": core_status,
        "status_counts": status_counts,
        "target_count": len(reports),
        "targets": reports,
        "interpretation": {
            "core_status": "certification status excluding governed SII",
            "status": "combined status including governed SII graduation",
        },
    }


__all__ = [
    "CERTIFICATION_CONTRACT_ID", "CERTIFICATION_CONTRACT_VERSION", "CERTIFICATION_STATUSES",
    "CERTIFICATION_TARGET_IDS", "CERTIFICATION_TARGET_ALIASES", "CertificationCheck", "CertificationReport",
    "certification_contract", "run_certification",
]
