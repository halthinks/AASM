from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from math import isclose
from typing import Any, Iterable, Mapping

from .effects import (
    EFFECT_DISPATCH_REQUEST_CONTRACT_ID,
    EFFECT_GOVERNANCE_CONTRACT_VERSION,
    EFFECT_GOVERNANCE_STABILITY,
    EFFECT_INTENT_CONTRACT_ID,
    EFFECT_OWNERSHIP_CONTRACT_ID,
    EFFECT_RECONCILIATION_CONTRACT_ID,
    EffectDispatchRequest,
    EffectIntent,
    EffectOutcome,
    EffectOwnership,
    EffectOwnershipRequest,
    EffectReconciliation,
    EffectStatus,
    EffectUnknownOutcome,
    bind_effect_reconciliation,
    effect_governance_contract,
)
from .evidence import EvidenceRecord
from .model import now
from .optimization import (
    OPTIMIZATION_CAPABILITIES,
    OptimizationModel,
    OptimizationRequest,
    OptimizationResult,
    objective_value,
    validate_optimization_result,
    validate_optimization_solution,
)
from .proof_claims import SolverClaimCertificate
from .runtime_v53_learning import AASMEngine as V53Engine
from .semantic_result import canonical_semantic_json, semantic_fingerprint
from .workers import LeaseStatus


EFFECT_GOVERNANCE_RUNTIME_CONTRACT_ID = "aasm.effect.governance.runtime.v1"
EFFECT_GOVERNANCE_RUNTIME_CONTRACT_VERSION = "0.1.0"
EFFECT_GOVERNANCE_RUNTIME_STABILITY = "FOUNDATION_EXPERIMENTAL"
_EFFECT_GOVERNANCE_RECORD_TYPE = "aasm_effect_governance_record_type"
_EFFECT_GOVERNANCE_DOCUMENT = "document"

SOLVER_TRANSLATION_CONTRACT_ID = "aasm.solver.translation.v1"
SOLVER_PORTFOLIO_CONTRACT_ID = "aasm.solver.portfolio.v1"
SOLVER_PORTFOLIO_CONTRACT_VERSION = "0.1.0"
SOLVER_PORTFOLIO_STABILITY = "FOUNDATION_EXPERIMENTAL"
SOLVER_TRANSLATION_CHECKER_ID = "aasm.checker.solver-translation.v1"
SOLVER_TRANSLATION_CHECKER_VERSION = "0.1.0"
PORTFOLIO_DECISION_STATUSES = (
    "CERTIFIED_OPTIMAL",
    "CERTIFIED_NEGATIVE",
    "BEST_VALIDATED_FEASIBLE",
    "INCONCLUSIVE",
    "CONFLICT",
)


def effect_governance_runtime_contract() -> dict[str, Any]:
    return {
        "contract_id": EFFECT_GOVERNANCE_RUNTIME_CONTRACT_ID,
        "contract_version": EFFECT_GOVERNANCE_RUNTIME_CONTRACT_VERSION,
        "stability": EFFECT_GOVERNANCE_RUNTIME_STABILITY,
        "model_contract": effect_governance_contract(),
        "intent_contract_id": EFFECT_INTENT_CONTRACT_ID,
        "dispatch_request_contract_id": EFFECT_DISPATCH_REQUEST_CONTRACT_ID,
        "ownership_contract_id": EFFECT_OWNERSHIP_CONTRACT_ID,
        "reconciliation_contract_id": EFFECT_RECONCILIATION_CONTRACT_ID,
        "existing_effect_execution": "V08_ATOMIC_EFFECT_CLAIM_REUSED",
        "claim_atomicity": "EXISTING_STORE_EFFECT_CLAIM_TRANSACTION",
        "authority": "V53_SCOPED_EFFECT_EXECUTE_REQUIRED_EACH_ATTEMPT",
        "task_lease": "EXISTING_AASM_TASKLEASE_REQUIRED_FOR_V54_DISPATCH",
        "resource_reservation": "DECLARED_RESERVATIONS_MUST_REMAIN_ACTIVE_AT_AUTHORIZATION_AND_DISPATCH",
        "external_boundary": "DURABLE_OWNERSHIP_EVIDENCE_REQUIRED_BEFORE_EXECUTOR_CALL",
        "unknown_outcome": "RETRY_BLOCKED_UNTIL_EXPLICIT_RECONCILIATION",
        "reconciliation_evidence": "LOCAL_EVIDENCE_IDS_ONLY_VALIDATED_BEFORE_MUTATION",
        "crash_idempotency": "INTENT_AND_DISPATCH_EVIDENCE_REPAIRABLE",
        "resource_state_grants_authority": False,
        "truth_authority": "NONE_ADDED_BY_EFFECT_GOVERNANCE",
    }


def solver_portfolio_contract() -> dict[str, Any]:
    return {
        "translation_contract_id": SOLVER_TRANSLATION_CONTRACT_ID,
        "portfolio_contract_id": SOLVER_PORTFOLIO_CONTRACT_ID,
        "contract_version": SOLVER_PORTFOLIO_CONTRACT_VERSION,
        "stability": SOLVER_PORTFOLIO_STABILITY,
        "canonical_problem": "ONE_SOURCE_MODEL",
        "solver_representations": "CERTIFIED_IDENTITY_CANONICAL_REPRESENTATIONS",
        "translation_checker": SOLVER_TRANSLATION_CHECKER_ID,
        "result_validation": "SOURCE_MODEL_REVALIDATED",
        "negative_claims": "PROOF_CERTIFICATE_REQUIRED_TO_BE_DECISIVE",
        "optimality_claims": "PROOF_CERTIFICATE_REQUIRED_TO_BE_DECISIVE",
        "uncertified_negative_majority": "NEVER_DECISIVE",
        "fastest_result": "NEVER_CORRECTNESS_TIEBREAK",
        "arrival_order": "NEVER_CORRECTNESS_TIEBREAK",
        "conflicting_certified_or_validated_facts": "CONFLICT_FAIL_CLOSED",
        "result_authority": "EVIDENCE_ONLY",
        "truth_authority": "EXISTING_AASM_POLICY_ONLY",
    }


def _semantic_model_payload(model: OptimizationModel) -> dict[str, Any]:
    return {
        "variables": [row.to_dict() for row in model.variables],
        "constraints": [row.to_dict() for row in model.constraints],
        "objective": None if model.objective is None else model.objective.to_dict(),
    }


def _semantic_model_fingerprint(model: OptimizationModel) -> str:
    return semantic_fingerprint(_semantic_model_payload(model))


