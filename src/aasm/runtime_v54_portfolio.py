from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

from .evidence import EvidenceRecord
from .optimization import OPTIMIZATION_CAPABILITIES, OptimizationModel, OptimizationResult
from .proof_claims import SolverClaimCertificate
from .resources import TaskDemand
from .runtime_v54 import (
    AASMEngine as V54EffectEngine,
    PortfolioRaceDecision,
    PortfolioRaceEntry,
    PortfolioRacePolicy,
    SOLVER_PORTFOLIO_CONTRACT_ID,
    SOLVER_PORTFOLIO_CONTRACT_VERSION,
    SOLVER_PORTFOLIO_STABILITY,
    SolverTranslation,
    SolverTranslationCertificate,
    evaluate_portfolio_race,
    solver_portfolio_contract,
    translate_model_for_solver,
)
from .scoped_authority import AuthorityRequest
from .semantic_result import canonical_semantic_json, semantic_fingerprint
from .typed_protocol import CapabilityProvider


SOLVER_PORTFOLIO_RUNTIME_CONTRACT_ID = "aasm.solver.portfolio.runtime.v1"
SOLVER_PORTFOLIO_RUNTIME_CONTRACT_VERSION = "0.1.0"
SOLVER_PORTFOLIO_RUNTIME_STABILITY = "FOUNDATION_EXPERIMENTAL"
SOLVER_PORTFOLIO_AUTHORITY_CAPABILITIES = {
    "prepare": "solver.portfolio.prepare",
    "evaluate": "solver.portfolio.evaluate",
}
_PORTFOLIO_RECORD_TYPE = "aasm_solver_portfolio_record_type"
_PORTFOLIO_DOCUMENT = "document"


def solver_portfolio_runtime_contract() -> dict[str, Any]:
    return {
        "contract_id": SOLVER_PORTFOLIO_RUNTIME_CONTRACT_ID,
        "contract_version": SOLVER_PORTFOLIO_RUNTIME_CONTRACT_VERSION,
        "stability": SOLVER_PORTFOLIO_RUNTIME_STABILITY,
        "portfolio_contract": solver_portfolio_contract(),
        "prepare_authority": SOLVER_PORTFOLIO_AUTHORITY_CAPABILITIES["prepare"],
        "evaluate_authority": SOLVER_PORTFOLIO_AUTHORITY_CAPABILITIES["evaluate"],
        "model_admission": "EXISTING_OPTIMIZATION_MODEL_EVIDENCE",
        "request_queue": "EXISTING_OPTIMIZATION_REQUEST_AND_TASKDEMAND",
        "execution_lease": "EXISTING_AASM_TASKLEASE",
        "provider_execution": "EXISTING_EXECUTE_OPTIMIZATION_LEASE",
        "result_commit": "EXISTING_OPTIMIZATION_RESULT_EVIDENCE",
        "proof_lookup": "EXISTING_V050_SOLVER_CLAIM_CERTIFICATES",
        "decision_authority": "EVIDENCE_ONLY",
        "truth_authority": "EXISTING_AASM_POLICY_ONLY",
        "parallel_scheduler": "NONE",
    }


