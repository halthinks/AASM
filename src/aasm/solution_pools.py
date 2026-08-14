from __future__ import annotations

from dataclasses import dataclass, field
from itertools import islice, product
from math import prod
from typing import Any, Iterable, Mapping, Sequence

from .optimization import (
    OPTIMIZATION_CAPABILITIES,
    BooleanLiteral,
    OptimizationConstraint,
    OptimizationModel,
    OptimizationRequest,
    OptimizationVariable,
    objective_value,
    solve_optimization_request,
    validate_optimization_solution,
)
from .proof_claims import FINITE_DOMAIN_CHECKER_ID, FINITE_DOMAIN_CHECKER_VERSION, SOLVER_PROOF_CONTRACT_ID
from .semantic_result import semantic_fingerprint


SOLUTION_POOL_CONTRACT_ID = "aasm.optimization.solution-pool.v1"
SOLUTION_POOL_CONTRACT_VERSION = "0.1.0"
ENUMERATION_CONTRACT_ID = "aasm.optimization.enumeration.v1"
ENUMERATION_CONTRACT_VERSION = "0.1.0"
SOLUTION_POOL_STABILITY = "EXPERIMENTAL_ENFORCED"
SOLUTION_POOL_MODES = (
    "COMPLETE_FINITE_ENUMERATION",
    "BOUNDED_PARTIAL_POOL",
    "TOP_K",
    "DIVERSE_POOL",
    "INCUMBENT_HISTORY",
)
POOL_COMPLETENESS_STATUSES = (
    "PARTIAL",
    "PARTIAL_NON_EXHAUSTIVE",
    "EXHAUSTED_PENDING_CERTIFICATION",
    "COMPLETE",
    "FAILED_COMPLETENESS",
)
ENUMERATION_CHECKER_ID = "aasm.checker.finite-enumeration-exhaustion.v1"
ENUMERATION_CHECKER_VERSION = "0.1.0"


class EnumerationUnsupportedError(ValueError):
    """The finite enumerator/checker cannot cover the requested model or budget."""


def solution_pool_contract() -> dict[str, Any]:
    return {
        "contract_id": SOLUTION_POOL_CONTRACT_ID,
        "contract_version": SOLUTION_POOL_CONTRACT_VERSION,
        "stability": SOLUTION_POOL_STABILITY,
        "modes": list(SOLUTION_POOL_MODES),
        "solution_identity": "MODEL_FINGERPRINT_PLUS_CANONICAL_ASSIGNMENT",
        "deduplication": "EXACT_CANONICAL_ASSIGNMENT_FINGERPRINT",
        "durability": "EXISTING_AASM_EVIDENCE_EVENT_HISTORY_ONLY",
        "scheduler": "EXISTING_AASM_TASKLEASE_ONLY",
        "solver_execution": "EXISTING_AASM_OPTIMIZATION_PROVIDERS_ONLY",
        "result_authority": "EVIDENCE_ONLY",
        "truth_authority": "EXISTING_AASM_POLICY_ONLY",
        "complete_requires_independent_exhaustion_certificate": True,
        "bounded_or_native_pool_implies_completeness": False,
        "duplicate_solution_counts_toward_completeness": False,
        "certificate_linkage": SOLVER_PROOF_CONTRACT_ID,
    }