@dataclass(frozen=True)
class SolverTranslation:
    source_model_fingerprint: str
    source_semantic_fingerprint: str
    target_model: OptimizationModel | Mapping[str, Any]
    target_family: str
    target_provider_id: str
    target_semantic_fingerprint: str = ""
    translation_kind: str = "IDENTITY_CANONICAL_REPRESENTATION"
    metadata: Mapping[str, Any] = field(default_factory=dict)
    translation_id: str = ""

    def __post_init__(self) -> None:
        model = self.target_model if isinstance(self.target_model, OptimizationModel) else OptimizationModel.from_dict(self.target_model)
        if self.target_family not in OPTIMIZATION_CAPABILITIES:
            raise ValueError(f"unsupported target solver family: {self.target_family}")
        if model.solver_family != self.target_family:
            raise ValueError("translated target model does not match target solver family")
        if not self.source_model_fingerprint or not self.source_semantic_fingerprint or not self.target_provider_id:
            raise ValueError("solver translation requires source model/semantic and target provider identity")
        if self.translation_kind != "IDENTITY_CANONICAL_REPRESENTATION":
            raise ValueError("unsupported v0.54 solver translation kind")
        object.__setattr__(self, "target_model", model)
        target_semantic = self.target_semantic_fingerprint or _semantic_model_fingerprint(model)
        object.__setattr__(self, "target_semantic_fingerprint", target_semantic)
        if not self.translation_id:
            object.__setattr__(self, "translation_id", f"solver-translation-{semantic_fingerprint(self.identity_payload())[:24]}")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": SOLVER_TRANSLATION_CONTRACT_ID,
            "contract_version": SOLVER_PORTFOLIO_CONTRACT_VERSION,
            "source_model_fingerprint": self.source_model_fingerprint,
            "source_semantic_fingerprint": self.source_semantic_fingerprint,
            "target_model": self.target_model.to_dict(),
            "target_family": self.target_family,
            "target_provider_id": self.target_provider_id,
            "target_semantic_fingerprint": self.target_semantic_fingerprint,
            "translation_kind": self.translation_kind,
            "metadata": dict(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"translation_id": self.translation_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"translation_id": self.translation_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SolverTranslation":
        payload = deepcopy(dict(value))
        payload.pop("fingerprint", None)
        payload.pop("contract_id", None)
        payload.pop("contract_version", None)
        return cls(**payload)


@dataclass(frozen=True)
class SolverTranslationCertificate:
    translation_id: str
    translation_fingerprint: str
    source_model_fingerprint: str
    target_model_fingerprint: str
    target_family: str
    target_provider_id: str
    exact_semantic_match: bool
    status: str
    checker_id: str = SOLVER_TRANSLATION_CHECKER_ID
    checker_version: str = SOLVER_TRANSLATION_CHECKER_VERSION
    diagnostics: tuple[str, ...] = ()
    certificate_id: str = ""

    def __post_init__(self) -> None:
        if self.status not in {"PASS", "FAIL"}:
            raise ValueError("translation certificate status must be PASS or FAIL")
        if self.status == "PASS" and not self.exact_semantic_match:
            raise ValueError("passing solver translation certificate requires exact semantic match")
        object.__setattr__(self, "diagnostics", tuple(map(str, self.diagnostics)))
        if not self.certificate_id:
            object.__setattr__(self, "certificate_id", f"solver-translation-certificate-{semantic_fingerprint(self.identity_payload())[:24]}")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "translation_id": self.translation_id,
            "translation_fingerprint": self.translation_fingerprint,
            "source_model_fingerprint": self.source_model_fingerprint,
            "target_model_fingerprint": self.target_model_fingerprint,
            "target_family": self.target_family,
            "target_provider_id": self.target_provider_id,
            "exact_semantic_match": bool(self.exact_semantic_match),
            "status": self.status,
            "checker_id": self.checker_id,
            "checker_version": self.checker_version,
            "diagnostics": list(self.diagnostics),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"certificate_id": self.certificate_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"certificate_id": self.certificate_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SolverTranslationCertificate":
        payload = deepcopy(dict(value))
        payload.pop("fingerprint", None)
        payload["diagnostics"] = tuple(payload.get("diagnostics") or ())
        return cls(**payload)


def translate_model_for_solver(
    source_model: OptimizationModel | Mapping[str, Any],
    *,
    target_family: str,
    target_provider_id: str,
) -> tuple[SolverTranslation, SolverTranslationCertificate]:
    source = source_model if isinstance(source_model, OptimizationModel) else OptimizationModel.from_dict(source_model)
    target = OptimizationModel(
        source.name,
        source.variables,
        source.constraints,
        objective=source.objective,
        family=target_family,
        metadata={
            **dict(source.metadata),
            "v54_translation_source_model_fingerprint": source.fingerprint,
            "v54_translation_target_provider_id": target_provider_id,
        },
    )
    translation = SolverTranslation(
        source.fingerprint,
        _semantic_model_fingerprint(source),
        target,
        target_family,
        target_provider_id,
        metadata={"source_family": source.solver_family},
    )
    return translation, verify_solver_translation(source, translation)


def verify_solver_translation(
    source_model: OptimizationModel | Mapping[str, Any],
    translation: SolverTranslation | Mapping[str, Any],
) -> SolverTranslationCertificate:
    source = source_model if isinstance(source_model, OptimizationModel) else OptimizationModel.from_dict(source_model)
    item = translation if isinstance(translation, SolverTranslation) else SolverTranslation.from_dict(translation)
    diagnostics: list[str] = []
    if item.source_model_fingerprint != source.fingerprint:
        diagnostics.append("SOURCE_MODEL_FINGERPRINT_MISMATCH")
    source_semantic = _semantic_model_fingerprint(source)
    target_semantic = _semantic_model_fingerprint(item.target_model)
    if item.source_semantic_fingerprint != source_semantic:
        diagnostics.append("SOURCE_SEMANTIC_FINGERPRINT_MISMATCH")
    if item.target_semantic_fingerprint != target_semantic:
        diagnostics.append("TARGET_SEMANTIC_FINGERPRINT_MISMATCH")
    if source_semantic != target_semantic:
        diagnostics.append("SEMANTIC_PROJECTION_MISMATCH")
    if item.target_model.solver_family != item.target_family:
        diagnostics.append("TARGET_FAMILY_MISMATCH")
    exact = not diagnostics
    return SolverTranslationCertificate(
        item.translation_id,
        item.fingerprint,
        source.fingerprint,
        item.target_model.fingerprint,
        item.target_family,
        item.target_provider_id,
        exact,
        "PASS" if exact else "FAIL",
        diagnostics=tuple(diagnostics),
    )


def _proof_certificate_from_dict(value: Mapping[str, Any]) -> SolverClaimCertificate:
    payload = deepcopy(dict(value))
    payload.pop("fingerprint", None)
    payload["diagnostics"] = tuple(payload.get("diagnostics") or ())
    return SolverClaimCertificate(**payload)


@dataclass(frozen=True)
class PortfolioRaceEntry:
    translation: SolverTranslation | Mapping[str, Any]
    translation_certificate: SolverTranslationCertificate | Mapping[str, Any]
    request: OptimizationRequest | Mapping[str, Any]
    result: OptimizationResult | Mapping[str, Any]
    proof_certificate: SolverClaimCertificate | Mapping[str, Any] | None = None
    evidence_ids: tuple[str, ...] = ()
    entry_id: str = ""

    def __post_init__(self) -> None:
        translation = self.translation if isinstance(self.translation, SolverTranslation) else SolverTranslation.from_dict(self.translation)
        translation_certificate = self.translation_certificate if isinstance(self.translation_certificate, SolverTranslationCertificate) else SolverTranslationCertificate.from_dict(self.translation_certificate)
        request = self.request if isinstance(self.request, OptimizationRequest) else OptimizationRequest.from_dict(self.request)
        result = self.result if isinstance(self.result, OptimizationResult) else OptimizationResult.from_dict(self.result)
        proof = self.proof_certificate
        if proof is not None and not isinstance(proof, SolverClaimCertificate):
            proof = _proof_certificate_from_dict(proof)
        object.__setattr__(self, "translation", translation)
        object.__setattr__(self, "translation_certificate", translation_certificate)
        object.__setattr__(self, "request", request)
        object.__setattr__(self, "result", result)
        object.__setattr__(self, "proof_certificate", proof)
        object.__setattr__(self, "evidence_ids", tuple(sorted(set(map(str, self.evidence_ids)))))
        if not self.entry_id:
            object.__setattr__(self, "entry_id", f"portfolio-entry-{semantic_fingerprint(self.identity_payload())[:24]}")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "translation": self.translation.to_dict(),
            "translation_certificate": self.translation_certificate.to_dict(),
            "request": self.request.to_dict(),
            "result": self.result.to_dict(),
            "proof_certificate": None if self.proof_certificate is None else self.proof_certificate.to_dict(),
            "evidence_ids": list(self.evidence_ids),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"entry_id": self.entry_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"entry_id": self.entry_id, **self.identity_payload(), "fingerprint": self.fingerprint}