@dataclass(frozen=True)
class SolverPortfolioPlan:
    workspace_id: str
    scope_id: str
    source_model_id: str
    source_model_fingerprint: str
    requester_id: str
    policy: Mapping[str, Any]
    legs: tuple[Mapping[str, Any], ...]
    prepare_authority_evidence_id: str
    metadata: Mapping[str, Any] = field(default_factory=dict)
    portfolio_id: str = ""

    def __post_init__(self) -> None:
        for name in ("workspace_id", "scope_id", "source_model_id", "source_model_fingerprint", "requester_id", "prepare_authority_evidence_id"):
            if not str(getattr(self, name)).strip():
                raise ValueError(f"portfolio plan requires {name}")
        legs = tuple(sorted((deepcopy(dict(row)) for row in self.legs), key=lambda row: (str(row["provider_id"]), str(row["target_family"]))))
        providers = [str(row["provider_id"]) for row in legs]
        if len(legs) < 2 or len(providers) != len(set(providers)):
            raise ValueError("portfolio plan requires at least two unique provider legs")
        object.__setattr__(self, "legs", legs)
        if not self.portfolio_id:
            object.__setattr__(self, "portfolio_id", f"solver-portfolio-{semantic_fingerprint(self.identity_payload())[:24]}")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": SOLVER_PORTFOLIO_CONTRACT_ID,
            "contract_version": SOLVER_PORTFOLIO_CONTRACT_VERSION,
            "workspace_id": self.workspace_id,
            "scope_id": self.scope_id,
            "source_model_id": self.source_model_id,
            "source_model_fingerprint": self.source_model_fingerprint,
            "requester_id": self.requester_id,
            "policy": deepcopy(dict(self.policy)),
            "legs": [deepcopy(dict(row)) for row in self.legs],
            "prepare_authority_evidence_id": self.prepare_authority_evidence_id,
            "metadata": deepcopy(dict(self.metadata)),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"portfolio_id": self.portfolio_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"portfolio_id": self.portfolio_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SolverPortfolioPlan":
        payload = deepcopy(dict(value))
        payload.pop("fingerprint", None)
        payload.pop("contract_id", None)
        payload.pop("contract_version", None)
        payload["legs"] = tuple(payload.get("legs") or ())
        return cls(**payload)


def _policy_from_document(value: Mapping[str, Any]) -> PortfolioRacePolicy:
    keys = ("accept_best_feasible", "require_proof_for_negative", "require_proof_for_optimal", "objective_tolerance")
    return PortfolioRacePolicy(**{key: value[key] for key in keys if key in value})


def _certificate_from_document(value: Mapping[str, Any]) -> SolverClaimCertificate:
    payload = deepcopy(dict(value))
    payload.pop("fingerprint", None)
    payload["diagnostics"] = tuple(payload.get("diagnostics") or ())
    return SolverClaimCertificate(**payload)


