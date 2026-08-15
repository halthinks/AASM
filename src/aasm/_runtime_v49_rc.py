from __future__ import annotations

from .advanced_optimization import clear_incremental_sat_sessions
from .semantic_solver_rc import (
    build_semantic_solver_rc_freeze_manifest,
    run_claim_gate_audit,
    run_cross_backend_overlap_certification,
    run_rc_benchmarks,
    run_semantic_solver_rc_certification,
    run_upgrade_compatibility,
    semantic_solver_rc_contract,
)


class SemanticSolverRCRuntimeMixin:
    """v0.49 release-candidate assurance facade over the existing v0.48 runtime.

    This mixin adds no scheduler, authority plane, reducer, memory store, reuse
    path, or solver kernel. It exposes compatibility/freeze/certification
    reports over the already-released runtime.
    """

    def semantic_solver_rc_contract_report(self):
        return semantic_solver_rc_contract()

    def semantic_solver_rc_freeze_manifest(self, public_contract=None):
        return build_semantic_solver_rc_freeze_manifest(public_contract)

    def semantic_solver_rc_upgrade_report(self):
        return run_upgrade_compatibility(target_engine_cls=self.__class__)

    def semantic_solver_rc_cross_backend_report(self, *, real: bool = False):
        return run_cross_backend_overlap_certification(real=real)

    def semantic_solver_rc_benchmark_report(self, *, real: bool = False, iterations: int = 64):
        return run_rc_benchmarks(real=real, target_engine_cls=self.__class__, iterations=iterations)

    def semantic_solver_rc_claim_audit(self):
        return run_claim_gate_audit()

    def semantic_solver_rc_certify(self, *, real: bool = False, public_contract=None):
        # Certification must be independent of performance-only search state
        # left behind by earlier native solver runs in the same process.
        clear_incremental_sat_sessions()
        return run_semantic_solver_rc_certification(
            real=real,
            target_engine_cls=self.__class__,
            public_contract=public_contract,
        )


__all__ = ["SemanticSolverRCRuntimeMixin"]