@dataclass(frozen=True)
class PortfolioRacePolicy:
    accept_best_feasible: bool = True
    require_proof_for_negative: bool = True
    require_proof_for_optimal: bool = True
    objective_tolerance: float = 1e-9

    def __post_init__(self) -> None:
        if float(self.objective_tolerance) < 0:
            raise ValueError("portfolio objective_tolerance must be non-negative")

    def to_dict(self) -> dict[str, Any]:
        return {
            "accept_best_feasible": bool(self.accept_best_feasible),
            "require_proof_for_negative": bool(self.require_proof_for_negative),
            "require_proof_for_optimal": bool(self.require_proof_for_optimal),
            "objective_tolerance": float(self.objective_tolerance),
            "majority_vote": False,
            "fastest_wins": False,
            "arrival_order_tiebreak": False,
        }


@dataclass(frozen=True)
class PortfolioRaceDecision:
    source_model_fingerprint: str
    status: str
    selected_entry_id: str = ""
    selected_result_id: str = ""
    selected_provider_id: str = ""
    selected_assignment: Mapping[str, float] = field(default_factory=dict)
    selected_objective: float | None = None
    certified: bool = False
    decisive_certificate_ids: tuple[str, ...] = ()
    ignored_entry_ids: tuple[str, ...] = ()
    conflicting_entry_ids: tuple[str, ...] = ()
    diagnostics: tuple[str, ...] = ()
    policy: Mapping[str, Any] = field(default_factory=dict)
    decision_id: str = ""

    def __post_init__(self) -> None:
        if self.status not in PORTFOLIO_DECISION_STATUSES:
            raise ValueError(f"unsupported portfolio decision status: {self.status}")
        object.__setattr__(self, "selected_assignment", {str(k): float(v) for k, v in sorted(self.selected_assignment.items())})
        object.__setattr__(self, "decisive_certificate_ids", tuple(sorted(set(map(str, self.decisive_certificate_ids)))))
        object.__setattr__(self, "ignored_entry_ids", tuple(sorted(set(map(str, self.ignored_entry_ids)))))
        object.__setattr__(self, "conflicting_entry_ids", tuple(sorted(set(map(str, self.conflicting_entry_ids)))))
        object.__setattr__(self, "diagnostics", tuple(map(str, self.diagnostics)))
        if not self.decision_id:
            object.__setattr__(self, "decision_id", f"portfolio-decision-{semantic_fingerprint(self.identity_payload())[:24]}")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": SOLVER_PORTFOLIO_CONTRACT_ID,
            "contract_version": SOLVER_PORTFOLIO_CONTRACT_VERSION,
            "source_model_fingerprint": self.source_model_fingerprint,
            "status": self.status,
            "selected_entry_id": self.selected_entry_id,
            "selected_result_id": self.selected_result_id,
            "selected_provider_id": self.selected_provider_id,
            "selected_assignment": dict(self.selected_assignment),
            "selected_objective": self.selected_objective,
            "certified": bool(self.certified),
            "decisive_certificate_ids": list(self.decisive_certificate_ids),
            "ignored_entry_ids": list(self.ignored_entry_ids),
            "conflicting_entry_ids": list(self.conflicting_entry_ids),
            "diagnostics": list(self.diagnostics),
            "policy": dict(self.policy),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"decision_id": self.decision_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"decision_id": self.decision_id, **self.identity_payload(), "fingerprint": self.fingerprint}


def _proof_certificate_is_exact(entry: PortfolioRaceEntry, claim_types: set[str]) -> bool:
    certificate = entry.proof_certificate
    if certificate is None:
        return False
    return bool(
        certificate.status == "PASS"
        and certificate.verification_level == "PROOF_CERTIFIED"
        and certificate.independent_of_solver
        and certificate.model_fingerprint == entry.request.model.fingerprint
        and certificate.result_fingerprint == entry.result.fingerprint
        and str(certificate.coverage.get("claim_type") or "") in claim_types
    )


def _entry_tiebreak(entry: PortfolioRaceEntry) -> tuple[str, str, str]:
    assignment_fingerprint = semantic_fingerprint({str(k): float(v) for k, v in sorted(entry.result.assignment.items())})
    return assignment_fingerprint, entry.result.solver.provider_id, entry.result.result_id


