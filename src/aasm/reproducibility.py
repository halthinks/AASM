from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from .optimization import OptimizationResult
from .semantic_result import semantic_fingerprint
from .solver_outcome_v2 import SolverOutcomeV2
from .solver_provenance_v2 import SolverProfileEvaluationV2, SolverRuntimeProvenanceV2


REPRODUCIBILITY_RUN_CONTRACT_ID = "aasm.solver.reproducibility-run.v1"
REPRODUCIBILITY_RUN_CONTRACT_VERSION = "0.1.0"
REPRODUCIBILITY_CERTIFICATE_CONTRACT_ID = "aasm.solver.reproducibility-certificate.v1"
REPRODUCIBILITY_CERTIFICATE_CONTRACT_VERSION = "0.1.0"
REPRODUCIBILITY_STABILITY = "FOUNDATION_EXPERIMENTAL"

REPRODUCIBILITY_CLAIM_LEVELS = (
    "NO_REPRODUCIBILITY_CLAIM",
    "CONFIGURATION_REPLAYABLE",
    "SEMANTIC_OUTCOME_REPRODUCED",
    "ASSIGNMENT_REPRODUCED",
    "OBJECTIVE_REPRODUCED",
    "PROOF_REPRODUCED",
    "ARTIFACT_REPRODUCED",
)


def _required(value: str, name: str) -> str:
    normalized = str(value).strip()
    if not normalized:
        raise ValueError(f"{name} is required")
    return normalized


def _uniq(values: Sequence[str]) -> tuple[str, ...]:
    return tuple(sorted(set(map(str, values))))


