from __future__ import annotations

"""AASM v0.43 semantic conformance and adversarial certification harness.

Certification here is deliberately narrower than theorem proving or a claim
that arbitrary external domain conclusions are true.  It certifies observed
AASM contract behavior against explicit deterministic fixtures and may return
INCONCLUSIVE when required evidence or an enforcement boundary is absent.
"""

from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Iterable

from .evidence import EvidenceRecord
from .model import ProblemSpec
from .reference_domains import run_reference_domain_stress
from .runtime_v41 import AASMEngine
from .sii import StructuredProposal, create_sii, sii_contract


CERTIFICATION_CONTRACT_ID = "aasm.certification.v1"
CERTIFICATION_CONTRACT_VERSION = "0.1.0"
CERTIFICATION_STATUSES = ("PASS", "FAIL", "INCONCLUSIVE")
CERTIFICATION_TARGET_IDS = (
    "reference-domains",
    "solver-reuse",
    "truth-memory",
    "formal-verification",
    "sii-preview",
)


def certification_contract() -> dict[str, Any]:
    return {
        "contract_id": CERTIFICATION_CONTRACT_ID,
        "contract_version": CERTIFICATION_CONTRACT_VERSION,
        "statuses": list(CERTIFICATION_STATUSES),
        "status_semantics": {
            "PASS": "all required observed checks passed",
            "FAIL": "one or more required observed checks failed",
            "INCONCLUSIVE": "no required observed check failed, but required evidence or enforcement is absent",
        },
        "authority": "CERTIFICATION_HARNESS_ONLY",
        "truth_claim": "NO_ARBITRARY_EXTERNAL_SEMANTIC_TRUTH_CLAIM",
        "kernel_changes": "NONE",
        "network_required": False,
        "model_key_required": False,
        "targets": list(CERTIFICATION_TARGET_IDS),
        "adversarial_rules": [
            "negative_fixtures_are_first_class",
            "missing_evidence_is_not_pass",
            "self_attestation_is_not_certification",
            "synthetic_fixture_success_is_not_real_world_truth",
            "inconclusive_is_a_valid_terminal_result",
        ],
    }


@dataclass(frozen=True)
class CertificationCheck:
    check_id: str
    status: str
    statement: str
    evidence: tuple[str, ...] = ()
    detail: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.status not in CERTIFICATION_STATUSES:
            raise ValueError(f"invalid certification status: {self.status}")
        if not self.check_id.strip():
            raise ValueError("certification check_id is required")
        if not self.statement.strip():
            raise ValueError("certification statement is required")
        object.__setattr__(self, "evidence", tuple(sorted(set(map(str, self.evidence)))))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CertificationReport:
    target_id: str
    checks: tuple[CertificationCheck, ...]
    scope: str = "DETERMINISTIC_AASM_CONTRACT_BEHAVIOR"
    notes: tuple[str, ...] = ()

    @property
    def status(self) -> str:
        values = {check.status for check in self.checks}
        if "FAIL" in values:
            return "FAIL"
        if "INCONCLUSIVE" in values or not self.checks:
            return "INCONCLUSIVE"
        return "PASS"

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_id": self.target_id,
            "status": self.status,
            "scope": self.scope,
            "checks": [check.to_dict() for check in self.checks],
            "notes": list(self.notes),
        }


def _check(check_id: str, passed: bool, statement: str, *, evidence: Iterable[str] = (), detail: dict[str, Any] | None = None) -> CertificationCheck:
    return CertificationCheck(
        check_id=check_id,
        status="PASS" if passed else "FAIL",
        statement=statement,
        evidence=tuple(evidence),
        detail=dict(detail or {}),
    )


def _inconclusive(check_id: str, statement: str, *, detail: dict[str, Any] | None = None) -> CertificationCheck:
    return CertificationCheck(check_id, "INCONCLUSIVE", statement, detail=dict(detail or {}))


def _reference_domains() -> CertificationReport:
    stress = run_reference_domain_stress()
    checks = [
        _check(
            "reference-domains-pass",
            stress["passed"] is True,
            "all v0.42 reference-domain boundary checks pass",
            detail={
                "domain_count": stress["domain_count"],
                "checks_total": stress["checks_total"],
                "checks_passed": stress["checks_passed"],
            },
        )
    ]
    for row in stress["domains"]:
        checks.append(
            _check(
                f"domain:{row['domain_id']}",
                row["passed"] is True,
                f"reference domain {row['domain_id']} preserves its declared AASM boundaries",
                detail={"checks": row["checks"]},
            )
        )
    return CertificationReport(
        "reference-domains",
        tuple(checks),
        notes=("Synthetic offline fixtures certify contract behavior, not production-domain answer quality.",),
    )