def evaluate_portfolio_race(
    source_model: OptimizationModel | Mapping[str, Any],
    entries: Iterable[PortfolioRaceEntry | Mapping[str, Any]],
    policy: PortfolioRacePolicy | None = None,
) -> PortfolioRaceDecision:
    source = source_model if isinstance(source_model, OptimizationModel) else OptimizationModel.from_dict(source_model)
    policy = policy or PortfolioRacePolicy()
    rows = tuple(row if isinstance(row, PortfolioRaceEntry) else PortfolioRaceEntry(**dict(row)) for row in entries)
    if not rows:
        raise ValueError("portfolio race requires at least one result entry")

    validated_solutions: list[tuple[PortfolioRaceEntry, float | None]] = []
    certified_negative: list[PortfolioRaceEntry] = []
    certified_optimal: list[tuple[PortfolioRaceEntry, float]] = []
    ignored: list[str] = []

    for entry in rows:
        rebuilt = verify_solver_translation(source, entry.translation)
        if rebuilt.to_dict() != entry.translation_certificate.to_dict() or rebuilt.status != "PASS":
            raise ValueError(f"portfolio entry has invalid solver translation certificate: {entry.entry_id}")
        if entry.request.model.fingerprint != entry.translation.target_model.fingerprint:
            raise ValueError("portfolio request does not use its certified translated model")
        if entry.request.required_provider and entry.request.required_provider != entry.translation.target_provider_id:
            raise ValueError("portfolio request provider does not match certified translation target")
        if entry.result.solver.provider_id != entry.translation.target_provider_id:
            raise ValueError("portfolio result provider does not match certified translation target")
        validate_optimization_result(entry.request, entry.result)

        if entry.result.status in {"SAT", "FEASIBLE", "OPTIMAL"}:
            validate_optimization_solution(source, entry.result.assignment)
            source_objective = objective_value(source, entry.result.assignment)
            validated_solutions.append((entry, source_objective))
            if entry.result.status == "OPTIMAL" and _proof_certificate_is_exact(entry, {"OPTIMAL"}):
                if source_objective is None:
                    raise ValueError("certified OPTIMAL portfolio result requires a source objective")
                certified_optimal.append((entry, float(source_objective)))
            continue

        if entry.result.status in {"UNSAT", "INFEASIBLE"}:
            if _proof_certificate_is_exact(entry, {"UNSAT", "INFEASIBLE"}):
                certified_negative.append(entry)
            else:
                ignored.append(entry.entry_id)
            continue

        ignored.append(entry.entry_id)

    if certified_negative and validated_solutions:
        conflict_ids = [row.entry_id for row in certified_negative] + [row.entry_id for row, _ in validated_solutions]
        return PortfolioRaceDecision(
            source.fingerprint,
            "CONFLICT",
            conflicting_entry_ids=tuple(conflict_ids),
            ignored_entry_ids=tuple(ignored),
            diagnostics=("CERTIFIED_NEGATIVE_CONFLICTS_WITH_VALIDATED_FEASIBLE_SOLUTION",),
            policy=policy.to_dict(),
        )

    if certified_optimal:
        values = [value for _, value in certified_optimal]
        reference = values[0]
        if any(not isclose(value, reference, abs_tol=policy.objective_tolerance) for value in values[1:]):
            return PortfolioRaceDecision(
                source.fingerprint,
                "CONFLICT",
                conflicting_entry_ids=tuple(row.entry_id for row, _ in certified_optimal),
                ignored_entry_ids=tuple(ignored),
                diagnostics=("CERTIFIED_OPTIMAL_RESULTS_DISAGREE_ON_OBJECTIVE",),
                policy=policy.to_dict(),
            )
        if source.objective is not None:
            for entry, value in validated_solutions:
                better = value is not None and (
                    value < reference - policy.objective_tolerance
                    if source.objective.sense == "MINIMIZE"
                    else value > reference + policy.objective_tolerance
                )
                if better:
                    return PortfolioRaceDecision(
                        source.fingerprint,
                        "CONFLICT",
                        conflicting_entry_ids=tuple([entry.entry_id, *[row.entry_id for row, _ in certified_optimal]]),
                        ignored_entry_ids=tuple(ignored),
                        diagnostics=("CERTIFIED_OPTIMAL_CONFLICTS_WITH_BETTER_VALIDATED_SOLUTION",),
                        policy=policy.to_dict(),
                    )
        selected = min((row for row, _ in certified_optimal), key=_entry_tiebreak)
        return PortfolioRaceDecision(
            source.fingerprint,
            "CERTIFIED_OPTIMAL",
            selected.entry_id,
            selected.result.result_id,
            selected.result.solver.provider_id,
            selected.result.assignment,
            reference,
            True,
            tuple(
                row.proof_certificate.certificate_id
                for row, _ in certified_optimal
                if row.proof_certificate is not None
            ),
            tuple(ignored),
            policy=policy.to_dict(),
        )

    if certified_negative:
        selected = min(certified_negative, key=lambda row: (row.result.solver.provider_id, row.result.result_id))
        return PortfolioRaceDecision(
            source.fingerprint,
            "CERTIFIED_NEGATIVE",
            selected.entry_id,
            selected.result.result_id,
            selected.result.solver.provider_id,
            certified=True,
            decisive_certificate_ids=tuple(
                row.proof_certificate.certificate_id
                for row in certified_negative
                if row.proof_certificate is not None
            ),
            ignored_entry_ids=tuple(ignored),
            policy=policy.to_dict(),
        )

    if validated_solutions and policy.accept_best_feasible:
        if source.objective is None:
            selected, selected_value = min(validated_solutions, key=lambda item: _entry_tiebreak(item[0]))
        else:
            values = [float(value) for _, value in validated_solutions if value is not None]
            best_value = min(values) if source.objective.sense == "MINIMIZE" else max(values)
            eligible = [
                (entry, value)
                for entry, value in validated_solutions
                if value is not None and isclose(float(value), best_value, abs_tol=policy.objective_tolerance)
            ]
            selected, selected_value = min(eligible, key=lambda item: _entry_tiebreak(item[0]))
        return PortfolioRaceDecision(
            source.fingerprint,
            "BEST_VALIDATED_FEASIBLE",
            selected.entry_id,
            selected.result.result_id,
            selected.result.solver.provider_id,
            selected.result.assignment,
            None if selected_value is None else float(selected_value),
            False,
            ignored_entry_ids=tuple(ignored),
            diagnostics=("BEST_KNOWN_VALIDATED_SOLUTION_NOT_PROOF_OF_OPTIMALITY",),
            policy=policy.to_dict(),
        )

    return PortfolioRaceDecision(
        source.fingerprint,
        "INCONCLUSIVE",
        ignored_entry_ids=tuple(ignored),
        diagnostics=("NO_DECISIVE_CERTIFICATE_OR_VALIDATED_SOLUTION",),
        policy=policy.to_dict(),
    )


