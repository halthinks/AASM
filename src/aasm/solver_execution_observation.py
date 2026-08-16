from __future__ import annotations

from dataclasses import dataclass, field
from importlib import metadata as importlib_metadata
import platform
import sys
from typing import Any, Mapping

from .convex_optimization import ConvexOptimizationRequest, ConvexOptimizationResult
from .optimization import OptimizationRequest, OptimizationResult
from .semantic_result import semantic_fingerprint


SOLVER_EXECUTION_OBSERVATION_CONTRACT_ID = "aasm.solver.execution-observation.internal.v1"
SOLVER_EXECUTION_OBSERVATION_CONTRACT_VERSION = "0.1.0"


def _package_version(name: str) -> str:
    try:
        return importlib_metadata.version(name)
    except importlib_metadata.PackageNotFoundError:
        return "unknown"


def runtime_platform_identity() -> dict[str, Any]:
    return {
        "python_implementation": platform.python_implementation(),
        "python_version": platform.python_version(),
        "python_executable_implementation": sys.implementation.name,
        "os": platform.system(),
        "os_release": platform.release(),
        "machine": platform.machine(),
    }


def runtime_environment_fingerprint() -> str:
    return semantic_fingerprint(runtime_platform_identity())


def _pair(metadata: Mapping[str, Any], name: str) -> tuple[str, str]:
    object_id = str(metadata.get(f"{name}_id") or "")
    fingerprint = str(metadata.get(f"{name}_fingerprint") or "")
    if bool(object_id) != bool(fingerprint):
        raise ValueError(f"{name}_id and {name}_fingerprint must be supplied together")
    return object_id, fingerprint


