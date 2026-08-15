from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Mapping

from .optimization import OptimizationModel
from .runtime_v54 import (
    SolverTranslation,
    SolverTranslationCertificate,
    verify_solver_translation,
)
from .runtime_v54_portfolio import AASMEngine as V54PortfolioEngine, SolverPortfolioPlan
from .scoped_authority import AuthorityRequest
from .semantic_result import semantic_fingerprint
from .solver_learning import (
    CORRECTNESS_SENSITIVE_KINDS,
    PERFORMANCE_HINT_KINDS,
    SolverLearningArtifact,
    SolverLearningValidation,
)
from ._runtime_v53_solver_learning import SOLVER_LEARNING_AUTHORITY_CAPABILITIES


SOLVER_EXCHANGE_CONTRACT_ID = "aasm.solver.exchange.v1"
SOLVER_EXCHANGE_CONTRACT_VERSION = "0.1.0"
SOLVER_EXCHANGE_STABILITY = "FOUNDATION_EXPERIMENTAL"
SOLVER_EXCHANGE_CHECKER_ID = "aasm.checker.solver-exchange.v1"
SOLVER_EXCHANGE_CHECKER_VERSION = "0.1.0"
SOLVER_EXCHANGE_AUTHORITY_CAPABILITY = "solver.portfolio.exchange"


def solver_exchange_contract() -> dict[str, Any]:
    return {
        "contract_id": SOLVER_EXCHANGE_CONTRACT_ID,
        "contract_version": SOLVER_EXCHANGE_CONTRACT_VERSION,
        "stability": SOLVER_EXCHANGE_STABILITY,
        "source_learning": "EXACT_LOCAL_PASS_VALIDATION_REQUIRED",
        "source_translation": "PASS_TRANSLATION_CERTIFICATE_REQUIRED",
        "target_translation": "PASS_TRANSLATION_CERTIFICATE_REQUIRED",
        "semantic_exchange": "PAYLOAD_REBOUND_TO_CERTIFIED_TARGET_MODEL",
        "target_validation": "EXISTING_V053_LOCAL_REVALIDATION_REQUIRED",
        "native_accelerator_exchange": "FORBIDDEN_ACROSS_SOLVERS",
        "application": "EXISTING_SOLVER_LEARNING_APPLY_PATH_ONLY",
        "truth_authority": "NONE",
        "policy_authority": "NONE",
        "cross_solver_agreement_grants_truth": False,
    }


@dataclass(frozen=True)
class SolverLearningExchangeCertificate:
    portfolio_id: str
    source_provider_id: str
    target_provider_id: str
    source_learning_id: str
    source_learning_fingerprint: str
    source_validation_id: str
    source_validation_fingerprint: str
    source_translation_certificate_id: str
    source_translation_certificate_fingerprint: str
    target_translation_certificate_id: str
    target_translation_certificate_fingerprint: str
    target_learning_id: str
    target_learning_fingerprint: str
    target_validation_id: str
    target_validation_fingerprint: str
    exact_semantic_translation: bool
    target_validation_status: str
    application_ready: bool
    status: str
    diagnostics: tuple[str, ...] = ()
    certificate_id: str = ""

    def __post_init__(self) -> None:
        if self.status not in {"PASS", "FAIL"}:
            raise ValueError("solver exchange certificate status must be PASS or FAIL")
        if self.status == "PASS" and (not self.exact_semantic_translation or self.target_validation_status != "PASS"):
            raise ValueError("passing solver exchange certificate requires exact translation and target PASS validation")
        object.__setattr__(self, "diagnostics", tuple(map(str, self.diagnostics)))
        if not self.certificate_id:
            object.__setattr__(self, "certificate_id", f"solver-exchange-certificate-{semantic_fingerprint(self.identity_payload())[:24]}")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": SOLVER_EXCHANGE_CONTRACT_ID,
            "contract_version": SOLVER_EXCHANGE_CONTRACT_VERSION,
            "portfolio_id": self.portfolio_id,
            "source_provider_id": self.source_provider_id,
            "target_provider_id": self.target_provider_id,
            "source_learning_id": self.source_learning_id,
            "source_learning_fingerprint": self.source_learning_fingerprint,
            "source_validation_id": self.source_validation_id,
            "source_validation_fingerprint": self.source_validation_fingerprint,
            "source_translation_certificate_id": self.source_translation_certificate_id,
            "source_translation_certificate_fingerprint": self.source_translation_certificate_fingerprint,
            "target_translation_certificate_id": self.target_translation_certificate_id,
            "target_translation_certificate_fingerprint": self.target_translation_certificate_fingerprint,
            "target_learning_id": self.target_learning_id,
            "target_learning_fingerprint": self.target_learning_fingerprint,
            "target_validation_id": self.target_validation_id,
            "target_validation_fingerprint": self.target_validation_fingerprint,
            "exact_semantic_translation": bool(self.exact_semantic_translation),
            "target_validation_status": self.target_validation_status,
            "application_ready": bool(self.application_ready),
            "status": self.status,
            "diagnostics": list(self.diagnostics),
            "truth_authority": "NONE",
            "policy_authority": "NONE",
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"certificate_id": self.certificate_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"certificate_id": self.certificate_id, **self.identity_payload(), "fingerprint": self.fingerprint}


