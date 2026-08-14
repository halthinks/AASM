from __future__ import annotations

from dataclasses import dataclass, field
from itertools import product
from math import prod
from typing import Any, Mapping

from .optimization import OptimizationModel, OptimizationResult, objective_value, validate_optimization_solution
from .semantic_result import semantic_fingerprint


SOLVER_PROOF_CONTRACT_ID = "aasm.solver.proof-certificate.v1"
SOLVER_PROOF_CONTRACT_VERSION = "0.1.0"
SOLVER_PROOF_STABILITY = "EXPERIMENTAL_ENFORCED"

SOLVER_CLAIM_TYPES = (
    "SAT", "UNSAT", "FEASIBLE", "INFEASIBLE", "BOUNDED", "UNBOUNDED", "OPTIMAL", "SUBOPTIMAL", "UNKNOWN",
)
PROOF_VERIFICATION_LEVELS = ("SOLVER_VALIDATED", "PROOF_CERTIFIED")
PROOF_CERTIFIABLE_CLAIMS = ("UNSAT", "INFEASIBLE", "OPTIMAL")
FINITE_DOMAIN_CHECKER_ID = "aasm.checker.finite-domain-exhaustive.v1"
FINITE_DOMAIN_CHECKER_VERSION = "0.1.0"


def solver_proof_contract() -> dict[str, Any]:
    return {
        "contract_id": SOLVER_PROOF_CONTRACT_ID,
        "contract_version": SOLVER_PROOF_CONTRACT_VERSION,
        "stability": SOLVER_PROOF_STABILITY,
        "claim_types": list(SOLVER_CLAIM_TYPES),
        "verification_levels": list(PROOF_VERIFICATION_LEVELS),
        "proof_certifiable_claims_v050": list(PROOF_CERTIFIABLE_CLAIMS),
        "solver_status_is_proof_grade": False,
        "proof_certified_requires_independent_checker": True,
        "exact_problem_binding_required": True,
        "exact_model_binding_required": True,
        "exact_result_binding_required": True,
        "failed_proof_promotes_claim": False,
        "unsupported_proof_promotes_claim": False,
        "certificate_authority": "EVIDENCE_ONLY",
        "truth_authority": "EXISTING_AASM_POLICY_ONLY",
        "initial_checker": {
            "checker_id": FINITE_DOMAIN_CHECKER_ID,
            "checker_version": FINITE_DOMAIN_CHECKER_VERSION,
            "scope": "BOUNDED_BOOL_INTEGER_EXHAUSTIVE",
            "continuous_variables": "UNSUPPORTED",
            "claim_scope": list(PROOF_CERTIFIABLE_CLAIMS),
        },
    }