class AASMEngine(V54EffectEngine):
    """Full experimental v0.54 composition: effect governance + governed portfolio execution."""

    def solver_portfolio_runtime_contract_report(self) -> dict[str, Any]:
        return solver_portfolio_runtime_contract()

    def _authorize_portfolio_action(
        self,
        *,
        actor_principal_id: str,
        workspace_id: str,
        scope_id: str,
        capability: str,
        at_time: float,
        portfolio_id: str = "",
    ) -> dict[str, Any]:
        result = self.authorize_scoped_request(
            AuthorityRequest(
                actor_principal_id,
                workspace_id,
                scope_id,
                capability,
                at_time=at_time,
                machine_id=self.snapshot.machine_id,
                metadata={"solver_portfolio_id": portfolio_id},
            ),
            reason=f"v0.54 solver portfolio authority evaluated: {capability}",
        )
        if not result["decision"]["allowed"]:
            raise PermissionError(f"v0.54 solver portfolio authority denied {capability}: {result['decision']['reason']}")
        return result

    def _record_portfolio_document(
        self,
        *,
        record_type: str,
        object_id: str,
        document: Mapping[str, Any],
        derived_from=(),
        reason: str,
    ) -> str:
        payload = deepcopy(dict(document))
        identity = {"record_type": record_type, "object_id": str(object_id), "document": payload}
        evidence_id = f"solver-portfolio-evidence-{semantic_fingerprint(identity)[:24]}"
        for row in self.snapshot.evidence.get("records", []):
            if row.get("evidence_id") != evidence_id:
                continue
            metadata = row.get("metadata") or {}
            if metadata.get(_PORTFOLIO_RECORD_TYPE) != record_type or metadata.get(_PORTFOLIO_DOCUMENT) != payload:
                raise ValueError(f"solver portfolio Evidence collision: {evidence_id}")
            return evidence_id
        record = EvidenceRecord(
            kind="solver_portfolio",
            statement=canonical_semantic_json(payload),
            source=SOLVER_PORTFOLIO_CONTRACT_ID,
            derived_from=list(sorted(set(map(str, derived_from)))),
            metadata={
                _PORTFOLIO_RECORD_TYPE: record_type,
                "object_id": str(object_id),
                _PORTFOLIO_DOCUMENT: payload,
                "authority": "EVIDENCE_ONLY",
            },
            evidence_id=evidence_id,
        )
        guarded = getattr(self, "add_evidence_guarded", None)
        if guarded is not None:
            guarded(record, expected_machine_version=self.snapshot.version, reason=reason)
        else:
            self.add_evidence(record, reason=reason)
        return evidence_id

    def _portfolio_rows(self, *, workspace_id: str, scope_id: str | None = None, record_type: str | None = None) -> list[dict[str, Any]]:
        self._workspace_authority_inputs(workspace_id)
        rows = []
        for row in self.snapshot.evidence.get("records", []):
            if row.get("status", "active") != "active":
                continue
            metadata = row.get("metadata") or {}
            current_type = metadata.get(_PORTFOLIO_RECORD_TYPE)
            if not current_type or (record_type is not None and current_type != record_type):
                continue
            document = metadata.get(_PORTFOLIO_DOCUMENT)
            if not isinstance(document, dict) or document.get("workspace_id") != workspace_id:
                continue
            if scope_id is not None and document.get("scope_id") != scope_id:
                continue
            rows.append({
                "record_type": current_type,
                "evidence_id": str(row.get("evidence_id")),
                "document": deepcopy(document),
                "derived_from": list(row.get("derived_from") or []),
            })
        return rows

    def solver_portfolio_report(self, *, workspace_id: str, scope_id: str | None = None, portfolio_id: str | None = None) -> dict[str, Any]:
        plans: dict[str, Any] = {}
        decisions: dict[str, list[dict[str, Any]]] = {}
        for row in self._portfolio_rows(workspace_id=workspace_id, scope_id=scope_id):
            if row["record_type"] == "plan":
                plan = SolverPortfolioPlan.from_dict(row["document"]["plan"])
                plans[plan.portfolio_id] = {"plan": plan.to_dict(), "evidence_id": row["evidence_id"]}
            elif row["record_type"] == "decision":
                pid = str(row["document"]["portfolio_id"])
                decisions.setdefault(pid, []).append({"decision": deepcopy(row["document"]["decision"]), "evidence_id": row["evidence_id"]})
        for values in decisions.values():
            values.sort(key=lambda row: row["decision"]["decision_id"])
        report = {
            "contract": solver_portfolio_runtime_contract(),
            "access_context": {"workspace_id": workspace_id, "scope_id": scope_id},
            "plans": plans,
            "decisions": decisions,
        }
        if portfolio_id is not None:
            if portfolio_id not in plans:
                raise KeyError(f"unknown solver portfolio in access context: {portfolio_id}")
            return {
                **report,
                "portfolio_id": portfolio_id,
                "plan": deepcopy(plans[portfolio_id]),
                "portfolio_decisions": deepcopy(decisions.get(portfolio_id, [])),
            }
        return report

    def prepare_solver_portfolio(
        self,
        source_model_id: str,
        targets: Sequence[Mapping[str, Any]],
        *,
        workspace_id: str,
        scope_id: str,
        actor_principal_id: str,
        requester_id: str,
        policy: PortfolioRacePolicy | None = None,
        timeout_ms: int = 30_000,
        accept_feasible: bool = True,
        environment_fingerprint: str = "",
        dependency_fingerprints: Sequence[str] = (),
        priority: int = 0,
        at_time: float = 0.0,
        metadata: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        self._workspace_authority_inputs(workspace_id)
        source_row = self.optimization_model_report(source_model_id)
        source = OptimizationModel.from_dict(source_row["model"])
        target_rows = [deepcopy(dict(row)) for row in targets]
        if len(target_rows) < 2:
            raise ValueError("solver portfolio requires at least two target providers")
        providers = self.capability_report()["providers"]
        compiled: list[dict[str, Any]] = []
        seen: set[str] = set()
        for target in sorted(target_rows, key=lambda row: (str(row.get("target_provider_id", "")), str(row.get("target_family", "")))):
            family = str(target.get("target_family") or "")
            provider_id = str(target.get("target_provider_id") or "")
            if not family or not provider_id:
                raise ValueError("portfolio target requires target_family and target_provider_id")
            if provider_id in seen:
                raise ValueError(f"duplicate portfolio provider: {provider_id}")
            seen.add(provider_id)
            try:
                provider = CapabilityProvider.from_dict(providers[provider_id]["provider"])
            except KeyError:
                raise KeyError(f"unknown optimization provider: {provider_id}") from None
            expected_capability = OPTIMIZATION_CAPABILITIES.get(family)
            if expected_capability is None or provider.capability_id != expected_capability:
                raise ValueError(f"portfolio provider {provider_id} does not implement target family {family}")
            translation, certificate = translate_model_for_solver(source, target_family=family, target_provider_id=provider_id)
            if certificate.status != "PASS":
                raise ValueError(f"portfolio translation did not certify for provider {provider_id}")
            compiled.append({
                "provider": provider,
                "translation": translation,
                "translation_certificate": certificate,
            })

        authorization = self._authorize_portfolio_action(
            actor_principal_id=actor_principal_id,
            workspace_id=workspace_id,
            scope_id=scope_id,
            capability=SOLVER_PORTFOLIO_AUTHORITY_CAPABILITIES["prepare"],
            at_time=at_time,
        )
        race_policy = policy or PortfolioRacePolicy()
        legs: list[dict[str, Any]] = []
        lineage = [source_row["evidence_id"], authorization["evidence_id"]]
        for row in compiled:
            translation: SolverTranslation = row["translation"]
            certificate: SolverTranslationCertificate = row["translation_certificate"]
            admitted_model = self.admit_optimization_model(
                translation.target_model,
                reason="v0.54 portfolio translated model admitted",
            )
            requested = self.request_optimization(
                translation.target_model.model_id,
                requester_id=requester_id,
                required_provider=translation.target_provider_id,
                timeout_ms=timeout_ms,
                accept_feasible=accept_feasible,
                environment_fingerprint=environment_fingerprint,
                dependency_fingerprints=dependency_fingerprints,
                priority=priority,
                reason="v0.54 portfolio leg requested",
            )
            lineage.extend([admitted_model["evidence_id"], requested["request_evidence_id"]])
            legs.append({
                "provider_id": translation.target_provider_id,
                "target_family": translation.target_family,
                "translation": translation.to_dict(),
                "translation_certificate": certificate.to_dict(),
                "target_model_id": translation.target_model.model_id,
                "target_model_fingerprint": translation.target_model.fingerprint,
                "target_model_evidence_id": admitted_model["evidence_id"],
                "request_id": requested["request"]["request_id"],
                "request_fingerprint": requested["request"]["fingerprint"],
                "request_evidence_id": requested["request_evidence_id"],
                "task": deepcopy(requested["task"]),
            })
        plan = SolverPortfolioPlan(
            workspace_id,
            scope_id,
            source.model_id,
            source.fingerprint,
            requester_id,
            race_policy.to_dict(),
            tuple(legs),
            authorization["evidence_id"],
            metadata=deepcopy(dict(metadata or {})),
        )
        evidence_id = self._record_portfolio_document(
            record_type="plan",
            object_id=plan.portfolio_id,
            document={
                "workspace_id": workspace_id,
                "scope_id": scope_id,
                "plan": plan.to_dict(),
            },
            derived_from=lineage,
            reason="v0.54 governed solver portfolio plan recorded",
        )
        return {"plan": plan.to_dict(), "evidence_id": evidence_id, "authority_decision_evidence_id": authorization["evidence_id"]}

    def _portfolio_plan_row(self, portfolio_id: str, *, workspace_id: str, scope_id: str) -> dict[str, Any]:
        report = self.solver_portfolio_report(workspace_id=workspace_id, scope_id=scope_id, portfolio_id=portfolio_id)
        return deepcopy(report["plan"])

    @staticmethod
    def _portfolio_leg(plan: SolverPortfolioPlan, provider_id: str) -> dict[str, Any]:
        for row in plan.legs:
            if row["provider_id"] == provider_id:
                return deepcopy(dict(row))
        raise KeyError(f"portfolio has no provider leg: {provider_id}")

    def claim_solver_portfolio_leg(
        self,
        portfolio_id: str,
        provider_id: str,
        worker_id: str,
        *,
        workspace_id: str,
        scope_id: str,
        lease_seconds: float = 300.0,
    ) -> dict[str, Any]:
        plan_row = self._portfolio_plan_row(portfolio_id, workspace_id=workspace_id, scope_id=scope_id)
        plan = SolverPortfolioPlan.from_dict(plan_row["plan"])
        leg = self._portfolio_leg(plan, provider_id)
        task = TaskDemand(**deepcopy(leg["task"]))
        lease = self.claim_task(task, worker_id, lease_seconds=lease_seconds)
        if lease.get("task_id") != task.task_id:
            raise ValueError("portfolio leg TaskLease does not bind the expected optimization task")
        return {"portfolio_id": portfolio_id, "provider_id": provider_id, "lease": deepcopy(lease), "task": deepcopy(leg["task"])}

    def execute_solver_portfolio_leg(
        self,
        portfolio_id: str,
        provider_id: str,
        lease_id: str,
        *,
        workspace_id: str,
        scope_id: str,
    ) -> dict[str, Any]:
        plan_row = self._portfolio_plan_row(portfolio_id, workspace_id=workspace_id, scope_id=scope_id)
        plan = SolverPortfolioPlan.from_dict(plan_row["plan"])
        leg = self._portfolio_leg(plan, provider_id)
        lease = next((deepcopy(row) for row in self.list_leases() if row.get("lease_id") == lease_id), None)
        if lease is None:
            raise KeyError(lease_id)
        if lease.get("task_id") != leg["task"]["task_id"]:
            raise PermissionError("TaskLease does not belong to the requested portfolio leg")
        result = self.execute_optimization_lease(lease_id)
        return {"portfolio_id": portfolio_id, "provider_id": provider_id, **result}

    def certify_solver_portfolio_leg(
        self,
        portfolio_id: str,
        provider_id: str,
        *,
        workspace_id: str,
        scope_id: str,
        max_states: int = 100_000,
    ) -> dict[str, Any]:
        plan_row = self._portfolio_plan_row(portfolio_id, workspace_id=workspace_id, scope_id=scope_id)
        plan = SolverPortfolioPlan.from_dict(plan_row["plan"])
        leg = self._portfolio_leg(plan, provider_id)
        result_rows = self.optimization_result_report(leg["request_id"])["results"]
        if len(result_rows) != 1:
            raise ValueError(f"portfolio leg requires exactly one committed result before certification: {provider_id}")
        result = OptimizationResult.from_dict(result_rows[0]["result"])
        model = OptimizationModel.from_dict(leg["translation"]["target_model"])
        return self.certify_optimization_claim(model, result, max_states=max_states)

    def _proof_certificate_for_result(self, result: OptimizationResult, model: OptimizationModel) -> tuple[SolverClaimCertificate | None, str | None]:
        matches = []
        for certificate_id, document in self.solver_proof_claim_report()["certificates"].items():
            if document.get("status") != "PASS" or document.get("verification_level") != "PROOF_CERTIFIED":
                continue
            if document.get("model_fingerprint") != model.fingerprint or document.get("result_fingerprint") != result.fingerprint:
                continue
            matches.append((str(certificate_id), _certificate_from_document(document)))
        if not matches:
            return None, None
        matches.sort(key=lambda row: row[0])
        return matches[0][1], matches[0][0]

    def evaluate_solver_portfolio(
        self,
        portfolio_id: str,
        *,
        workspace_id: str,
        scope_id: str,
        actor_principal_id: str,
        at_time: float = 0.0,
        policy: PortfolioRacePolicy | None = None,
        require_all_results: bool = True,
    ) -> dict[str, Any]:
        plan_row = self._portfolio_plan_row(portfolio_id, workspace_id=workspace_id, scope_id=scope_id)
        plan = SolverPortfolioPlan.from_dict(plan_row["plan"])
        source_row = self.optimization_model_report(plan.source_model_id)
        source = OptimizationModel.from_dict(source_row["model"])
        if source.fingerprint != plan.source_model_fingerprint:
            raise ValueError("portfolio source model fingerprint changed")

        pending: list[str] = []
        entries: list[PortfolioRaceEntry] = []
        result_evidence_ids: list[str] = []
        proof_evidence_ids: list[str] = []
        for leg in plan.legs:
            results = self.optimization_result_report(leg["request_id"])["results"]
            if not results:
                pending.append(str(leg["provider_id"]))
                continue
            if len(results) != 1:
                raise ValueError(f"portfolio leg has ambiguous committed results: {leg['provider_id']}")
            result = OptimizationResult.from_dict(results[0]["result"])
            translation = SolverTranslation.from_dict(leg["translation"])
            translation_certificate = SolverTranslationCertificate.from_dict(leg["translation_certificate"])
            request = self.optimization_request_report(leg["request_id"])["request"]
            model = translation.target_model
            proof, proof_evidence_id = self._proof_certificate_for_result(result, model)
            evidence_ids = [results[0]["evidence_id"]]
            if proof_evidence_id:
                evidence_ids.append(proof_evidence_id)
                proof_evidence_ids.append(proof_evidence_id)
            result_evidence_ids.append(results[0]["evidence_id"])
            entries.append(
                PortfolioRaceEntry(
                    translation,
                    translation_certificate,
                    request,
                    result,
                    proof_certificate=proof,
                    evidence_ids=tuple(evidence_ids),
                )
            )
        if pending and require_all_results:
            return {
                "contract": solver_portfolio_runtime_contract(),
                "portfolio_id": portfolio_id,
                "status": "PENDING",
                "pending_providers": sorted(pending),
                "recorded": False,
            }
        if not entries:
            return {
                "contract": solver_portfolio_runtime_contract(),
                "portfolio_id": portfolio_id,
                "status": "PENDING",
                "pending_providers": sorted(pending),
                "recorded": False,
            }

        authorization = self._authorize_portfolio_action(
            actor_principal_id=actor_principal_id,
            workspace_id=workspace_id,
            scope_id=scope_id,
            capability=SOLVER_PORTFOLIO_AUTHORITY_CAPABILITIES["evaluate"],
            at_time=at_time,
            portfolio_id=portfolio_id,
        )
        race_policy = policy or _policy_from_document(plan.policy)
        decision: PortfolioRaceDecision = evaluate_portfolio_race(source, entries, race_policy)
        document = {
            "workspace_id": workspace_id,
            "scope_id": scope_id,
            "portfolio_id": portfolio_id,
            "decision": decision.to_dict(),
            "entry_ids": sorted(row.entry_id for row in entries),
            "pending_providers": sorted(pending),
            "evaluate_authority_evidence_id": authorization["evidence_id"],
        }
        evidence_id = self._record_portfolio_document(
            record_type="decision",
            object_id=decision.decision_id,
            document=document,
            derived_from=[
                plan_row["evidence_id"],
                authorization["evidence_id"],
                *result_evidence_ids,
                *proof_evidence_ids,
            ],
            reason="v0.54 deterministic solver portfolio decision recorded",
        )
        return {
            "contract": solver_portfolio_runtime_contract(),
            "portfolio_id": portfolio_id,
            "status": decision.status,
            "decision": decision.to_dict(),
            "evidence_id": evidence_id,
            "authority_decision_evidence_id": authorization["evidence_id"],
            "recorded": True,
        }


__all__ = [
    "AASMEngine",
    "SOLVER_PORTFOLIO_RUNTIME_CONTRACT_ID",
    "SOLVER_PORTFOLIO_RUNTIME_CONTRACT_VERSION",
    "SOLVER_PORTFOLIO_RUNTIME_STABILITY",
    "SOLVER_PORTFOLIO_AUTHORITY_CAPABILITIES",
    "SolverPortfolioPlan",
    "solver_portfolio_runtime_contract",
]