def enumeration_contract() -> dict[str, Any]:
    return {
        "contract_id": ENUMERATION_CONTRACT_ID,
        "contract_version": ENUMERATION_CONTRACT_VERSION,
        "stability": SOLUTION_POOL_STABILITY,
        "complete_mode": "COMPLETE_FINITE_ENUMERATION",
        "finite_domains": ["BOOL", "INTEGER"],
        "continuous_domains": "UNSUPPORTED_FOR_COMPLETE_FINITE_ENUMERATION",
        "ordering": "LEXICOGRAPHIC_VARIABLE_ID_THEN_ASCENDING_DOMAIN_VALUE",
        "continuation": "DURABLE_NEXT_STATE_INDEX_CURSOR",
        "exclusions": "DURABLE_EXACT_ASSIGNMENT_NO_GOODS",
        "restart": "CURSOR_AND_POOL_RECONSTRUCTED_FROM_EXISTING_EVIDENCE_HISTORY",
        "completeness_checker": {
            "checker_id": ENUMERATION_CHECKER_ID,
            "checker_version": ENUMERATION_CHECKER_VERSION,
            "independent_of_solver": True,
            "algorithm": "FULL_FINITE_DOMAIN_RECONSTRUCTION_AND_SET_EQUALITY",
            "proof_checker_contract": {
                "contract_id": SOLVER_PROOF_CONTRACT_ID,
                "finite_domain_checker_id": FINITE_DOMAIN_CHECKER_ID,
                "finite_domain_checker_version": FINITE_DOMAIN_CHECKER_VERSION,
            },
        },
        "complete_claim_without_certificate": "REJECTED",
        "false_completeness": "FAIL_CLOSED",
        "cross_backend_consistency": "EXACT_SOLUTION_SET_EQUALITY_NEVER_VOTING",
    }


def _canonical_assignment(assignment: Mapping[str, float]) -> dict[str, float]:
    return {str(key): float(value) for key, value in sorted(assignment.items())}


def assignment_fingerprint(model_fingerprint: str, assignment: Mapping[str, float]) -> str:
    return semantic_fingerprint({"model_fingerprint": model_fingerprint, "assignment": _canonical_assignment(assignment)})


@dataclass(frozen=True)
class SolutionRecord:
    model_fingerprint: str
    assignment: Mapping[str, float]
    solver_provider_id: str = "aasm-finite-enumerator"
    objective: float | None = None
    lineage_ids: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)
    solution_id: str = ""

    def __post_init__(self):
        assignment = _canonical_assignment(self.assignment)
        if not self.model_fingerprint or not assignment:
            raise ValueError("solution record requires model fingerprint and assignment")
        object.__setattr__(self, "assignment", assignment)
        object.__setattr__(self, "lineage_ids", tuple(sorted(set(map(str, self.lineage_ids)))))
        object.__setattr__(self, "solution_id", self.solution_id or f"solution-{assignment_fingerprint(self.model_fingerprint, assignment)[:24]}")

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(self.to_dict(include_fingerprint=False))

    def to_dict(self, *, include_fingerprint: bool = True) -> dict[str, Any]:
        out = {
            "solution_id": self.solution_id,
            "model_fingerprint": self.model_fingerprint,
            "assignment": dict(self.assignment),
            "solver_provider_id": self.solver_provider_id,
            "objective": self.objective,
            "lineage_ids": list(self.lineage_ids),
            "metadata": dict(self.metadata),
        }
        if include_fingerprint:
            out["fingerprint"] = semantic_fingerprint(out)
        return out

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SolutionRecord":
        payload = dict(value); payload.pop("fingerprint", None); return cls(**payload)