def _solver_reuse() -> CertificationReport:
    constraint = run_reference_domain_stress("constraint-solving")["domains"][0]
    software = run_reference_domain_stress("software-repair")["domains"][0]
    formal = run_reference_domain_stress("formal-reasoning")["domains"][0]
    selected = {
        "durable-hit": constraint["checks"]["hot_index_deletion_does_not_change_truth"],
        "certificate-gated-skip": constraint["checks"]["solver_skips_only_after_reuse_certificate"],
        "freshness-rejection": software["checks"]["expired_observation_rejected"],
        "dependency-rejection": software["checks"]["dependency_change_rejected"],
        "effect-rejection": software["checks"]["non_idempotent_effect_never_reused"],
        "strength-rejection": formal["checks"]["insufficient_verification_strength_rejected"],
    }
    return CertificationReport(
        "solver-reuse",
        tuple(
            _check(name, bool(value), f"solver/reuse adversarial invariant {name} holds")
            for name, value in selected.items()
        ),
    )


def _truth_memory() -> CertificationReport:
    reasoning = run_reference_domain_stress("research-synthesis")["domains"][0]
    memory = run_reference_domain_stress("long-horizon-memory")["domains"][0]
    selected = {
        "truth-change-invalidates-reuse": reasoning["checks"]["truth_change_invalidates_reasoning_reuse"],
        "stale-state-durable": reasoning["checks"]["reasoning_source_is_durably_stale"],
        "privacy-isolation": memory["checks"]["other_principal_cannot_see_memory"],
        "privacy-reuse-isolation": memory["checks"]["other_principal_cannot_reuse_memory"],
        "revocation-invalidates-reuse": memory["checks"]["revoked_memory_cannot_be_reused"],
        "revocation-durable": memory["checks"]["memory_is_durably_revoked"],
    }
    return CertificationReport(
        "truth-memory",
        tuple(
            _check(name, bool(value), f"truth/memory adversarial invariant {name} holds")
            for name, value in selected.items()
        ),
    )


def _formal_verification() -> CertificationReport:
    formal = run_reference_domain_stress("formal-reasoning")["domains"][0]
    return CertificationReport(
        "formal-verification",
        (
            _check(
                "weak-proof-rejected",
                formal["checks"]["insufficient_verification_strength_rejected"],
                "a weaker proof-strength label cannot satisfy a stronger exact requirement",
                detail={"weak_rejections": formal["details"].get("weak_rejections", [])},
            ),
            _check(
                "required-proof-reused",
                formal["checks"]["required_verification_strength_reused"],
                "a candidate with the required verification strength may be reused",
                detail={"accepted_strength": formal["details"].get("accepted_strength")},
            ),
            _check(
                "formal-skip-certificate-gated",
                formal["checks"]["formal_reuse_skips_execution_after_certificate"],
                "formal execution is skipped only through validated reuse",
            ),
        ),
        notes=("This certifies the AASM fixture/contract path; it is not a theorem that an arbitrary external solver result is sound.",),
    )