def _jsonable(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        return _jsonable(value.to_dict())
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))}
    if isinstance(value, (tuple, list, set)):
        return [_jsonable(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    raise TypeError(f"reproducibility value is not JSON serializable: {type(value)!r}")


@dataclass(frozen=True)
class ReproducibilityRun:
    result: OptimizationResult | Mapping[str, Any]
    outcome: SolverOutcomeV2 | Mapping[str, Any]
    provenance: SolverRuntimeProvenanceV2 | Mapping[str, Any]
    profile_evaluation: SolverProfileEvaluationV2 | Mapping[str, Any]
    semantic_projection_fingerprint: str = ""
    proof_fingerprint: str = ""
    artifact_fingerprint: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)
    run_id: str = ""
    contract_id: str = REPRODUCIBILITY_RUN_CONTRACT_ID
    contract_version: str = REPRODUCIBILITY_RUN_CONTRACT_VERSION

    def __post_init__(self) -> None:
        if self.contract_id != REPRODUCIBILITY_RUN_CONTRACT_ID or self.contract_version != REPRODUCIBILITY_RUN_CONTRACT_VERSION:
            raise ValueError("unsupported reproducibility-run contract")
        result = self.result if isinstance(self.result, OptimizationResult) else OptimizationResult.from_dict(self.result)
        outcome = self.outcome if isinstance(self.outcome, SolverOutcomeV2) else SolverOutcomeV2.from_dict(self.outcome)
        provenance = self.provenance if isinstance(self.provenance, SolverRuntimeProvenanceV2) else SolverRuntimeProvenanceV2.from_dict(self.provenance)
        if isinstance(self.profile_evaluation, SolverProfileEvaluationV2):
            evaluation = self.profile_evaluation
        else:
            payload = deepcopy(dict(self.profile_evaluation)); payload.pop("fingerprint", None); payload["deviations"] = tuple(payload.get("deviations") or ())
            evaluation = SolverProfileEvaluationV2(**payload)
        if outcome.source_result_id != result.result_id or outcome.source_result_fingerprint != result.fingerprint:
            raise ValueError("reproducibility run outcome does not bind exact result")
        if provenance.source_result_id != result.result_id or provenance.source_result_fingerprint != result.fingerprint:
            raise ValueError("reproducibility run provenance does not bind exact result")
        if provenance.source_outcome_id != outcome.outcome_id or provenance.source_outcome_fingerprint != outcome.fingerprint:
            raise ValueError("reproducibility run provenance does not bind exact outcome")
        if evaluation.provenance_id != provenance.provenance_id or evaluation.provenance_fingerprint != provenance.fingerprint:
            raise ValueError("reproducibility run profile evaluation does not bind exact provenance")
        object.__setattr__(self, "result", result)
        object.__setattr__(self, "outcome", outcome)
        object.__setattr__(self, "provenance", provenance)
        object.__setattr__(self, "profile_evaluation", evaluation)
        for name in ("semantic_projection_fingerprint", "proof_fingerprint", "artifact_fingerprint"):
            object.__setattr__(self, name, str(getattr(self, name)).strip())
        object.__setattr__(self, "metadata", _jsonable(dict(self.metadata)))
        if not self.run_id:
            object.__setattr__(self, "run_id", f"reproducibility-run-{semantic_fingerprint(self.identity_payload())[:24]}")

    @property
    def configuration_fingerprint(self) -> str:
        provenance = self.provenance
        return semantic_fingerprint({
            "profile_fingerprint": provenance.profile_fingerprint,
            "provider_id": provenance.provider_id,
            "provider_implementation": provenance.provider_implementation,
            "provider_version": provenance.provider_version,
            "adapter_id": provenance.adapter_id,
            "adapter_version": provenance.adapter_version,
            "solver_command": list(provenance.solver_command),
            "effective_options": _jsonable(provenance.effective_options),
            "environment_fingerprint": provenance.environment_fingerprint,
            "build_fingerprint": provenance.build_fingerprint,
            "provider_status_map_fingerprint": provenance.provider_status_map_fingerprint,
            "numeric_policy_fingerprint": provenance.numeric_policy_fingerprint,
            "dependency_fingerprints": list(provenance.dependency_fingerprints),
        })

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "result_id": self.result.result_id,
            "result_fingerprint": self.result.fingerprint,
            "outcome_id": self.outcome.outcome_id,
            "outcome_fingerprint": self.outcome.fingerprint,
            "provenance_id": self.provenance.provenance_id,
            "provenance_fingerprint": self.provenance.fingerprint,
            "profile_evaluation_id": self.profile_evaluation.evaluation_id,
            "profile_evaluation_fingerprint": self.profile_evaluation.fingerprint,
            "configuration_fingerprint": self.configuration_fingerprint,
            "semantic_projection_fingerprint": self.semantic_projection_fingerprint,
            "proof_fingerprint": self.proof_fingerprint,
            "artifact_fingerprint": self.artifact_fingerprint,
            "metadata": _jsonable(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"run_id": self.run_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"run_id": self.run_id, **self.identity_payload(), "fingerprint": self.fingerprint}


@dataclass(frozen=True)
class ReproducibilityCertificate:
    left_run_id: str
    left_run_fingerprint: str
    right_run_id: str
    right_run_fingerprint: str
    claim_level: str
    configuration_same: bool
    both_profile_compliant: bool
    model_same: bool
    normalized_status_same: bool
    semantic_projection_same: bool | None
    assignment_same: bool
    objective_same: bool | None
    proof_same: bool | None
    artifact_same: bool | None
    diagnostics: tuple[str, ...] = ()
    certificate_id: str = ""
    contract_id: str = REPRODUCIBILITY_CERTIFICATE_CONTRACT_ID
    contract_version: str = REPRODUCIBILITY_CERTIFICATE_CONTRACT_VERSION

    def __post_init__(self) -> None:
        for name in ("left_run_id", "left_run_fingerprint", "right_run_id", "right_run_fingerprint"):
            object.__setattr__(self, name, _required(getattr(self, name), name))
        if self.contract_id != REPRODUCIBILITY_CERTIFICATE_CONTRACT_ID or self.contract_version != REPRODUCIBILITY_CERTIFICATE_CONTRACT_VERSION:
            raise ValueError("unsupported reproducibility-certificate contract")
        if self.claim_level not in REPRODUCIBILITY_CLAIM_LEVELS:
            raise ValueError(f"invalid reproducibility claim level: {self.claim_level}")
        object.__setattr__(self, "diagnostics", _uniq(self.diagnostics))
        if self.claim_level != "NO_REPRODUCIBILITY_CLAIM" and not (self.configuration_same and self.both_profile_compliant):
            raise ValueError("reproducibility claim requires same configuration and compliant profiles")
        if not self.certificate_id:
            object.__setattr__(self, "certificate_id", f"reproducibility-certificate-{semantic_fingerprint(self.identity_payload())[:24]}")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "left_run_id": self.left_run_id,
            "left_run_fingerprint": self.left_run_fingerprint,
            "right_run_id": self.right_run_id,
            "right_run_fingerprint": self.right_run_fingerprint,
            "claim_level": self.claim_level,
            "configuration_same": bool(self.configuration_same),
            "both_profile_compliant": bool(self.both_profile_compliant),
            "model_same": bool(self.model_same),
            "normalized_status_same": bool(self.normalized_status_same),
            "semantic_projection_same": self.semantic_projection_same,
            "assignment_same": bool(self.assignment_same),
            "objective_same": self.objective_same,
            "proof_same": self.proof_same,
            "artifact_same": self.artifact_same,
            "diagnostics": list(self.diagnostics),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"certificate_id": self.certificate_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"certificate_id": self.certificate_id, **self.identity_payload(), "fingerprint": self.fingerprint}