@dataclass(frozen=True)
class SolutionExclusion:
    pool_id: str
    model_fingerprint: str
    solution_id: str
    assignment: Mapping[str, float]
    exclusion_id: str = ""

    def __post_init__(self):
        assignment = _canonical_assignment(self.assignment)
        if not all((self.pool_id, self.model_fingerprint, self.solution_id)):
            raise ValueError("solution exclusion requires pool/model/solution identity")
        object.__setattr__(self, "assignment", assignment)
        identity = {
            "pool_id": self.pool_id,
            "model_fingerprint": self.model_fingerprint,
            "solution_id": self.solution_id,
            "assignment_fingerprint": assignment_fingerprint(self.model_fingerprint, assignment),
            "kind": "EXACT_ASSIGNMENT_NO_GOOD",
        }
        object.__setattr__(self, "exclusion_id", self.exclusion_id or f"solution-exclusion-{semantic_fingerprint(identity)[:24]}")

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(self.to_dict(include_fingerprint=False))

    def to_dict(self, *, include_fingerprint: bool = True) -> dict[str, Any]:
        out = {
            "exclusion_id": self.exclusion_id,
            "pool_id": self.pool_id,
            "model_fingerprint": self.model_fingerprint,
            "solution_id": self.solution_id,
            "assignment": dict(self.assignment),
            "assignment_fingerprint": assignment_fingerprint(self.model_fingerprint, self.assignment),
            "kind": "EXACT_ASSIGNMENT_NO_GOOD",
        }
        if include_fingerprint:
            out["fingerprint"] = semantic_fingerprint(out)
        return out

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SolutionExclusion":
        payload = dict(value); payload.pop("fingerprint", None); payload.pop("assignment_fingerprint", None); payload.pop("kind", None); return cls(**payload)