@dataclass(frozen=True)
class SolverExecutionObservation:
    adapter_id: str
    adapter_version: str
    requested_options: Mapping[str, Any]
    effective_options: Mapping[str, Any]
    worker_count: int | None
    thread_count: int | None
    environment_fingerprint: str
    platform_identity: Mapping[str, Any]
    library_identity: Mapping[str, Any]
    build_fingerprint: str = ""
    formulation_id: str = ""
    formulation_fingerprint: str = ""
    problem_revision_id: str = ""
    problem_revision_fingerprint: str = ""
    numeric_policy_id: str = ""
    numeric_policy_fingerprint: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_id": SOLVER_EXECUTION_OBSERVATION_CONTRACT_ID,
            "contract_version": SOLVER_EXECUTION_OBSERVATION_CONTRACT_VERSION,
            "adapter_id": self.adapter_id,
            "adapter_version": self.adapter_version,
            "requested_options": dict(self.requested_options),
            "effective_options": dict(self.effective_options),
            "worker_count": self.worker_count,
            "thread_count": self.thread_count,
            "environment_fingerprint": self.environment_fingerprint,
            "platform_identity": dict(self.platform_identity),
            "library_identity": dict(self.library_identity),
            "build_fingerprint": self.build_fingerprint,
            "formulation_id": self.formulation_id,
            "formulation_fingerprint": self.formulation_fingerprint,
            "problem_revision_id": self.problem_revision_id,
            "problem_revision_fingerprint": self.problem_revision_fingerprint,
            "numeric_policy_id": self.numeric_policy_id,
            "numeric_policy_fingerprint": self.numeric_policy_fingerprint,
            "metadata": dict(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(self.to_dict())


def execution_observation_for_optimization(request: OptimizationRequest, result: OptimizationResult) -> SolverExecutionObservation:
    if result.request_id != request.request_id or result.request_fingerprint != request.fingerprint:
        raise ValueError("execution observation result does not bind exact optimization request")
    provider = result.solver.provider_id
    metadata = dict(request.metadata or {})
    formulation_id, formulation_fp = _pair(metadata, "formulation")
    revision_id, revision_fp = _pair(metadata, "problem_revision")
    numeric_id, numeric_fp = _pair(metadata, "numeric_policy")
    platform_identity = runtime_platform_identity()
    environment_fingerprint = runtime_environment_fingerprint()
    shared = {
        "environment_fingerprint": environment_fingerprint,
        "platform_identity": platform_identity,
        "build_fingerprint": result.solver.fingerprint,
        "formulation_id": formulation_id,
        "formulation_fingerprint": formulation_fp,
        "problem_revision_id": revision_id,
        "problem_revision_fingerprint": revision_fp,
        "numeric_policy_id": numeric_id,
        "numeric_policy_fingerprint": numeric_fp,
        "metadata": {
            "declared_request_environment_fingerprint": request.environment_fingerprint,
            "source_result_fingerprint": result.fingerprint,
        },
    }
    if provider == "cadical":
        solver_name = str(result.solver.metadata.get("solver_name") or "cadical195")
        options = {"solver_name": solver_name, "use_timer": True}
        return SolverExecutionObservation(
            "aasm.optimization.pysat-cadical", "0.1.0", options, options, 1, 1,
            library_identity={"python-sat": result.solver.version, "solver_implementation": result.solver.implementation},
            **shared,
        )
    if provider == "ortools-cp-sat":
        options = {
            "max_time_in_seconds": request.timeout_ms / 1000.0,
            "num_search_workers": 1,
            "random_seed": 0,
        }
        return SolverExecutionObservation(
            "aasm.optimization.ortools-cp-sat", "0.1.0", options, options, 1, 1,
            library_identity={"ortools": result.solver.version, "solver_implementation": result.solver.implementation},
            **shared,
        )
    if provider == "highs":
        options = {"output_flag": False, "time_limit": request.timeout_ms / 1000.0}
        return SolverExecutionObservation(
            "aasm.optimization.highs", "0.1.0", options, options, 1, None,
            library_identity={"highspy": result.solver.version, "solver_implementation": result.solver.implementation},
            metadata={**shared["metadata"], "thread_count_observation": "UNAVAILABLE_FROM_CURRENT_ADAPTER"},
            **{key: value for key, value in shared.items() if key != "metadata"},
        )
    raise ValueError(f"unsupported optimization provider for execution observation: {provider}")


def execution_observation_for_convex(request: ConvexOptimizationRequest, result: ConvexOptimizationResult) -> SolverExecutionObservation:
    if result.request_id != request.request_id or result.request_fingerprint != request.fingerprint:
        raise ValueError("execution observation result does not bind exact convex request")
    if result.solver.provider_id != "cvxpy":
        raise ValueError("v0.56.1 convex execution observation requires CVXPY provider")
    backend = result.solver.backend_solver
    platform_identity = runtime_platform_identity()
    options = {"solver": backend, "verbose": False, "warm_start": False}
    return SolverExecutionObservation(
        "aasm.optimization.cvxpy", "0.1.0",
        requested_options=options,
        effective_options=options,
        worker_count=1,
        thread_count=None,
        environment_fingerprint=runtime_environment_fingerprint(),
        platform_identity=platform_identity,
        library_identity={"cvxpy": result.solver.version, "backend_solver": backend},
        build_fingerprint=result.solver.fingerprint,
        metadata={
            "source_result_fingerprint": result.fingerprint,
            "thread_count_observation": "BACKEND_SPECIFIC_NOT_EXPOSED_BY_CURRENT_CVXPY_ADAPTER",
            "solver_stats": dict(result.statistics),
            "declared_request_environment_fingerprint": request.environment_fingerprint,
        },
    )


__all__ = [
    "SOLVER_EXECUTION_OBSERVATION_CONTRACT_ID",
    "SOLVER_EXECUTION_OBSERVATION_CONTRACT_VERSION",
    "SolverExecutionObservation",
    "runtime_platform_identity",
    "runtime_environment_fingerprint",
    "execution_observation_for_optimization",
    "execution_observation_for_convex",
]