def compare_reproducibility_runs(
    left: ReproducibilityRun,
    right: ReproducibilityRun,
) -> ReproducibilityCertificate:
    diagnostics: list[str] = []
    configuration_same = left.configuration_fingerprint == right.configuration_fingerprint
    both_profile_compliant = left.profile_evaluation.compliant and right.profile_evaluation.compliant
    model_same = left.result.model_fingerprint == right.result.model_fingerprint
    normalized_status_same = (
        left.outcome.solution_status == right.outcome.solution_status
        and left.outcome.optimality_claim == right.outcome.optimality_claim
        and left.outcome.incumbent_status == right.outcome.incumbent_status
    )
    assignment_same = bool(left.result.assignment) and left.result.assignment == right.result.assignment
    if left.result.objective_value is None or right.result.objective_value is None:
        objective_same = None
    else:
        objective_same = float(left.result.objective_value) == float(right.result.objective_value)
    if left.semantic_projection_fingerprint and right.semantic_projection_fingerprint:
        semantic_projection_same = left.semantic_projection_fingerprint == right.semantic_projection_fingerprint
    elif left.semantic_projection_fingerprint or right.semantic_projection_fingerprint:
        semantic_projection_same = False
    else:
        semantic_projection_same = None
    if left.proof_fingerprint and right.proof_fingerprint:
        proof_same = left.proof_fingerprint == right.proof_fingerprint
    elif left.proof_fingerprint or right.proof_fingerprint:
        proof_same = False
    else:
        proof_same = None
    if left.artifact_fingerprint and right.artifact_fingerprint:
        artifact_same = left.artifact_fingerprint == right.artifact_fingerprint
    elif left.artifact_fingerprint or right.artifact_fingerprint:
        artifact_same = False
    else:
        artifact_same = None

    if not configuration_same:
        diagnostics.append("CONFIGURATION_FINGERPRINT_DIFFERS")
    if not both_profile_compliant:
        diagnostics.append("PROFILE_NONCOMPLIANT")
    if not model_same:
        diagnostics.append("MODEL_FINGERPRINT_DIFFERS")
    if not normalized_status_same:
        diagnostics.append("NORMALIZED_STATUS_DIFFERS")
    if semantic_projection_same is False:
        diagnostics.append("SEMANTIC_PROJECTION_DIFFERS")
    if not assignment_same:
        diagnostics.append("ASSIGNMENT_DIFFERS_OR_ABSENT")
    if objective_same is False:
        diagnostics.append("OBJECTIVE_DIFFERS")
    if proof_same is False:
        diagnostics.append("PROOF_DIFFERS_OR_MISSING_PEER")
    if artifact_same is False:
        diagnostics.append("ARTIFACT_DIFFERS_OR_MISSING_PEER")

    claim = "NO_REPRODUCIBILITY_CLAIM"
    base_ok = configuration_same and both_profile_compliant
    if base_ok:
        claim = "CONFIGURATION_REPLAYABLE"
        semantic_ok = model_same and normalized_status_same and (
            semantic_projection_same is True or (semantic_projection_same is None and assignment_same)
        )
        if semantic_ok:
            claim = "SEMANTIC_OUTCOME_REPRODUCED"
            if assignment_same:
                claim = "ASSIGNMENT_REPRODUCED"
                if objective_same is True:
                    claim = "OBJECTIVE_REPRODUCED"
                    if proof_same is True:
                        claim = "PROOF_REPRODUCED"
                        if artifact_same is True:
                            claim = "ARTIFACT_REPRODUCED"
    return ReproducibilityCertificate(
        left.run_id,
        left.fingerprint,
        right.run_id,
        right.fingerprint,
        claim,
        configuration_same,
        both_profile_compliant,
        model_same,
        normalized_status_same,
        semantic_projection_same,
        assignment_same,
        objective_same,
        proof_same,
        artifact_same,
        tuple(diagnostics),
    )


def reproducibility_contract() -> dict[str, Any]:
    return {
        "run_contract_id": REPRODUCIBILITY_RUN_CONTRACT_ID,
        "certificate_contract_id": REPRODUCIBILITY_CERTIFICATE_CONTRACT_ID,
        "stability": REPRODUCIBILITY_STABILITY,
        "claim_levels": list(REPRODUCIBILITY_CLAIM_LEVELS),
        "profile_requirement": "BOTH_RUNS_COMPLIANT_FOR_ANY_POSITIVE_REPRODUCIBILITY_CLAIM",
        "configuration": "EXACT_FINGERPRINT_OVER_PROFILE_PROVIDER_ADAPTER_COMMAND_EFFECTIVE_OPTIONS_ENVIRONMENT_BUILD_NUMERIC_POLICY_DEPENDENCIES",
        "semantic_equivalence": "EXPLICIT_SEMANTIC_PROJECTION_FINGERPRINT_OR_EXACT_ASSIGNMENT_FALLBACK",
        "proof_equivalence": "EXPLICIT_PROOF_FINGERPRINT_ONLY",
        "artifact_equivalence": "EXPLICIT_ARTIFACT_FINGERPRINT_ONLY",
        "agreement_grants_truth": False,
        "truth_authority": "NONE",
    }


__all__ = [
    "REPRODUCIBILITY_RUN_CONTRACT_ID",
    "REPRODUCIBILITY_CERTIFICATE_CONTRACT_ID",
    "REPRODUCIBILITY_CLAIM_LEVELS",
    "ReproducibilityRun",
    "ReproducibilityCertificate",
    "compare_reproducibility_runs",
    "reproducibility_contract",
]