@dataclass(frozen=True)
class EnumerationCursor:
    pool_id: str
    model_fingerprint: str
    mode: str
    next_state_index: int
    total_states: int
    accepted_solution_ids: tuple[str, ...] = ()
    exclusion_ids: tuple[str, ...] = ()
    exhausted: bool = False
    cursor_id: str = ""

    def __post_init__(self):
        if self.mode not in SOLUTION_POOL_MODES:
            raise ValueError(f"unsupported solution pool mode: {self.mode}")
        if int(self.next_state_index) < 0 or int(self.total_states) < 0 or int(self.next_state_index) > int(self.total_states):
            raise ValueError("invalid enumeration cursor bounds")
        object.__setattr__(self, "accepted_solution_ids", tuple(sorted(set(map(str, self.accepted_solution_ids)))))
        object.__setattr__(self, "exclusion_ids", tuple(sorted(set(map(str, self.exclusion_ids)))))
        identity = self._identity_payload()
        object.__setattr__(self, "cursor_id", self.cursor_id or f"enumeration-cursor-{semantic_fingerprint(identity)[:24]}")

    def _identity_payload(self) -> dict[str, Any]:
        return {
            "pool_id": self.pool_id,
            "model_fingerprint": self.model_fingerprint,
            "mode": self.mode,
            "next_state_index": int(self.next_state_index),
            "total_states": int(self.total_states),
            "accepted_solution_ids": list(self.accepted_solution_ids),
            "exclusion_ids": list(self.exclusion_ids),
            "exhausted": bool(self.exhausted),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(self.to_dict(include_fingerprint=False))

    def to_dict(self, *, include_fingerprint: bool = True) -> dict[str, Any]:
        out = {"cursor_id": self.cursor_id, **self._identity_payload()}
        if include_fingerprint:
            out["fingerprint"] = semantic_fingerprint(out)
        return out

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "EnumerationCursor":
        payload = dict(value); payload.pop("fingerprint", None); return cls(**payload)


@dataclass(frozen=True)
class SolutionPool:
    model_fingerprint: str
    mode: str
    solutions: tuple[SolutionRecord | Mapping[str, Any], ...] = ()
    exclusion_ids: tuple[str, ...] = ()
    completeness_status: str = "PARTIAL"
    cursor_fingerprint: str = ""
    completeness_certificate_id: str = ""
    lineage: Mapping[str, Any] = field(default_factory=dict)
    pool_id: str = ""

    def __post_init__(self):
        if self.mode not in SOLUTION_POOL_MODES:
            raise ValueError(f"unsupported solution pool mode: {self.mode}")
        if self.completeness_status not in POOL_COMPLETENESS_STATUSES:
            raise ValueError(f"unsupported completeness status: {self.completeness_status}")
        solutions = tuple(row if isinstance(row, SolutionRecord) else SolutionRecord.from_dict(row) for row in self.solutions)
        ids = [row.solution_id for row in solutions]
        if len(ids) != len(set(ids)):
            raise ValueError("solution pool cannot contain duplicate solution IDs")
        object.__setattr__(self, "solutions", tuple(sorted(solutions, key=lambda row: row.solution_id)))
        object.__setattr__(self, "exclusion_ids", tuple(sorted(set(map(str, self.exclusion_ids)))))
        stable_identity = {"model_fingerprint": self.model_fingerprint, "mode": self.mode, "lineage": dict(self.lineage)}
        object.__setattr__(self, "pool_id", self.pool_id or f"solution-pool-{semantic_fingerprint(stable_identity)[:24]}")
        if self.completeness_status == "COMPLETE" and not self.completeness_certificate_id:
            raise ValueError("COMPLETE solution pool requires a completeness certificate")

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(self.to_dict(include_fingerprint=False))

    def to_dict(self, *, include_fingerprint: bool = True) -> dict[str, Any]:
        out = {
            "pool_id": self.pool_id,
            "model_fingerprint": self.model_fingerprint,
            "mode": self.mode,
            "solutions": [row.to_dict() for row in self.solutions],
            "solution_ids": [row.solution_id for row in self.solutions],
            "exclusion_ids": list(self.exclusion_ids),
            "completeness_status": self.completeness_status,
            "cursor_fingerprint": self.cursor_fingerprint,
            "completeness_certificate_id": self.completeness_certificate_id,
            "lineage": dict(self.lineage),
        }
        if include_fingerprint:
            out["fingerprint"] = semantic_fingerprint(out)
        return out

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SolutionPool":
        payload = dict(value); payload.pop("fingerprint", None); payload.pop("solution_ids", None); return cls(**payload)


@dataclass(frozen=True)
class EnumerationCompletenessCertificate:
    pool_id: str
    model_fingerprint: str
    pool_fingerprint: str
    checker_id: str
    checker_version: str
    independent_of_solver: bool
    total_states: int
    feasible_count: int
    pool_solution_count: int
    unseen_solution_count: int
    duplicate_count: int
    trace_digest: str
    status: str
    diagnostics: tuple[str, ...] = ()
    certificate_id: str = ""

    def __post_init__(self):
        if self.status not in {"PASS", "FAIL", "UNSUPPORTED"}:
            raise ValueError(f"unsupported completeness certificate status: {self.status}")
        if self.status == "PASS" and not self.independent_of_solver:
            raise ValueError("passing completeness certificate requires independent checker")
        identity = self._identity_payload()
        object.__setattr__(self, "certificate_id", self.certificate_id or f"enumeration-certificate-{semantic_fingerprint(identity)[:24]}")

    def _identity_payload(self) -> dict[str, Any]:
        return {
            "pool_id": self.pool_id,
            "model_fingerprint": self.model_fingerprint,
            "pool_fingerprint": self.pool_fingerprint,
            "checker_id": self.checker_id,
            "checker_version": self.checker_version,
            "independent_of_solver": bool(self.independent_of_solver),
            "total_states": int(self.total_states),
            "feasible_count": int(self.feasible_count),
            "pool_solution_count": int(self.pool_solution_count),
            "unseen_solution_count": int(self.unseen_solution_count),
            "duplicate_count": int(self.duplicate_count),
            "trace_digest": self.trace_digest,
            "status": self.status,
            "diagnostics": list(self.diagnostics),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(self.to_dict(include_fingerprint=False))

    def to_dict(self, *, include_fingerprint: bool = True) -> dict[str, Any]:
        out = {"certificate_id": self.certificate_id, **self._identity_payload()}
        if include_fingerprint:
            out["fingerprint"] = semantic_fingerprint(out)
        return out


def _finite_domains(model: OptimizationModel) -> tuple[list[tuple[str, tuple[float, ...]]], int]:
    domains: list[tuple[str, tuple[float, ...]]] = []
    for variable in model.variables:
        if variable.domain == "CONTINUOUS":
            raise EnumerationUnsupportedError(f"complete finite enumeration does not support CONTINUOUS variable {variable.variable_id}")
        lo, hi = int(variable.lower_bound), int(variable.upper_bound)
        values = tuple(float(value) for value in range(lo, hi + 1))
        domains.append((variable.variable_id, values))
    return domains, prod(len(values) for _, values in domains)


def _bounded_domains(model: OptimizationModel, *, max_total_states: int) -> tuple[list[tuple[str, tuple[float, ...]]], int]:
    if int(max_total_states) <= 0:
        raise EnumerationUnsupportedError("enumeration state budget must be positive")
    domains, total = _finite_domains(model)
    if total > int(max_total_states):
        raise EnumerationUnsupportedError(f"enumeration state budget exceeded: {total} states > {int(max_total_states)}")
    return domains, total


def _assignment_rows(domains: Sequence[tuple[str, Sequence[float]]], start: int, stop: int) -> Iterable[dict[str, float]]:
    iterator = product(*(values for _, values in domains))
    for values in islice(iterator, int(start), int(stop)):
        yield {domains[index][0]: float(value) for index, value in enumerate(values)}


def initial_enumeration_cursor(model: OptimizationModel, pool_id: str, mode: str, *, max_total_states: int = 100_000) -> EnumerationCursor:
    _, total = _bounded_domains(model, max_total_states=max_total_states)
    return EnumerationCursor(pool_id, model.fingerprint, mode, 0, total, exhausted=(total == 0))


def enumerate_finite_step(
    model: OptimizationModel,
    pool_id: str,
    *,
    cursor: EnumerationCursor | None = None,
    existing_solutions: Sequence[SolutionRecord] = (),
    max_states_per_step: int = 1_000,
    max_total_states: int = 100_000,
) -> dict[str, Any]:
    if int(max_states_per_step) <= 0:
        raise ValueError("max_states_per_step must be positive")
    domains, total = _bounded_domains(model, max_total_states=max_total_states)
    cursor = cursor or initial_enumeration_cursor(model, pool_id, "COMPLETE_FINITE_ENUMERATION", max_total_states=max_total_states)
    if cursor.pool_id != pool_id or cursor.model_fingerprint != model.fingerprint:
        raise ValueError("stale or corrupted enumeration cursor does not bind the target pool/model")
    if cursor.total_states != total:
        raise ValueError("enumeration cursor total state count does not match current model")
    existing_by_id = {row.solution_id: row for row in existing_solutions}
    start = int(cursor.next_state_index)
    stop = min(total, start + int(max_states_per_step))
    accepted: list[SolutionRecord] = []
    exclusions: list[SolutionExclusion] = []
    trace: list[dict[str, Any]] = []
    for assignment in _assignment_rows(domains, start, stop):
        feasible = True
        try:
            validate_optimization_solution(model, assignment)
        except ValueError:
            feasible = False
        trace.append({"assignment": assignment, "feasible": feasible})
        if not feasible:
            continue
        record = SolutionRecord(
            model.fingerprint,
            assignment,
            objective=objective_value(model, assignment),
            metadata={"enumeration_state_index": start + len(trace) - 1},
        )
        if record.solution_id in existing_by_id:
            continue
        existing_by_id[record.solution_id] = record
        accepted.append(record)
        exclusions.append(SolutionExclusion(pool_id, model.fingerprint, record.solution_id, assignment))
    exhausted = stop >= total
    next_cursor = EnumerationCursor(
        pool_id,
        model.fingerprint,
        cursor.mode,
        stop,
        total,
        accepted_solution_ids=tuple(existing_by_id),
        exclusion_ids=tuple(sorted(set(cursor.exclusion_ids) | {row.exclusion_id for row in exclusions})),
        exhausted=exhausted,
    )
    return {
        "accepted": accepted,
        "exclusions": exclusions,
        "cursor": next_cursor,
        "states_examined": stop - start,
        "trace_digest": semantic_fingerprint(trace),
    }


def certify_complete_finite_enumeration(
    model: OptimizationModel,
    pool: SolutionPool,
    *,
    cursor: EnumerationCursor,
    max_total_states: int = 100_000,
) -> EnumerationCompletenessCertificate:
    domains, total = _bounded_domains(model, max_total_states=max_total_states)
    if pool.model_fingerprint != model.fingerprint or cursor.model_fingerprint != model.fingerprint or cursor.pool_id != pool.pool_id:
        raise ValueError("pool/cursor/model binding mismatch")
    trace: list[dict[str, Any]] = []
    oracle_ids: set[str] = set()
    for assignment in _assignment_rows(domains, 0, total):
        feasible = True
        try:
            validate_optimization_solution(model, assignment)
        except ValueError:
            feasible = False
        trace.append({"assignment": assignment, "feasible": feasible})
        if feasible:
            oracle_ids.add(f"solution-{assignment_fingerprint(model.fingerprint, assignment)[:24]}")
    pool_ids = [row.solution_id for row in pool.solutions]
    unique_pool_ids = set(pool_ids)
    duplicate_count = len(pool_ids) - len(unique_pool_ids)
    unseen = oracle_ids - unique_pool_ids
    foreign = unique_pool_ids - oracle_ids
    diagnostics: list[str] = []
    if pool.mode != "COMPLETE_FINITE_ENUMERATION":
        diagnostics.append("pool mode is not COMPLETE_FINITE_ENUMERATION")
    if not cursor.exhausted or cursor.next_state_index != total:
        diagnostics.append("enumeration cursor has not exhausted the finite state space")
    if duplicate_count:
        diagnostics.append(f"pool contains {duplicate_count} duplicate solution identities")
    if unseen:
        diagnostics.append(f"pool is missing {len(unseen)} feasible solutions")
    if foreign:
        diagnostics.append(f"pool contains {len(foreign)} solutions outside the oracle feasible set")
    status = "PASS" if not diagnostics else "FAIL"
    return EnumerationCompletenessCertificate(
        pool.pool_id,
        model.fingerprint,
        pool.fingerprint,
        ENUMERATION_CHECKER_ID,
        ENUMERATION_CHECKER_VERSION,
        True,
        total,
        len(oracle_ids),
        len(pool_ids),
        len(unseen),
        duplicate_count,
        semantic_fingerprint(trace),
        status,
        tuple(diagnostics),
    )


def _binary_no_good(model: OptimizationModel, assignment: Mapping[str, float], index: int) -> OptimizationConstraint:
    if any(row.domain != "BOOL" for row in model.variables):
        raise EnumerationUnsupportedError("native no-good consistency fixture currently requires BOOL variables")
    if model.solver_family == "SAT":
        literals = tuple(BooleanLiteral(row.variable_id, positive=(round(float(assignment[row.variable_id])) == 0)) for row in model.variables)
        return OptimizationConstraint("CLAUSE", literals=literals, metadata={"enumeration_no_good": index})
    coefficients: dict[str, float] = {}
    ones = 0
    for variable in model.variables:
        bit = int(round(float(assignment[variable.variable_id])))
        if bit:
            coefficients[variable.variable_id] = -1.0
            ones += 1
        else:
            coefficients[variable.variable_id] = 1.0
    return OptimizationConstraint(
        "LINEAR",
        coefficients=coefficients,
        sense=">=",
        rhs=float(1 - ones),
        metadata={"enumeration_no_good": index},
    )


def enumerate_native_binary_backend(
    model: OptimizationModel,
    provider_id: str,
    *,
    max_solutions: int = 10_000,
) -> dict[str, Any]:
    if max_solutions <= 0:
        raise ValueError("max_solutions must be positive")
    if any(row.domain != "BOOL" for row in model.variables):
        raise EnumerationUnsupportedError("native enumeration consistency currently requires binary models")
    current_constraints = list(model.constraints)
    found: dict[str, dict[str, float]] = {}
    result_lineage: list[str] = []
    exhausted = False
    for index in range(max_solutions + 1):
        current = OptimizationModel(
            f"{model.name}-enumeration-{index}",
            model.variables,
            tuple(current_constraints),
            objective=model.objective,
            family=model.family,
            metadata={**model.metadata, "enumeration_parent_fingerprint": model.fingerprint, "enumeration_iteration": index},
        )
        request = OptimizationRequest(
            current,
            OPTIMIZATION_CAPABILITIES[current.solver_family],
            "0.1.0",
            f"enumeration-native-{provider_id}-{index}",
            required_provider=provider_id,
            accept_feasible=True,
        )
        result = solve_optimization_request(request)
        result_lineage.append(result.result_id)
        if result.status in {"UNSAT", "INFEASIBLE"}:
            exhausted = True
            break
        if result.status not in {"SAT", "FEASIBLE", "OPTIMAL"}:
            return {"status": "INCONCLUSIVE", "provider_id": provider_id, "result_status": result.status, "solutions": found, "exhausted": False, "result_lineage": result_lineage}
        validate_optimization_solution(current, result.assignment)
        canonical = _canonical_assignment({key: result.assignment[key] for key in (row.variable_id for row in model.variables)})
        sid = f"solution-{assignment_fingerprint(model.fingerprint, canonical)[:24]}"
        if sid in found:
            return {"status": "FAIL", "provider_id": provider_id, "reason": "duplicate_native_solution_after_no_good", "solutions": found, "exhausted": False, "result_lineage": result_lineage}
        found[sid] = canonical
        if len(found) >= max_solutions:
            break
        current_constraints.append(_binary_no_good(current, result.assignment, index))
    return {
        "status": "PASS" if exhausted else "PARTIAL",
        "provider_id": provider_id,
        "solutions": found,
        "solution_ids": sorted(found),
        "exhausted": exhausted,
        "result_lineage": result_lineage,
    }


def binary_overlap_models() -> dict[str, OptimizationModel]:
    variables = (OptimizationVariable("x", "BOOL"), OptimizationVariable("y", "BOOL"), OptimizationVariable("z", "BOOL"))
    cp = OptimizationModel(
        "enumeration-overlap-cp-sat",
        variables,
        (OptimizationConstraint("LINEAR", coefficients={"x": 1, "y": 1, "z": 1}, sense=">=", rhs=1),),
        family="CP_SAT",
    )
    milp = OptimizationModel(
        "enumeration-overlap-milp",
        variables,
        (OptimizationConstraint("LINEAR", coefficients={"x": 1, "y": 1, "z": 1}, sense=">=", rhs=1),),
        family="MILP",
    )
    return {"CP_SAT": cp, "MILP": milp}


__all__ = [
    "SOLUTION_POOL_CONTRACT_ID", "SOLUTION_POOL_CONTRACT_VERSION", "ENUMERATION_CONTRACT_ID",
    "ENUMERATION_CONTRACT_VERSION", "SOLUTION_POOL_STABILITY", "SOLUTION_POOL_MODES",
    "POOL_COMPLETENESS_STATUSES", "ENUMERATION_CHECKER_ID", "ENUMERATION_CHECKER_VERSION",
    "EnumerationUnsupportedError", "SolutionRecord", "SolutionExclusion", "EnumerationCursor",
    "SolutionPool", "EnumerationCompletenessCertificate", "solution_pool_contract", "enumeration_contract",
    "assignment_fingerprint", "initial_enumeration_cursor", "enumerate_finite_step",
    "certify_complete_finite_enumeration", "enumerate_native_binary_backend", "binary_overlap_models",
]