@dataclass(frozen=True)
class SolverClaim:
    claim_type: str
    model_fingerprint: str
    result_fingerprint: str
    solver_provider_id: str
    problem_fingerprint: str = ""
    formulation_fingerprint: str = ""
    claimed_value: Any = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    claim_id: str = ""

    def __post_init__(self):
        if self.claim_type not in SOLVER_CLAIM_TYPES:
            raise ValueError(f"unsupported solver claim type: {self.claim_type}")
        if not self.model_fingerprint or not self.result_fingerprint or not self.solver_provider_id:
            raise ValueError("solver claim requires model/result/provider identity")
        object.__setattr__(self, "claim_id", self.claim_id or f"solver-claim-{semantic_fingerprint(self._identity_payload())[:24]}")

    def _identity_payload(self) -> dict[str, Any]:
        return {
            "claim_type": self.claim_type,
            "model_fingerprint": self.model_fingerprint,
            "result_fingerprint": self.result_fingerprint,
            "solver_provider_id": self.solver_provider_id,
            "problem_fingerprint": self.problem_fingerprint,
            "formulation_fingerprint": self.formulation_fingerprint,
            "claimed_value": self.claimed_value,
            "metadata": dict(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(self.to_dict(include_fingerprint=False))

    def to_dict(self, *, include_fingerprint: bool = True) -> dict[str, Any]:
        out = {"claim_id": self.claim_id, **self._identity_payload()}
        if include_fingerprint:
            out["fingerprint"] = semantic_fingerprint(out)
        return out


@dataclass(frozen=True)
class SolverProofArtifact:
    claim_id: str
    claim_fingerprint: str
    proof_format: str
    payload: Mapping[str, Any]
    producer_id: str
    producer_version: str
    artifact_id: str = ""

    def __post_init__(self):
        if not self.claim_id or not self.claim_fingerprint or not self.proof_format:
            raise ValueError("proof artifact requires exact claim identity and proof format")
        identity = {
            "claim_id": self.claim_id, "claim_fingerprint": self.claim_fingerprint, "proof_format": self.proof_format,
            "payload": dict(self.payload), "producer_id": self.producer_id, "producer_version": self.producer_version,
        }
        object.__setattr__(self, "artifact_id", self.artifact_id or f"solver-proof-{semantic_fingerprint(identity)[:24]}")

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(self.to_dict(include_fingerprint=False))

    def to_dict(self, *, include_fingerprint: bool = True) -> dict[str, Any]:
        out = {
            "artifact_id": self.artifact_id, "claim_id": self.claim_id, "claim_fingerprint": self.claim_fingerprint,
            "proof_format": self.proof_format, "payload": dict(self.payload), "producer_id": self.producer_id,
            "producer_version": self.producer_version,
        }
        if include_fingerprint:
            out["fingerprint"] = semantic_fingerprint(out)
        return out


@dataclass(frozen=True)
class SolverClaimCertificate:
    claim_id: str
    claim_fingerprint: str
    proof_artifact_id: str
    proof_artifact_fingerprint: str
    checker_id: str
    checker_version: str
    independent_of_solver: bool
    model_fingerprint: str
    result_fingerprint: str
    verification_level: str
    status: str
    coverage: Mapping[str, Any]
    diagnostics: tuple[str, ...] = ()
    certificate_id: str = ""

    def __post_init__(self):
        if self.verification_level not in PROOF_VERIFICATION_LEVELS:
            raise ValueError(f"unsupported verification level: {self.verification_level}")
        if self.status not in {"PASS", "FAIL", "UNSUPPORTED"}:
            raise ValueError(f"unsupported proof certificate status: {self.status}")
        if self.verification_level == "PROOF_CERTIFIED" and (self.status != "PASS" or not self.independent_of_solver):
            raise ValueError("PROOF_CERTIFIED requires a passing independent checker")
        object.__setattr__(self, "certificate_id", self.certificate_id or f"solver-certificate-{semantic_fingerprint(self._identity_payload())[:24]}")

    def _identity_payload(self) -> dict[str, Any]:
        return {
            "claim_id": self.claim_id, "claim_fingerprint": self.claim_fingerprint,
            "proof_artifact_id": self.proof_artifact_id, "proof_artifact_fingerprint": self.proof_artifact_fingerprint,
            "checker_id": self.checker_id, "checker_version": self.checker_version,
            "independent_of_solver": self.independent_of_solver, "model_fingerprint": self.model_fingerprint,
            "result_fingerprint": self.result_fingerprint, "verification_level": self.verification_level,
            "status": self.status, "coverage": dict(self.coverage), "diagnostics": list(self.diagnostics),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(self.to_dict(include_fingerprint=False))

    def to_dict(self, *, include_fingerprint: bool = True) -> dict[str, Any]:
        out = {"certificate_id": self.certificate_id, **self._identity_payload()}
        if include_fingerprint:
            out["fingerprint"] = semantic_fingerprint(out)
        return out


def claim_from_optimization_result(model: OptimizationModel, result: OptimizationResult, *, problem_fingerprint: str = "", formulation_fingerprint: str = "") -> SolverClaim:
    if result.model_fingerprint != model.fingerprint:
        raise ValueError("optimization result does not bind the supplied model")
    claim_type = result.status if result.status in SOLVER_CLAIM_TYPES else "UNKNOWN"
    claimed_value = result.objective_value if claim_type in {"OPTIMAL", "SUBOPTIMAL", "BOUNDED"} else None
    return SolverClaim(
        claim_type=claim_type, model_fingerprint=model.fingerprint, result_fingerprint=result.fingerprint,
        solver_provider_id=result.solver.provider_id, problem_fingerprint=problem_fingerprint,
        formulation_fingerprint=formulation_fingerprint or model.fingerprint, claimed_value=claimed_value,
        metadata={"result_id": result.result_id, "model_id": model.model_id},
    )


def _finite_domains(model: OptimizationModel) -> list[tuple[str, tuple[float, ...]]]:
    domains: list[tuple[str, tuple[float, ...]]] = []
    for variable in model.variables:
        if variable.domain == "BOOL":
            lo, hi = int(variable.lower_bound), int(variable.upper_bound)
            domains.append((variable.variable_id, tuple(float(value) for value in range(lo, hi + 1))))
            continue
        if variable.domain != "INTEGER":
            raise ValueError(f"finite-domain proof checker does not support {variable.domain} variable {variable.variable_id}")
        lo = int(variable.lower_bound); hi = int(variable.upper_bound)
        if float(lo) != float(variable.lower_bound) or float(hi) != float(variable.upper_bound):
            raise ValueError(f"integer variable {variable.variable_id} has non-integral bounds")
        domains.append((variable.variable_id, tuple(float(value) for value in range(lo, hi + 1))))
    return domains


def _enumerate_model(model: OptimizationModel, *, max_states: int) -> dict[str, Any]:
    domains = _finite_domains(model)
    state_count = prod(len(values) for _, values in domains)
    if state_count > int(max_states):
        raise ValueError(f"finite-domain proof budget exceeded: {state_count} states > {int(max_states)}")
    feasible: list[tuple[dict[str, float], float | None]] = []
    trace_rows: list[dict[str, Any]] = []
    for values in product(*(values for _, values in domains)):
        assignment = {domains[index][0]: float(value) for index, value in enumerate(values)}
        is_feasible = True
        try:
            validate_optimization_solution(model, assignment)
        except ValueError:
            is_feasible = False
        objective = objective_value(model, assignment) if is_feasible and model.objective is not None else None
        if is_feasible:
            feasible.append((assignment, objective))
        trace_rows.append({"assignment": assignment, "feasible": is_feasible, "objective": objective})
    return {
        "states_examined": state_count, "domain_sizes": {name: len(values) for name, values in domains},
        "feasible_count": len(feasible), "feasible": feasible, "trace_digest": semantic_fingerprint(trace_rows),
    }


def build_finite_domain_proof(model: OptimizationModel, result: OptimizationResult, *, max_states: int = 100_000, problem_fingerprint: str = "", formulation_fingerprint: str = "") -> tuple[SolverClaim, SolverProofArtifact]:
    claim = claim_from_optimization_result(model, result, problem_fingerprint=problem_fingerprint, formulation_fingerprint=formulation_fingerprint)
    if claim.claim_type not in PROOF_CERTIFIABLE_CLAIMS:
        raise ValueError(f"claim type {claim.claim_type} is not proof-certifiable by the v0.50 finite-domain checker")
    enumeration = _enumerate_model(model, max_states=max_states)
    feasible = enumeration.pop("feasible")
    payload: dict[str, Any] = {
        "checker_scope": "BOUNDED_BOOL_INTEGER_EXHAUSTIVE", "claim_type": claim.claim_type,
        "model_fingerprint": model.fingerprint, "result_fingerprint": result.fingerprint, **enumeration,
    }
    if claim.claim_type in {"UNSAT", "INFEASIBLE"}:
        if feasible:
            raise ValueError("negative solver claim is false: exhaustive checker found a feasible assignment")
        payload["conclusion"] = "NO_FEASIBLE_ASSIGNMENT"
    elif claim.claim_type == "OPTIMAL":
        if not feasible:
            raise ValueError("OPTIMAL solver claim is false: exhaustive checker found no feasible assignment")
        if model.objective is None:
            raise ValueError("OPTIMAL proof requires an objective")
        validate_optimization_solution(model, result.assignment)
        values = [float(value) for _, value in feasible if value is not None]
        optimum = min(values) if model.objective.sense == "MINIMIZE" else max(values)
        claimed = objective_value(model, result.assignment)
        if claimed is None or result.objective_value is None:
            raise ValueError("OPTIMAL proof requires a claimed objective value")
        if abs(float(claimed) - float(result.objective_value)) > 1e-9 or abs(float(optimum) - float(result.objective_value)) > 1e-9:
            raise ValueError("OPTIMAL solver claim is false: exhaustive checker found a different optimum")
        payload.update({"conclusion": "GLOBAL_OPTIMUM", "optimum": float(optimum), "sense": model.objective.sense})
    artifact = SolverProofArtifact(
        claim_id=claim.claim_id, claim_fingerprint=claim.fingerprint, proof_format="AASM_FINITE_DOMAIN_EXHAUSTIVE_V1",
        payload=payload, producer_id=FINITE_DOMAIN_CHECKER_ID, producer_version=FINITE_DOMAIN_CHECKER_VERSION,
    )
    return claim, artifact


def verify_finite_domain_proof(model: OptimizationModel, result: OptimizationResult, claim: SolverClaim, artifact: SolverProofArtifact, *, max_states: int = 100_000, checker_id: str = FINITE_DOMAIN_CHECKER_ID, checker_version: str = FINITE_DOMAIN_CHECKER_VERSION) -> SolverClaimCertificate:
    expected_claim = claim_from_optimization_result(model, result, problem_fingerprint=claim.problem_fingerprint, formulation_fingerprint=claim.formulation_fingerprint)
    if expected_claim.to_dict() != claim.to_dict():
        raise ValueError("solver claim is not exactly bound to model/result")
    if artifact.claim_id != claim.claim_id or artifact.claim_fingerprint != claim.fingerprint:
        raise ValueError("proof artifact is not exactly bound to solver claim")
    rebuilt_claim, rebuilt = build_finite_domain_proof(model, result, max_states=max_states, problem_fingerprint=claim.problem_fingerprint, formulation_fingerprint=claim.formulation_fingerprint)
    if rebuilt_claim.to_dict() != claim.to_dict() or rebuilt.payload != artifact.payload:
        raise ValueError("proof artifact failed independent deterministic recheck")
    if checker_id == result.solver.provider_id:
        raise ValueError("proof checker must be independent of the solver provider")
    coverage = {
        "claim_type": claim.claim_type, "proof_format": artifact.proof_format,
        "states_examined": artifact.payload["states_examined"], "model_fingerprint": model.fingerprint,
        "result_fingerprint": result.fingerprint, "exact_exhaustion": True,
    }
    return SolverClaimCertificate(
        claim_id=claim.claim_id, claim_fingerprint=claim.fingerprint, proof_artifact_id=artifact.artifact_id,
        proof_artifact_fingerprint=artifact.fingerprint, checker_id=checker_id, checker_version=checker_version,
        independent_of_solver=True, model_fingerprint=model.fingerprint, result_fingerprint=result.fingerprint,
        verification_level="PROOF_CERTIFIED", status="PASS", coverage=coverage,
    )


def certify_optimization_result(model: OptimizationModel, result: OptimizationResult, *, max_states: int = 100_000, problem_fingerprint: str = "", formulation_fingerprint: str = "") -> dict[str, Any]:
    claim = claim_from_optimization_result(model, result, problem_fingerprint=problem_fingerprint, formulation_fingerprint=formulation_fingerprint)
    if claim.claim_type not in PROOF_CERTIFIABLE_CLAIMS:
        return {"status": "UNSUPPORTED", "verification_level": "SOLVER_VALIDATED", "claim": claim.to_dict(), "proof_artifact": None, "certificate": None, "reason": f"claim type {claim.claim_type} has no v0.50 proof checker"}
    try:
        claim, artifact = build_finite_domain_proof(model, result, max_states=max_states, problem_fingerprint=problem_fingerprint, formulation_fingerprint=formulation_fingerprint)
        certificate = verify_finite_domain_proof(model, result, claim, artifact, max_states=max_states)
    except ValueError as exc:
        return {"status": "FAIL", "verification_level": "SOLVER_VALIDATED", "claim": claim.to_dict(), "proof_artifact": None, "certificate": None, "reason": str(exc)}
    return {"status": "PASS", "verification_level": certificate.verification_level, "claim": claim.to_dict(), "proof_artifact": artifact.to_dict(), "certificate": certificate.to_dict(), "reason": "independent exhaustive finite-domain proof verified"}