def _sii_preview() -> CertificationReport:
    engine = AASMEngine(ProblemSpec("v0.43 SII adversarial certification"))
    sii = create_sii(engine)
    registered = sii.register(
        principal_id="cert-principal",
        name="cert reasoner",
        kind="llm",
        provider="fixture",
        model_id="model-a",
    )
    proposer_id = registered["identity"]["proposer_id"]

    checks: list[CertificationCheck] = []

    try:
        StructuredProposal(
            proposer_id=proposer_id,
            decision_name="forged",
            scope_id="root",
            chosen="x",
            confidence=.5,
            semantic_fingerprint="producer-controlled",  # type: ignore[call-arg]
        )
        forged_rejected = False
    except TypeError:
        forged_rejected = True
    checks.append(_check(
        "producer-cannot-supply-fingerprint",
        forged_rejected,
        "producer-controlled semantic fingerprints are rejected by the proposal contract",
    ))

    try:
        sii.register(
            principal_id="cert-principal",
            name="identity reset attempt",
            kind="llm",
            provider="fixture",
            model_id="model-b",
        )
        reset_rejected = False
    except ValueError:
        reset_rejected = True
    checks.append(_check(
        "identity-reset-rejected",
        reset_rejected,
        "a stable principal cannot silently reset its SII identity metadata",
        evidence=(registered["evidence_id"],),
    ))

    proposal = StructuredProposal(
        proposer_id=proposer_id,
        decision_name="candidate",
        scope_id="root",
        chosen={"strategy": "reuse-first"},
        confidence=.7,
    )
    submitted = sii.submit(proposal)

    try:
        sii.measure_proposal_outcome(
            proposal.proposal_id,
            measured_by=proposer_id,
            authority_class="VERIFIER",
            disposition="INCONCLUSIVE",
            verification_verdict="INCONCLUSIVE",
        )
        self_measurement_rejected = False
    except ValueError:
        self_measurement_rejected = True
    checks.append(_check(
        "self-measurement-rejected",
        self_measurement_rejected,
        "a proposal producer cannot score its own SII outcome",
        evidence=(submitted["proposal_evidence_id"],),
    ))

    fake_metrics = engine.add_evidence(
        EvidenceRecord(
            kind="reuse_metrics",
            statement="{}",
            source="forged-meter",
        ),
        reason="v0.43 adversarial fake reuse telemetry",
    )
    try:
        sii.measure_proposal_outcome(
            proposal.proposal_id,
            measured_by="independent-meter",
            authority_class="VERIFIER",
            reuse_metrics_evidence_ids=(fake_metrics.evidence_id,),
            disposition="INCONCLUSIVE",
            verification_verdict="INCONCLUSIVE",
        )
        fake_reuse_rejected = False
    except ValueError:
        fake_reuse_rejected = True
    checks.append(_check(
        "forged-reuse-metrics-rejected",
        fake_reuse_rejected,
        "SII savings credit accepts only durable AASM reuse-metrics evidence",
        evidence=(fake_metrics.evidence_id,),
    ))

    feedback = sii.measure_proposal_outcome(
        proposal.proposal_id,
        measured_by="independent-meter",
        authority_class="VERIFIER",
        disposition="INCONCLUSIVE",
        verification_verdict="INCONCLUSIVE",
    )
    lease = feedback.resource_lease
    checks.append(_check(
        "resource-lease-never-grants-authority",
        lease.authority_class == "PROPOSER"
        and lease.direct_truth_promotion is False
        and lease.direct_state_mutation is False
        and lease.self_verification is False,
        "computed resource privilege does not promote epistemic authority",
        evidence=(feedback.outcome_evidence_id,),
        detail={"resource_tier": lease.resource_tier},
    ))

    try:
        sii.measure_proposal_outcome(
            proposal.proposal_id,
            measured_by="another-meter",
            authority_class="CONTROLLER",
            disposition="FAILED",
            verification_verdict="FAIL",
        )
        duplicate_score_rejected = False
    except ValueError:
        duplicate_score_rejected = True
    checks.append(_check(
        "one-scoreable-outcome-per-proposal",
        duplicate_score_rejected,
        "one proposal cannot be farmed into multiple scoreable SII outcome samples",
        evidence=(feedback.outcome_evidence_id,),
    ))

    contract = sii_contract()
    checks.append(_inconclusive(
        "measurement-principal-authority-binding",
        "v0.43 preview still receives measurement authority class from the caller; durable actor/authority binding is a v0.44 graduation gate",
        detail={"current": contract["measurement_identity_binding"]},
    ))
    checks.append(_inconclusive(
        "resource-lease-enforcement",
        "v0.43 computes a bounded ResourceLease but does not yet enforce it through the scheduler/capability plane",
        detail={"current": contract["resource_enforcement"]},
    ))

    return CertificationReport(
        "sii-preview",
        tuple(checks),
        scope="EXPERIMENTAL_V044_SII_GRADUATION_READINESS",
        notes=(
            "INCONCLUSIVE is expected until actor authority and resource enforcement are bound to existing AASM governance.",
            "The preview may be exercised directly through create_sii(engine), but is not the active runtime/public authority plane.",
        ),
    )


_RUNNERS: dict[str, Callable[[], CertificationReport]] = {
    "reference-domains": _reference_domains,
    "solver-reuse": _solver_reuse,
    "truth-memory": _truth_memory,
    "formal-verification": _formal_verification,
    "sii-preview": _sii_preview,
}


def run_certification(target_id: str | None = None) -> dict[str, Any]:
    if target_id is not None and target_id not in _RUNNERS:
        raise ValueError(f"unknown certification target: {target_id}")
    selected = [target_id] if target_id else list(CERTIFICATION_TARGET_IDS)
    reports = [_RUNNERS[name]().to_dict() for name in selected]
    status_counts = {status: sum(1 for report in reports if report["status"] == status) for status in CERTIFICATION_STATUSES}
    core_reports = [report for report in reports if report["target_id"] != "sii-preview"]
    core_status = "PASS"
    if any(report["status"] == "FAIL" for report in core_reports):
        core_status = "FAIL"
    elif any(report["status"] == "INCONCLUSIVE" for report in core_reports):
        core_status = "INCONCLUSIVE"
    overall_status = "FAIL" if status_counts["FAIL"] else ("INCONCLUSIVE" if status_counts["INCONCLUSIVE"] else "PASS")
    return {
        "contract": certification_contract(),
        "status": overall_status,
        "core_status": core_status,
        "status_counts": status_counts,
        "target_count": len(reports),
        "targets": reports,
        "interpretation": {
            "core_status": "certification status excluding explicitly experimental SII preview",
            "status": "combined status including experimental targets",
        },
    }


__all__ = [
    "CERTIFICATION_CONTRACT_ID",
    "CERTIFICATION_CONTRACT_VERSION",
    "CERTIFICATION_STATUSES",
    "CERTIFICATION_TARGET_IDS",
    "CertificationCheck",
    "CertificationReport",
    "certification_contract",
    "run_certification",
]