class AASMEngine(V53Engine):
    """Experimental v0.54 effect-governance runtime over the full v0.53 composition.

    This layer does not replace the historical effect executor, TaskLease,
    resource reservation, scoped authority, or solver-learning planes. It binds
    them into one explicit intent -> dispatch -> ownership -> outcome lifecycle.
    """

    def effect_governance_runtime_contract_report(self) -> dict[str, Any]:
        return effect_governance_runtime_contract()

    def solver_portfolio_contract_report(self) -> dict[str, Any]:
        return solver_portfolio_contract()

    def _record_effect_governance_document(
        self,
        *,
        record_type: str,
        object_id: str,
        document: Mapping[str, Any],
        source: str,
        derived_from=(),
        reason: str,
    ) -> str:
        payload = deepcopy(dict(document))
        identity = {"record_type": record_type, "object_id": object_id, "document": payload}
        evidence_id = f"effect-governance-evidence-{semantic_fingerprint(identity)[:24]}"
        for row in self.snapshot.evidence.get("records", []):
            if row.get("evidence_id") != evidence_id:
                continue
            metadata = row.get("metadata") or {}
            if metadata.get(_EFFECT_GOVERNANCE_RECORD_TYPE) != record_type or metadata.get(_EFFECT_GOVERNANCE_DOCUMENT) != payload:
                raise ValueError(f"effect governance Evidence collision: {evidence_id}")
            return evidence_id
        record = EvidenceRecord(
            kind="effect_governance",
            statement=canonical_semantic_json(payload),
            source=source,
            derived_from=list(sorted(set(map(str, derived_from)))),
            metadata={
                _EFFECT_GOVERNANCE_RECORD_TYPE: record_type,
                "object_id": object_id,
                _EFFECT_GOVERNANCE_DOCUMENT: payload,
                "authority": "EVIDENCE_ONLY",
            },
            evidence_id=evidence_id,
        )
        guarded = getattr(self, "add_evidence_guarded", None)
        if guarded is not None:
            guarded(
                record,
                expected_machine_version=self.snapshot.version,
                reason=reason,
            )
        else:
            self.add_evidence(record, reason=reason)
        return evidence_id

    def _local_evidence_ids(self) -> set[str]:
        return {
            str(row.get("evidence_id"))
            for row in self.snapshot.evidence.get("records", [])
            if row.get("evidence_id")
        }

    def _require_local_evidence_ids(self, evidence_ids: Iterable[str]) -> tuple[str, ...]:
        ids = tuple(sorted(set(map(str, evidence_ids))))
        missing = sorted(set(ids) - self._local_evidence_ids())
        if missing:
            raise KeyError(f"effect reconciliation Evidence is not local: {missing}")
        return ids

    def _effect_governance_rows(
        self,
        *,
        workspace_id: str,
        scope_id: str | None = None,
        record_types: Iterable[str] | None = None,
        effect_id: str | None = None,
    ) -> list[dict[str, Any]]:
        allowed = None if record_types is None else set(map(str, record_types))
        rows = []
        for row in self.snapshot.evidence.get("records", []):
            if row.get("status", "active") != "active":
                continue
            metadata = row.get("metadata") or {}
            record_type = metadata.get(_EFFECT_GOVERNANCE_RECORD_TYPE)
            if not record_type or (allowed is not None and record_type not in allowed):
                continue
            document = metadata.get(_EFFECT_GOVERNANCE_DOCUMENT)
            if not isinstance(document, dict) or document.get("workspace_id") != workspace_id:
                continue
            if scope_id is not None and document.get("scope_id") != scope_id:
                continue
            if effect_id is not None and document.get("effect_id") != effect_id:
                continue
            rows.append(
                {
                    "record_type": record_type,
                    "evidence_id": row.get("evidence_id"),
                    "document": deepcopy(document),
                    "derived_from": list(row.get("derived_from") or []),
                }
            )
        return rows

    def _reservation_context(
        self,
        reservation_ids: Iterable[str],
        *,
        workspace_id: str,
        scope_id: str,
        require_active: bool = True,
    ) -> dict[str, dict[str, Any]]:
        ids = tuple(sorted(set(map(str, reservation_ids))))
        if not ids:
            return {}
        report = self.resource_governance_report(workspace_id=workspace_id, scope_id=scope_id)
        out = {}
        for reservation_id in ids:
            try:
                reservation = report["reservations"][reservation_id]
            except KeyError:
                raise KeyError(f"effect references unknown or inaccessible resource reservation: {reservation_id}") from None
            if require_active and reservation.get("status") != "ACTIVE":
                raise ValueError(f"effect resource reservation is not ACTIVE: {reservation_id}")
            out[reservation_id] = deepcopy(reservation)
        return out

    def _resource_reservation_evidence_ids(self, reservation_ids: Iterable[str]) -> list[str]:
        wanted = set(map(str, reservation_ids))
        if not wanted:
            return []
        found = []
        for row in self.snapshot.evidence.get("records", []):
            metadata = row.get("metadata") or {}
            if metadata.get("aasm_resource_record_type") != "routing_transaction":
                continue
            document = metadata.get("document")
            if not isinstance(document, dict):
                continue
            reservation = document.get("reservation")
            if isinstance(reservation, dict) and reservation.get("reservation_id") in wanted:
                found.append(str(row.get("evidence_id")))
        return sorted(set(found))

    def _require_v54_intent(self, effect_id: str, workspace_id: str, scope_id: str) -> EffectIntent:
        record = self.store.load_effect(self.snapshot.machine_id, effect_id)
        if record.intent is None:
            raise PermissionError(
                "effect has no v0.54 EffectIntent; explicit intent migration is required before v0.54 authorization or dispatch"
            )
        intent = EffectIntent.from_dict(record.intent)
        if intent.workspace_id != workspace_id or intent.scope_id != scope_id:
            raise PermissionError("effect intent crosses workspace/scope boundary")
        self._require_effect_context(effect_id, workspace_id, scope_id)
        return intent

    def propose_effect(
        self,
        spec,
        *,
        workspace_id: str | None = None,
        scope_id: str | None = None,
        proposer_principal_id: str | None = None,
        resource_reservation_ids=(),
        intent_metadata: Mapping[str, Any] | None = None,
    ):
        if not workspace_id or not scope_id:
            raise PermissionError("v0.54 effect proposal requires workspace_id and scope_id")
        reservation_ids = tuple(sorted(set(map(str, resource_reservation_ids))))
        self._reservation_context(
            reservation_ids,
            workspace_id=workspace_id,
            scope_id=scope_id,
            require_active=True,
        )
        record = super().propose_effect(
            spec,
            workspace_id=workspace_id,
            scope_id=scope_id,
            proposer_principal_id=proposer_principal_id,
        )
        requested_intent = EffectIntent.from_spec(
            record.spec,
            workspace_id=workspace_id,
            scope_id=scope_id,
            resource_reservation_ids=reservation_ids,
            proposer_principal_id=proposer_principal_id,
            metadata=intent_metadata,
        )
        if record.intent is not None:
            intent = EffectIntent.from_dict(record.intent)
            if intent.fingerprint != requested_intent.fingerprint:
                raise ValueError("idempotent effect reuse conflicts with the existing v0.54 EffectIntent")
        else:
            if record.status != EffectStatus.PROPOSED.value:
                raise PermissionError("existing pre-v0.54 effect must be explicitly migrated before attaching an EffectIntent")
            intent = requested_intent
            record.intent = intent.to_dict()
            self.store.save_effect(record)
        proposal_context = self._effect_context(record.spec.effect_id)
        lineage = [proposal_context["evidence_id"], *self._resource_reservation_evidence_ids(reservation_ids)]
        evidence_id = self._record_effect_governance_document(
            record_type="effect_intent",
            object_id=intent.intent_id,
            document=intent.to_dict(),
            source=EFFECT_INTENT_CONTRACT_ID,
            derived_from=lineage,
            reason="v0.54 EffectIntent recorded",
        )
        record = self.store.load_effect(self.snapshot.machine_id, record.spec.effect_id)
        if evidence_id not in record.evidence:
            record.evidence.append(evidence_id)
            self.store.save_effect(record)
        return record

    def authorize_effect(
        self,
        effect_id,
        authority="controller",
        *,
        workspace_id: str | None = None,
        scope_id: str | None = None,
        actor_principal_id: str | None = None,
        at_time: float = 0.0,
    ):
        if not workspace_id or not scope_id:
            raise PermissionError("v0.54 effect authorization requires workspace_id and scope_id")
        intent = self._require_v54_intent(effect_id, workspace_id, scope_id)
        self._reservation_context(
            intent.resource_reservation_ids,
            workspace_id=workspace_id,
            scope_id=scope_id,
            require_active=True,
        )
        return super().authorize_effect(
            effect_id,
            authority=authority,
            workspace_id=workspace_id,
            scope_id=scope_id,
            actor_principal_id=actor_principal_id,
            at_time=at_time,
        )

    def _active_effect_lease(self, lease_id: str, owner_worker_id: str) -> dict[str, Any]:
        lease = next((deepcopy(row) for row in self.list_leases() if row.get("lease_id") == lease_id), None)
        if lease is None:
            raise KeyError(f"unknown TaskLease for effect dispatch: {lease_id}")
        if lease.get("status") != LeaseStatus.ACTIVE.value:
            raise ValueError(f"effect dispatch TaskLease is not ACTIVE: {lease_id}")
        if lease.get("worker_id") != owner_worker_id:
            raise PermissionError("effect dispatch worker does not own the supplied TaskLease")
        if float(lease.get("expires_at", 0)) <= now():
            raise ValueError(f"effect dispatch TaskLease is expired: {lease_id}")
        worker = next((row for row in self.list_workers() if row.get("worker_id") == owner_worker_id), None)
        if worker is None or worker.get("status") != "ACTIVE":
            raise ValueError(f"effect dispatch worker is not ACTIVE: {owner_worker_id}")
        return lease

    def _bind_dispatch_request(
        self,
        effect_id: str,
        *,
        workspace_id: str,
        scope_id: str,
        owner_worker_id: str,
        task_lease_id: str,
        owner_principal_id: str | None,
        metadata: Mapping[str, Any] | None,
    ) -> EffectDispatchRequest:
        intent = self._require_v54_intent(effect_id, workspace_id, scope_id)
        self._reservation_context(
            intent.resource_reservation_ids,
            workspace_id=workspace_id,
            scope_id=scope_id,
            require_active=True,
        )
        lease = self._active_effect_lease(task_lease_id, owner_worker_id)
        lease_effect_id = str((lease.get("metadata") or {}).get("effect_id") or "")
        if lease_effect_id and lease_effect_id != effect_id:
            raise PermissionError("TaskLease metadata binds it to a different effect")
        requested_dispatch = EffectDispatchRequest.from_intent(
            intent,
            owner_worker_id=owner_worker_id,
            task_lease_id=task_lease_id,
            owner_principal_id=owner_principal_id,
            metadata={"task_id": lease.get("task_id"), **dict(metadata or {})},
        )
        record = self.store.load_effect(self.snapshot.machine_id, effect_id)
        if record.status in {EffectStatus.RUNNING.value, EffectStatus.UNKNOWN.value}:
            raise ValueError(f"effect cannot accept a new dispatch request from status {record.status}")
        if record.dispatch_request is not None:
            dispatch = EffectDispatchRequest.from_dict(record.dispatch_request)
            if dispatch.fingerprint != requested_dispatch.fingerprint:
                dispatch = requested_dispatch
                record.dispatch_request = dispatch.to_dict()
                if not any(row.get("dispatch_request_id") == dispatch.dispatch_request_id for row in record.dispatch_history):
                    record.dispatch_history.append(dispatch.to_dict())
                self.store.save_effect(record)
        else:
            dispatch = requested_dispatch
            record.dispatch_request = dispatch.to_dict()
            if not any(row.get("dispatch_request_id") == dispatch.dispatch_request_id for row in record.dispatch_history):
                record.dispatch_history.append(dispatch.to_dict())
            self.store.save_effect(record)
        intent_rows = self._effect_governance_rows(
            workspace_id=workspace_id,
            scope_id=scope_id,
            record_types=("effect_intent",),
            effect_id=effect_id,
        )
        authorization = self._latest_effect_authorization(effect_id, workspace_id, scope_id)
        lineage = [authorization["evidence_id"], *[row["evidence_id"] for row in intent_rows]]
        evidence_id = self._record_effect_governance_document(
            record_type="effect_dispatch_request",
            object_id=dispatch.dispatch_request_id,
            document=dispatch.to_dict(),
            source=EFFECT_DISPATCH_REQUEST_CONTRACT_ID,
            derived_from=lineage,
            reason="v0.54 effect dispatch request recorded",
        )
        record = self.store.load_effect(self.snapshot.machine_id, effect_id)
        if evidence_id not in record.evidence:
            record.evidence.append(evidence_id)
            self.store.save_effect(record)
        return dispatch

    def execute_effect(
        self,
        effect_id,
        executor,
        *,
        workspace_id: str | None = None,
        scope_id: str | None = None,
        actor_principal_id: str | None = None,
        owner_worker_id: str | None = None,
        task_lease_id: str | None = None,
        at_time: float = 0.0,
        dispatch_metadata: Mapping[str, Any] | None = None,
    ):
        record = self.store.load_effect(self.snapshot.machine_id, effect_id)
        if record.status == EffectStatus.SUCCEEDED.value:
            return self._ensure_terminal_reconciliation(record)
        if record.status == EffectStatus.UNKNOWN.value:
            raise EffectUnknownOutcome(
                f"Effect {effect_id} has an unknown prior outcome; explicit scoped reconciliation is required before any new ownership"
            )
        if not workspace_id or not scope_id or not owner_worker_id or not task_lease_id:
            raise PermissionError(
                "v0.54 effect dispatch requires workspace_id, scope_id, owner_worker_id, and task_lease_id"
            )
        self._bind_dispatch_request(
            effect_id,
            workspace_id=workspace_id,
            scope_id=scope_id,
            owner_worker_id=owner_worker_id,
            task_lease_id=task_lease_id,
            owner_principal_id=actor_principal_id,
            metadata=dispatch_metadata,
        )
        result = super().execute_effect(
            effect_id,
            executor,
            workspace_id=workspace_id,
            scope_id=scope_id,
            actor_principal_id=actor_principal_id,
            at_time=at_time,
        )
        return self._ensure_terminal_reconciliation(result)

    def _effect_ownership_request_for_claim(self, effect_id):
        record = self.store.load_effect(self.snapshot.machine_id, effect_id)
        if record.intent is None or record.dispatch_request is None:
            raise PermissionError("v0.54 execution claim requires durable EffectIntent and EffectDispatchRequest")
        intent = EffectIntent.from_dict(record.intent)
        dispatch = EffectDispatchRequest.from_dict(record.dispatch_request)
        if dispatch.intent_id != intent.intent_id:
            raise ValueError("effect dispatch no longer matches durable EffectIntent")
        self._reservation_context(
            intent.resource_reservation_ids,
            workspace_id=intent.workspace_id,
            scope_id=intent.scope_id,
            require_active=True,
        )
        self._active_effect_lease(dispatch.task_lease_id, dispatch.owner_worker_id)
        rows = [
            row
            for row in self._effect_authority_rows("effect_execution_authority", effect_id)
            if row["document"].get("workspace_id") == intent.workspace_id
            and row["document"].get("scope_id") == intent.scope_id
        ]
        if not rows:
            raise PermissionError("v0.54 ownership requires the fresh v0.53 effect.execute authority decision")
        latest = rows[-1]
        authority_decision_evidence_id = str(latest["document"].get("authority_decision_evidence_id") or "")
        if not authority_decision_evidence_id:
            raise ValueError("effect execution authority binding lacks decision Evidence")
        return EffectOwnershipRequest.from_dispatch(
            dispatch,
            authority_decision_evidence_id=authority_decision_evidence_id,
            metadata={"execution_authority_binding_evidence_id": latest["evidence_id"]},
        )

    def _after_effect_claim(self, record):
        if record.ownership is None:
            raise PermissionError("v0.54 external dispatch is blocked without durable EffectOwnership")
        ownership = EffectOwnership.from_dict(record.ownership)
        if ownership.execution_id != record.execution_id:
            raise ValueError("EffectOwnership execution_id does not match the atomic effect claim")
        intent = EffectIntent.from_dict(record.intent)
        self._reservation_context(
            ownership.resource_reservation_ids,
            workspace_id=ownership.workspace_id,
            scope_id=ownership.scope_id,
            require_active=True,
        )
        self._active_effect_lease(ownership.task_lease_id or "", ownership.owner_worker_id)
        dispatch_rows = self._effect_governance_rows(
            workspace_id=ownership.workspace_id,
            scope_id=ownership.scope_id,
            record_types=("effect_dispatch_request",),
            effect_id=ownership.effect_id,
        )
        execution_binding = str(ownership.metadata.get("execution_authority_binding_evidence_id") or "")
        lineage = [
            ownership.authority_decision_evidence_id,
            execution_binding,
            *[row["evidence_id"] for row in dispatch_rows],
            *self._resource_reservation_evidence_ids(intent.resource_reservation_ids),
        ]
        evidence_id = self._record_effect_governance_document(
            record_type="effect_ownership",
            object_id=ownership.ownership_id,
            document=ownership.to_dict(),
            source=EFFECT_OWNERSHIP_CONTRACT_ID,
            derived_from=[row for row in lineage if row],
            reason="v0.54 atomic EffectOwnership recorded before external dispatch",
        )
        if evidence_id not in record.evidence:
            record.evidence.append(evidence_id)
            self.store.save_effect(record)
        return evidence_id

    def _record_reconciliation_evidence(
        self,
        record,
        reconciliation: EffectReconciliation,
        *,
        derived_from=(),
        reason: str,
    ) -> str:
        evidence_id = self._record_effect_governance_document(
            record_type="effect_reconciliation",
            object_id=reconciliation.reconciliation_id,
            document=reconciliation.to_dict(),
            source=EFFECT_RECONCILIATION_CONTRACT_ID,
            derived_from=derived_from,
            reason=reason,
        )
        current = self.store.load_effect(self.snapshot.machine_id, record.spec.effect_id)
        if evidence_id not in current.evidence:
            current.evidence.append(evidence_id)
            self.store.save_effect(current)
        return evidence_id

    def _ensure_terminal_reconciliation(self, record):
        if record.status not in {EffectStatus.SUCCEEDED.value, EffectStatus.FAILED.value}:
            return record
        current = self.store.load_effect(self.snapshot.machine_id, record.spec.effect_id)
        if current.ownership is None:
            return current
        ownership = EffectOwnership.from_dict(current.ownership)
        expected_outcome = EffectOutcome.CONFIRMED.value if current.status == EffectStatus.SUCCEEDED.value else EffectOutcome.FAILED.value
        local_ids = self._local_evidence_ids()
        durable_evidence_ids = tuple(sorted(set(row for row in current.evidence if row in local_ids)))
        existing = EffectReconciliation.from_dict(current.reconciliation) if current.reconciliation is not None else None
        if existing is not None and existing.outcome == expected_outcome and existing.ownership_id == ownership.ownership_id:
            reconciliation = existing
        else:
            reconciliation = EffectReconciliation(
                effect_id=current.spec.effect_id,
                outcome=expected_outcome,
                evidence_ids=durable_evidence_ids,
                ownership_id=ownership.ownership_id,
                reconciled_by_principal_id=ownership.owner_principal_id,
                authority_decision_evidence_id=ownership.authority_decision_evidence_id,
                result=deepcopy(current.result),
                error=current.error,
                metadata={"source": "executor_finalization", "execution_id": ownership.execution_id},
            )
            bind_effect_reconciliation(current, reconciliation)
            self.store.save_effect(current)
        ownership_rows = self._effect_governance_rows(
            workspace_id=ownership.workspace_id,
            scope_id=ownership.scope_id,
            record_types=("effect_ownership",),
            effect_id=ownership.effect_id,
        )
        self._record_reconciliation_evidence(
            current,
            reconciliation,
            derived_from=[ownership.authority_decision_evidence_id, *[row["evidence_id"] for row in ownership_rows]],
            reason="v0.54 effect terminal outcome recorded",
        )
        return self.store.load_effect(self.snapshot.machine_id, current.spec.effect_id)

    def reconcile_effect(
        self,
        effect_id,
        *,
        succeeded,
        result=None,
        evidence=None,
        error=None,
        workspace_id: str | None = None,
        scope_id: str | None = None,
        actor_principal_id: str | None = None,
        at_time: float = 0.0,
    ):
        if not workspace_id or not scope_id:
            raise PermissionError("v0.54 effect reconciliation requires workspace_id and scope_id")
        intent = self._require_v54_intent(effect_id, workspace_id, scope_id)
        before = self.store.load_effect(self.snapshot.machine_id, effect_id)
        if before.status != EffectStatus.UNKNOWN.value:
            raise ValueError("v0.54 explicit reconciliation is only valid for UNKNOWN effects")
        requested_evidence_ids = self._require_local_evidence_ids(evidence or ())
        merged_evidence = list(before.evidence)
        for evidence_id in requested_evidence_ids:
            if evidence_id not in merged_evidence:
                merged_evidence.append(evidence_id)
        reconciled = super().reconcile_effect(
            effect_id,
            succeeded=succeeded,
            result=result,
            evidence=merged_evidence,
            error=error,
            workspace_id=workspace_id,
            scope_id=scope_id,
            actor_principal_id=actor_principal_id,
            at_time=at_time,
        )
        authority_rows = [
            row
            for row in self._effect_authority_rows("effect_reconcile_authority", effect_id)
            if row["document"].get("workspace_id") == workspace_id
            and row["document"].get("scope_id") == scope_id
        ]
        if not authority_rows:
            raise ValueError("v0.54 reconciliation completed without a scoped reconciliation authority binding")
        latest = authority_rows[-1]
        decision_evidence_id = str(latest["document"].get("authority_decision_evidence_id") or "")
        current = self.store.load_effect(self.snapshot.machine_id, effect_id)
        ownership = EffectOwnership.from_dict(current.ownership) if current.ownership is not None else None
        local_ids = self._local_evidence_ids()
        durable_evidence_ids = tuple(sorted(set(row for row in current.evidence if row in local_ids)))
        reconciliation = EffectReconciliation(
            effect_id=effect_id,
            outcome=EffectOutcome.CONFIRMED.value if succeeded else EffectOutcome.FAILED.value,
            evidence_ids=durable_evidence_ids,
            ownership_id=None if ownership is None else ownership.ownership_id,
            reconciled_by_principal_id=actor_principal_id,
            authority_decision_evidence_id=decision_evidence_id,
            result=deepcopy(current.result),
            error=current.error,
            metadata={"source": "explicit_unknown_reconciliation"},
        )
        bind_effect_reconciliation(current, reconciliation)
        self.store.save_effect(current)
        self._record_reconciliation_evidence(
            current,
            reconciliation,
            derived_from=[latest["evidence_id"], decision_evidence_id, *reconciliation.evidence_ids],
            reason="v0.54 UNKNOWN effect explicitly reconciled",
        )
        self._reservation_context(
            intent.resource_reservation_ids,
            workspace_id=workspace_id,
            scope_id=scope_id,
            require_active=False,
        )
        return self.store.load_effect(self.snapshot.machine_id, effect_id)

    def effect_governance_report(self, *, workspace_id: str, scope_id: str | None = None) -> dict[str, Any]:
        self._workspace_authority_inputs(workspace_id)
        effects = {}
        intents = {}
        dispatches = {}
        ownerships = {}
        reconciliations = {}
        for record in self.store.list_effects(self.snapshot.machine_id):
            if record.intent is None:
                continue
            intent = EffectIntent.from_dict(record.intent)
            if intent.workspace_id != workspace_id or (scope_id is not None and intent.scope_id != scope_id):
                continue
            effect_id = record.spec.effect_id
            effects[effect_id] = {
                "status": record.status,
                "attempts": record.attempts,
                "execution_id": record.execution_id,
                "intent_id": intent.intent_id,
                "dispatch_request_id": None if record.dispatch_request is None else record.dispatch_request.get("dispatch_request_id"),
                "ownership_id": None if record.ownership is None else record.ownership.get("ownership_id"),
                "reconciliation_id": None if record.reconciliation is None else record.reconciliation.get("reconciliation_id"),
                "evidence": list(record.evidence),
            }
            intents[intent.intent_id] = intent.to_dict()
            for row in record.dispatch_history:
                dispatches[str(row["dispatch_request_id"])] = deepcopy(row)
            for row in record.ownership_history:
                ownerships[str(row["ownership_id"])] = deepcopy(row)
            for row in record.reconciliation_history:
                reconciliations[str(row["reconciliation_id"])] = deepcopy(row)
        evidence_rows = self._effect_governance_rows(
            workspace_id=workspace_id,
            scope_id=scope_id,
        )
        return {
            "contract": self.effect_governance_runtime_contract_report(),
            "access_context": {"workspace_id": workspace_id, "scope_id": scope_id},
            "effects": effects,
            "intents": intents,
            "dispatches": dispatches,
            "ownerships": ownerships,
            "reconciliations": reconciliations,
            "evidence_records": evidence_rows,
        }


__all__ = [
    "AASMEngine",
    "EFFECT_GOVERNANCE_RUNTIME_CONTRACT_ID",
    "EFFECT_GOVERNANCE_RUNTIME_CONTRACT_VERSION",
    "EFFECT_GOVERNANCE_RUNTIME_STABILITY",
    "effect_governance_runtime_contract",
    "SOLVER_TRANSLATION_CONTRACT_ID",
    "SOLVER_PORTFOLIO_CONTRACT_ID",
    "SOLVER_PORTFOLIO_CONTRACT_VERSION",
    "SOLVER_PORTFOLIO_STABILITY",
    "SOLVER_TRANSLATION_CHECKER_ID",
    "SOLVER_TRANSLATION_CHECKER_VERSION",
    "SolverTranslation",
    "SolverTranslationCertificate",
    "PortfolioRaceEntry",
    "PortfolioRacePolicy",
    "PortfolioRaceDecision",
    "solver_portfolio_contract",
    "translate_model_for_solver",
    "verify_solver_translation",
    "evaluate_portfolio_race",
]