class AASMEngine(V54PortfolioEngine):
    """Full experimental v0.54 composition including certified cross-solver learning exchange."""

    def solver_exchange_contract_report(self) -> dict[str, Any]:
        return solver_exchange_contract()

    def _exchange_rows(self, *, workspace_id: str, scope_id: str | None = None) -> list[dict[str, Any]]:
        return self._portfolio_rows(workspace_id=workspace_id, scope_id=scope_id, record_type="exchange")

    def solver_exchange_report(self, *, workspace_id: str, scope_id: str | None = None) -> dict[str, Any]:
        exchanges = {}
        for row in self._exchange_rows(workspace_id=workspace_id, scope_id=scope_id):
            certificate = deepcopy(row["document"]["certificate"])
            exchanges[certificate["certificate_id"]] = {
                "certificate": certificate,
                "source_artifact": deepcopy(row["document"]["source_artifact"]),
                "target_artifact": deepcopy(row["document"]["target_artifact"]),
                "target_validation": deepcopy(row["document"]["target_validation"]),
                "evidence_id": row["evidence_id"],
                "derived_from": list(row["derived_from"]),
            }
        return {
            "contract": solver_exchange_contract(),
            "access_context": {"workspace_id": workspace_id, "scope_id": scope_id},
            "exchanges": exchanges,
        }

    def _portfolio_translations(
        self,
        plan: SolverPortfolioPlan,
        source_provider_id: str,
        target_provider_id: str,
    ) -> tuple[dict[str, Any], dict[str, Any], SolverTranslation, SolverTranslationCertificate, SolverTranslation, SolverTranslationCertificate]:
        source_leg = self._portfolio_leg(plan, source_provider_id)
        target_leg = self._portfolio_leg(plan, target_provider_id)
        if source_provider_id == target_provider_id:
            raise ValueError("cross-solver exchange requires distinct source and target providers")
        source_translation = SolverTranslation.from_dict(source_leg["translation"])
        source_certificate = SolverTranslationCertificate.from_dict(source_leg["translation_certificate"])
        target_translation = SolverTranslation.from_dict(target_leg["translation"])
        target_certificate = SolverTranslationCertificate.from_dict(target_leg["translation_certificate"])
        source_model = OptimizationModel.from_dict(self.optimization_model_report(plan.source_model_id)["model"])
        rebuilt_source = verify_solver_translation(source_model, source_translation)
        rebuilt_target = verify_solver_translation(source_model, target_translation)
        if rebuilt_source.to_dict() != source_certificate.to_dict() or source_certificate.status != "PASS":
            raise ValueError("source solver translation certificate does not independently reproduce")
        if rebuilt_target.to_dict() != target_certificate.to_dict() or target_certificate.status != "PASS":
            raise ValueError("target solver translation certificate does not independently reproduce")
        if source_translation.source_semantic_fingerprint != target_translation.source_semantic_fingerprint:
            raise ValueError("source and target solver representations do not share one certified semantic model")
        return source_leg, target_leg, source_translation, source_certificate, target_translation, target_certificate

    def exchange_solver_learning(
        self,
        portfolio_id: str,
        source_provider_id: str,
        target_provider_id: str,
        source_learning_id: str,
        *,
        workspace_id: str,
        scope_id: str,
        actor_principal_id: str,
        at_time: float = 0.0,
        max_total_states: int = 100_000,
        max_states_per_step: int = 1_000,
    ) -> dict[str, Any]:
        plan_row = self._portfolio_plan_row(portfolio_id, workspace_id=workspace_id, scope_id=scope_id)
        plan = SolverPortfolioPlan.from_dict(plan_row["plan"])
        (
            source_leg,
            target_leg,
            source_translation,
            source_translation_certificate,
            target_translation,
            target_translation_certificate,
        ) = self._portfolio_translations(plan, source_provider_id, target_provider_id)

        source_artifact_row = self._solver_learning_artifact_row(
            source_learning_id,
            workspace_id=workspace_id,
            scope_id=scope_id,
        )
        source_artifact = SolverLearningArtifact.from_dict(source_artifact_row["document"]["artifact"])
        if source_artifact.learning_kind == "NATIVE_ACCELERATOR":
            raise ValueError("native accelerator state cannot be exchanged across solver providers")
        if source_artifact.model_fingerprint != source_translation.target_model.fingerprint:
            raise ValueError("source solver learning artifact does not belong to the source portfolio representation")
        if source_artifact.solver_family != source_translation.target_family:
            raise ValueError("source solver learning artifact family does not match the source portfolio representation")
        if source_artifact.provider_id and source_artifact.provider_id != source_provider_id:
            raise ValueError("source solver learning artifact provider does not match source portfolio provider")
        source_validation, source_validation_evidence_id = self._latest_solver_learning_validation(
            source_learning_id,
            workspace_id=workspace_id,
            scope_id=scope_id,
            artifact_fingerprint=source_artifact.fingerprint,
        )

        validation_access = self.evaluate_scoped_request(
            AuthorityRequest(
                actor_principal_id,
                workspace_id,
                scope_id,
                SOLVER_LEARNING_AUTHORITY_CAPABILITIES["validate"],
                at_time=at_time,
                machine_id=self.snapshot.machine_id,
                metadata={"solver_portfolio_id": portfolio_id, "exchange_target_provider_id": target_provider_id},
            )
        )
        if not validation_access.allowed:
            raise PermissionError("cross-solver exchange requires local solver.learning.validate authority for the target artifact")
        exchange_authorization = self._authorize_portfolio_action(
            actor_principal_id=actor_principal_id,
            workspace_id=workspace_id,
            scope_id=scope_id,
            capability=SOLVER_EXCHANGE_AUTHORITY_CAPABILITY,
            at_time=at_time,
            portfolio_id=portfolio_id,
        )

        target_artifact = SolverLearningArtifact(
            source_artifact.learning_kind,
            target_translation.target_model.fingerprint,
            target_translation.target_family,
            deepcopy(dict(source_artifact.payload)),
            source_result_fingerprint=source_artifact.source_result_fingerprint,
            source_evidence_ids=(str(source_artifact_row["evidence_id"]), str(source_validation_evidence_id)),
            source_validation="CERTIFIED_CROSS_SOLVER_EXCHANGE",
            provider_id=target_provider_id,
            environment_fingerprint=source_artifact.environment_fingerprint,
            dependency_fingerprints=source_artifact.dependency_fingerprints,
            metadata={
                **deepcopy(dict(source_artifact.metadata)),
                "exchange_portfolio_id": portfolio_id,
                "exchange_source_provider_id": source_provider_id,
                "exchange_target_provider_id": target_provider_id,
                "exchange_source_learning_id": source_artifact.learning_id,
                "exchange_source_learning_fingerprint": source_artifact.fingerprint,
                "source_translation_certificate_id": source_translation_certificate.certificate_id,
                "target_translation_certificate_id": target_translation_certificate.certificate_id,
                "truth_authority": "NONE",
                "policy_authority": "NONE",
            },
        )
        target_record = self.record_solver_learning_artifact(
            target_artifact,
            workspace_id=workspace_id,
            scope_id=scope_id,
            derived_from=[
                plan_row["evidence_id"],
                source_artifact_row["evidence_id"],
                source_validation_evidence_id,
                exchange_authorization["evidence_id"],
            ],
        )
        target_validation_result = self.revalidate_solver_learning(
            target_artifact.learning_id,
            target_translation.target_model,
            workspace_id=workspace_id,
            scope_id=scope_id,
            actor_principal_id=actor_principal_id,
            at_time=at_time,
            max_total_states=max_total_states,
            max_states_per_step=max_states_per_step,
        )
        target_validation = SolverLearningValidation.from_dict(target_validation_result["validation"])
        diagnostics: list[str] = []
        if target_validation.status != "PASS":
            diagnostics.append("TARGET_LOCAL_REVALIDATION_DID_NOT_PASS")
        exact_semantic_translation = bool(
            source_translation_certificate.status == "PASS"
            and target_translation_certificate.status == "PASS"
            and source_translation.source_semantic_fingerprint == target_translation.source_semantic_fingerprint
        )
        if not exact_semantic_translation:
            diagnostics.append("SOURCE_TARGET_SEMANTIC_TRANSLATION_MISMATCH")
        application_ready = False
        if target_validation.status == "PASS":
            if source_artifact.learning_kind in CORRECTNESS_SENSITIVE_KINDS:
                application_ready = target_validation.application_authority == "PRUNING_CERTIFIED_FOR_EXACT_MODEL"
            elif source_artifact.learning_kind in PERFORMANCE_HINT_KINDS:
                application_ready = bool(
                    target_validation.application_authority == "PERFORMANCE_HINT_ONLY"
                    and source_artifact.learning_kind in {"INCUMBENT", "WARM_START"}
                    and target_provider_id == "ortools-cp-sat"
                    and target_translation.target_family == "CP_SAT"
                )
        status = "PASS" if exact_semantic_translation and target_validation.status == "PASS" else "FAIL"
        certificate = SolverLearningExchangeCertificate(
            portfolio_id,
            source_provider_id,
            target_provider_id,
            source_artifact.learning_id,
            source_artifact.fingerprint,
            source_validation.validation_id,
            source_validation.fingerprint,
            source_translation_certificate.certificate_id,
            source_translation_certificate.fingerprint,
            target_translation_certificate.certificate_id,
            target_translation_certificate.fingerprint,
            target_artifact.learning_id,
            target_artifact.fingerprint,
            target_validation.validation_id,
            target_validation.fingerprint,
            exact_semantic_translation,
            target_validation.status,
            application_ready,
            status,
            diagnostics=tuple(diagnostics),
        )
        evidence_id = self._record_portfolio_document(
            record_type="exchange",
            object_id=certificate.certificate_id,
            document={
                "workspace_id": workspace_id,
                "scope_id": scope_id,
                "portfolio_id": portfolio_id,
                "certificate": certificate.to_dict(),
                "source_artifact": source_artifact.to_dict(),
                "target_artifact": target_artifact.to_dict(),
                "target_validation": target_validation.to_dict(),
                "exchange_authority_evidence_id": exchange_authorization["evidence_id"],
            },
            derived_from=[
                plan_row["evidence_id"],
                source_artifact_row["evidence_id"],
                source_validation_evidence_id,
                exchange_authorization["evidence_id"],
                target_record["evidence_id"],
                target_validation_result["evidence_id"],
            ],
            reason="v0.54 certified cross-solver learning exchange recorded",
        )
        return {
            "contract": solver_exchange_contract(),
            "certificate": certificate.to_dict(),
            "source_artifact": source_artifact.to_dict(),
            "target_artifact": target_artifact.to_dict(),
            "target_validation": target_validation.to_dict(),
            "target_artifact_evidence_id": target_record["evidence_id"],
            "target_validation_evidence_id": target_validation_result["evidence_id"],
            "evidence_id": evidence_id,
            "authority_decision_evidence_id": exchange_authorization["evidence_id"],
        }


__all__ = [
    "AASMEngine",
    "SOLVER_EXCHANGE_CONTRACT_ID",
    "SOLVER_EXCHANGE_CONTRACT_VERSION",
    "SOLVER_EXCHANGE_STABILITY",
    "SOLVER_EXCHANGE_CHECKER_ID",
    "SOLVER_EXCHANGE_CHECKER_VERSION",
    "SOLVER_EXCHANGE_AUTHORITY_CAPABILITY",
    "SolverLearningExchangeCertificate",
    "solver_exchange_contract",
]
