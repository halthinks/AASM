from __future__ import annotations

"""Experimental Symbiotic Intelligence Interface (SII).

This module stages the v0.44 participation/economic plane on top of the
existing AASM authority, reasoning, memory, reuse, and evidence machinery.
It intentionally does not create a second truth store or runtime kernel.

Design laws:
1. The reasoner proposes; AASM measures.
2. Utility may buy resources; utility never buys truth.
3. AASM returns compressed governed intelligence, not merely a score.

v0.43 status: EXPERIMENTAL_CERTIFICATION_TARGET.  Stable measurement-principal
binding and enforcement of ResourceLease values by the scheduler/capability
plane are explicit v0.44 graduation gates.
"""

from dataclasses import asdict, dataclass, field
from math import sqrt
import json
from typing import Any, Iterable, Mapping, Sequence

from .evidence import EvidenceRecord
from .hierarchical_memory import ContextProjectionRequest
from .reasoning import (
    REASONING_ARTIFACT_KINDS,
    ReasoningArtifact,
    ReasoningProducer,
    VerifierRequirement,
)
from .reuse_model import REUSE_CONTRACT_ID
from .reuse_metrics import ReuseMetrics
from .semantic_result import canonical_semantic_json, semantic_fingerprint


SII_CONTRACT_ID = "aasm.sii.v1"
SII_CONTRACT_VERSION = "0.2.0"
SII_STABILITY = "EXPERIMENTAL_CERTIFICATION_TARGET"
SII_EVENT_KIND = "sii_event"

SII_RECORD_TYPES = ("IDENTITY", "PROPOSAL", "OUTCOME")
PROPOSER_KINDS = ("llm", "script", "human", "ensemble", "solver")
OUTCOME_DISPOSITIONS = (
    "ADMITTED",
    "REJECTED_SCHEMA",
    "REJECTED_POLICY",
    "EXECUTED",
    "VERIFIED",
    "AUTHORIZED",
    "REFUTED",
    "STALE",
    "SUPERSEDED",
    "FAILED",
    "INCONCLUSIVE",
)
OUTCOME_VERDICTS = ("PASS", "FAIL", "INCONCLUSIVE")
MEASUREMENT_AUTHORITIES = ("VERIFIER", "POLICY", "CONTROLLER")

_PASS_REASONING_STATES = {"VERIFIED", "AUTHORIZED"}
_FAIL_REASONING_STATES = {"REFUTED", "REJECTED"}


def _jsonable(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        return _jsonable(value.to_dict())
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_jsonable(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    raise TypeError(f"SII value is not JSON serializable: {type(value)!r}")


def _uniq(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted(set(map(str, values))))


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, float(value)))


def _safe_ratio(numerator: float, denominator: float) -> float:
    return float(numerator) / float(denominator) if denominator else 0.0


def _wilson_lower_bound(successes: int, total: int, z: float = 1.96) -> float:
    if total <= 0:
        return 0.0
    p = successes / total
    zz = z * z
    denom = 1.0 + zz / total
    center = p + zz / (2.0 * total)
    margin = z * sqrt((p * (1.0 - p) + zz / (4.0 * total)) / total)
    return _clamp((center - margin) / denom)


def _evidence_id(prefix: str, fingerprint: str) -> str:
    return f"evidence-sii-{prefix}-{fingerprint[:20]}"


@dataclass(frozen=True)
class RejectedAlternative:
    value: Any
    reason_code: str
    summary: str = ""
    evidence_ids: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.reason_code.strip():
            raise ValueError("rejected alternative reason_code is required")
        object.__setattr__(self, "evidence_ids", _uniq(self.evidence_ids))
        _jsonable(self.value)
        _jsonable(self.metadata)

    def to_dict(self) -> dict[str, Any]:
        return _jsonable(asdict(self))

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "RejectedAlternative":
        return cls(**dict(data))


@dataclass(frozen=True)
class ArtifactProposal:
    """Typed public consequence, never a raw chain-of-thought container."""

    kind: str
    statement: str
    subject_ids: tuple[str, ...] = ()
    premise_artifact_ids: tuple[str, ...] = ()
    evidence_ids: tuple[str, ...] = ()
    verifier_ids: tuple[str, ...] = ()
    confidence: float | None = None
    scope: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.kind not in REASONING_ARTIFACT_KINDS:
            raise ValueError(f"invalid reasoning artifact kind: {self.kind}")
        if not self.statement.strip():
            raise ValueError("artifact proposal statement is required")
        object.__setattr__(self, "subject_ids", _uniq(self.subject_ids))
        object.__setattr__(self, "premise_artifact_ids", _uniq(self.premise_artifact_ids))
        object.__setattr__(self, "evidence_ids", _uniq(self.evidence_ids))
        object.__setattr__(self, "verifier_ids", _uniq(self.verifier_ids))
        if self.confidence is not None and not 0.0 <= float(self.confidence) <= 1.0:
            raise ValueError("artifact confidence must be between 0 and 1")
        _jsonable(self.scope)
        _jsonable(self.metadata)

    def to_dict(self) -> dict[str, Any]:
        return _jsonable(asdict(self))

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ArtifactProposal":
        return cls(**dict(data))

    def compile(
        self,
        *,
        proposer_id: str,
        default_scope_id: str,
        proposal_evidence_id: str,
    ) -> ReasoningArtifact:
        scope = {"scope_id": default_scope_id, **dict(self.scope)}
        evidence_ids = _uniq((*self.evidence_ids, proposal_evidence_id))
        return ReasoningArtifact(
            kind=self.kind,
            statement=self.statement,
            producer=ReasoningProducer(
                producer_id=proposer_id,
                authority_class="PROPOSER",
                metadata={"sii_contract_id": SII_CONTRACT_ID},
            ),
            subject_ids=self.subject_ids,
            premise_artifact_ids=self.premise_artifact_ids,
            evidence_ids=evidence_ids,
            verifier_requirements=tuple(
                VerifierRequirement(verifier_id=value) for value in self.verifier_ids
            ),
            confidence=self.confidence,
            scope=scope,
            metadata={
                **dict(self.metadata),
                "sii_contract_id": SII_CONTRACT_ID,
                "proposal_evidence_id": proposal_evidence_id,
            },
        )


@dataclass(frozen=True)
class StructuredProposal:
    proposer_id: str
    decision_name: str
    scope_id: str
    chosen: Any
    confidence: float
    task_class: str = "general"
    rejected_alternatives: tuple[RejectedAlternative | Mapping[str, Any], ...] = ()
    artifacts: tuple[ArtifactProposal | Mapping[str, Any], ...] = ()
    evidence_ids: tuple[str, ...] = ()
    expected_input_tokens: int | None = None
    expected_output_tokens: int | None = None
    expected_tool_calls: int | None = None
    rationale_summary: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.proposer_id.strip():
            raise ValueError("proposal proposer_id is required")
        if not self.decision_name.strip():
            raise ValueError("proposal decision_name is required")
        if not self.scope_id.strip():
            raise ValueError("proposal scope_id is required")
        if not self.task_class.strip():
            raise ValueError("proposal task_class is required")
        if not 0.0 <= float(self.confidence) <= 1.0:
            raise ValueError("proposal confidence must be between 0 and 1")
        object.__setattr__(
            self,
            "rejected_alternatives",
            tuple(
                item if isinstance(item, RejectedAlternative) else RejectedAlternative.from_dict(item)
                for item in self.rejected_alternatives
            ),
        )
        object.__setattr__(
            self,
            "artifacts",
            tuple(
                item if isinstance(item, ArtifactProposal) else ArtifactProposal.from_dict(item)
                for item in self.artifacts
            ),
        )
        object.__setattr__(self, "evidence_ids", _uniq(self.evidence_ids))
        for name in ("expected_input_tokens", "expected_output_tokens", "expected_tool_calls"):
            value = getattr(self, name)
            if value is not None and int(value) < 0:
                raise ValueError(f"{name} must be non-negative")
        _jsonable(self.chosen)
        _jsonable(self.metadata)

    def identity_payload(self) -> dict[str, Any]:
        return {
            "proposer_id": self.proposer_id,
            "decision_name": self.decision_name,
            "scope_id": self.scope_id,
            "chosen": _jsonable(self.chosen),
            "confidence": float(self.confidence),
            "task_class": self.task_class,
            "rejected_alternatives": [item.to_dict() for item in self.rejected_alternatives],
            "artifacts": [item.to_dict() for item in self.artifacts],
            "evidence_ids": list(self.evidence_ids),
            "expected_input_tokens": self.expected_input_tokens,
            "expected_output_tokens": self.expected_output_tokens,
            "expected_tool_calls": self.expected_tool_calls,
            "rationale_summary": self.rationale_summary,
            "metadata": _jsonable(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(self.identity_payload())

    @property
    def proposal_id(self) -> str:
        return f"sii-proposal-{self.fingerprint[:20]}"

    def to_dict(self) -> dict[str, Any]:
        return {"proposal_id": self.proposal_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "StructuredProposal":
        payload = dict(data)
        payload.pop("proposal_id", None)
        payload.pop("fingerprint", None)
        return cls(**payload)


@dataclass(frozen=True)
class ProposerIdentity:
    principal_id: str
    name: str
    kind: str = "llm"
    provider: str = ""
    model_id: str = ""
    version: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.principal_id.strip():
            raise ValueError("principal_id is required")
        if not self.name.strip():
            raise ValueError("proposer name is required")
        if self.kind not in PROPOSER_KINDS:
            raise ValueError(f"invalid proposer kind: {self.kind}")
        _jsonable(self.metadata)

    def identity_payload(self) -> dict[str, Any]:
        return {
            "principal_id": self.principal_id,
            "name": self.name,
            "kind": self.kind,
            "provider": self.provider,
            "model_id": self.model_id,
            "version": self.version,
            "metadata": _jsonable(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(self.identity_payload())

    @property
    def proposer_id(self) -> str:
        return f"sii-proposer-{semantic_fingerprint({'principal_id': self.principal_id, 'kind': self.kind})[:20]}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "proposer_id": self.proposer_id,
            **self.identity_payload(),
            "authority_class": "PROPOSER",
            "fingerprint": self.fingerprint,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ProposerIdentity":
        payload = dict(data)
        payload.pop("proposer_id", None)
        payload.pop("authority_class", None)
        payload.pop("fingerprint", None)
        return cls(**payload)


@dataclass(frozen=True)
class OutcomeMeasurement:
    proposal_id: str
    measured_by: str
    authority_class: str
    disposition: str
    verification_verdict: str = "INCONCLUSIVE"
    artifact_ids: tuple[str, ...] = ()
    authorized_artifact_ids: tuple[str, ...] = ()
    reusable_artifact_ids: tuple[str, ...] = ()
    reuse_metrics_evidence_ids: tuple[str, ...] = ()
    evidence_ids: tuple[str, ...] = ()
    learned_constraint_ids: tuple[str, ...] = ()
    repair_required: bool = False
    actual_input_tokens: int = 0
    actual_output_tokens: int = 0
    downstream_reuse_hits: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.proposal_id.strip():
            raise ValueError("measurement proposal_id is required")
        if not self.measured_by.strip():
            raise ValueError("measurement measured_by is required")
        if self.authority_class not in MEASUREMENT_AUTHORITIES:
            raise PermissionError("SII outcome measurement requires VERIFIER, POLICY, or CONTROLLER authority")
        if self.disposition not in OUTCOME_DISPOSITIONS:
            raise ValueError(f"invalid outcome disposition: {self.disposition}")
        if self.verification_verdict not in OUTCOME_VERDICTS:
            raise ValueError(f"invalid verification verdict: {self.verification_verdict}")
        for name in (
            "artifact_ids",
            "authorized_artifact_ids",
            "reusable_artifact_ids",
            "reuse_metrics_evidence_ids",
            "evidence_ids",
            "learned_constraint_ids",
        ):
            object.__setattr__(self, name, _uniq(getattr(self, name)))
        for name in ("actual_input_tokens", "actual_output_tokens", "downstream_reuse_hits"):
            if int(getattr(self, name)) < 0:
                raise ValueError(f"{name} must be non-negative")
        _jsonable(self.metadata)

    def identity_payload(self) -> dict[str, Any]:
        return _jsonable(asdict(self))

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(self.identity_payload())

    @property
    def outcome_id(self) -> str:
        return f"sii-outcome-{self.fingerprint[:20]}"

    def to_dict(self) -> dict[str, Any]:
        return {"outcome_id": self.outcome_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "OutcomeMeasurement":
        payload = dict(data)
        payload.pop("outcome_id", None)
        payload.pop("fingerprint", None)
        return cls(**payload)


@dataclass(frozen=True)
class PerformanceVector:
    proposer_id: str
    samples: int = 0
    terminal_samples: int = 0
    pass_count: int = 0
    fail_count: int = 0
    inconclusive_count: int = 0
    repair_count: int = 0
    reliability_lower_bound: float = 0.0
    brier_score: float | None = None
    calibration_score: float = 0.0
    verified_utility: float = 0.0
    reuse_contribution: float = 0.0
    compute_efficiency: float = 0.0
    conflict_learning_value: float = 0.0
    artifact_durability: float = 0.0
    repair_rate: float = 0.0
    measured_input_units_avoided: int = 0
    measured_output_units_avoided: int = 0
    measured_model_calls_avoided: int = 0
    measured_tool_calls_avoided: int = 0
    measured_solver_runs_avoided: int = 0
    projection_window: int = 50

    def to_dict(self) -> dict[str, Any]:
        return _jsonable(asdict(self))


@dataclass(frozen=True)
class WeightProfile:
    name: str
    reliability: float
    calibration: float
    verified_utility: float
    reuse_contribution: float
    compute_efficiency: float
    conflict_learning_value: float
    artifact_durability: float

    def normalized(self) -> "WeightProfile":
        total = sum((
            self.reliability,
            self.calibration,
            self.verified_utility,
            self.reuse_contribution,
            self.compute_efficiency,
            self.conflict_learning_value,
            self.artifact_durability,
        ))
        if total <= 0:
            raise ValueError("SII weight profile must have positive total weight")
        return WeightProfile(
            self.name,
            self.reliability / total,
            self.calibration / total,
            self.verified_utility / total,
            self.reuse_contribution / total,
            self.compute_efficiency / total,
            self.conflict_learning_value / total,
            self.artifact_durability / total,
        )


DEFAULT_WEIGHTS = WeightProfile("default", .25, .15, .20, .15, .15, .05, .05).normalized()
EXPLORATION_WEIGHTS = WeightProfile("exploration", .15, .10, .20, .15, .10, .15, .15).normalized()
EXPLOITATION_WEIGHTS = WeightProfile("exploitation", .25, .10, .15, .25, .20, .025, .025).normalized()
FORMAL_WEIGHTS = WeightProfile("formal", .30, .15, .20, .05, .05, .15, .10).normalized()


class DynamicWeightController:
    def select(self, *, phase: str = "normal", measured_reuse_rate: float = 0.0, formal_goal: bool = False) -> WeightProfile:
        measured_reuse_rate = _clamp(measured_reuse_rate)
        if formal_goal:
            return FORMAL_WEIGHTS
        if phase == "explore" or measured_reuse_rate < 0.25:
            return EXPLORATION_WEIGHTS
        if phase == "exploit" or measured_reuse_rate > 0.60:
            return EXPLOITATION_WEIGHTS
        return DEFAULT_WEIGHTS

    def compute(self, vector: PerformanceVector, profile: WeightProfile) -> float:
        return _clamp(
            profile.reliability * vector.reliability_lower_bound
            + profile.calibration * vector.calibration_score
            + profile.verified_utility * vector.verified_utility
            + profile.reuse_contribution * vector.reuse_contribution
            + profile.compute_efficiency * vector.compute_efficiency
            + profile.conflict_learning_value * vector.conflict_learning_value
            + profile.artifact_durability * vector.artifact_durability
        )


@dataclass(frozen=True)
class ResourceLease:
    """Computed resource policy projection; never epistemic authority."""

    proposer_id: str
    resource_tier: int
    contextual_utility: float
    weight_profile: str
    context_budget_tokens: int
    max_parallel_candidates: int
    allowed_solver_classes: tuple[str, ...]
    may_request_long_lived_memory: bool
    may_propose_schema_change: bool
    scheduler_priority: float
    authority_class: str = "PROPOSER"
    direct_truth_promotion: bool = False
    direct_state_mutation: bool = False
    self_verification: bool = False
    enforcement: str = "POLICY_PROJECTION_ONLY_V043"
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return _jsonable(asdict(self))


@dataclass(frozen=True)
class SymbioticFeedback:
    proposal_id: str
    outcome_evidence_id: str
    performance: PerformanceVector
    resource_lease: ResourceLease
    measured_savings: dict[str, int]
    next_best_actions: tuple[str, ...]
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "outcome_evidence_id": self.outcome_evidence_id,
            "performance": self.performance.to_dict(),
            "resource_lease": self.resource_lease.to_dict(),
            "measured_savings": dict(self.measured_savings),
            "next_best_actions": list(self.next_best_actions),
            "message": self.message,
        }


def sii_contract() -> dict[str, Any]:
    return {
        "contract_id": SII_CONTRACT_ID,
        "contract_version": SII_CONTRACT_VERSION,
        "stability": SII_STABILITY,
        "producer_authority": "PROPOSER_ONLY",
        "measurement_authority": list(MEASUREMENT_AUTHORITIES),
        "measurement_identity_binding": "CALLER_ASSERTED_PREVIEW_V043",
        "semantic_fingerprint": "AASM_COMPUTED",
        "novelty_score": "NOT_PROPOSER_CONTROLLED",
        "depth_score": "NOT_PROPOSER_CONTROLLED",
        "raw_chain_of_thought": "NOT_REQUIRED_OR_STORED",
        "truth_promotion": "EXISTING_AASM_REASONING_POLICY_ONLY",
        "self_verification": "REJECTED",
        "resource_reward": "COMPUTE_SEARCH_CONTEXT_ONLY",
        "resource_enforcement": "V044_GRADUATION_GATE",
        "authority_reward": "NEVER",
        "durability_boundary": "AASM_EVIDENCE_EVENT_REDUCER_ONLY",
        "identity_reset": "STABLE_PRINCIPAL_BINDING_EXPECTED",
        "metric_source": "DURABLE_OUTCOMES_AND_VALIDATED_REUSE_METRICS",
        "context_reward": "V0.40_BOUNDED_CONTEXT_PROJECTION",
        "reasoning_admission": "V0.37_REASONING_ARTIFACT_LIFECYCLE",
        "reuse_measurement": "V0.41_REUSE_METRICS",
        "kernel_runtime": "V0.41_ENGINE_UNCHANGED",
        "v044_graduation_gates": [
            "measurement_principal_authority_binding",
            "resource_lease_scheduler_enforcement",
            "resource_lease_capability_enforcement",
            "adversarial_certification_pass",
        ],
    }


def _parse_sii_record(row: Mapping[str, Any]) -> tuple[str, dict[str, Any]] | None:
    metadata = row.get("metadata") or {}
    if row.get("kind") != SII_EVENT_KIND or row.get("source") != SII_CONTRACT_ID:
        return None
    if metadata.get("sii_contract_id") != SII_CONTRACT_ID:
        return None
    record_type = str(metadata.get("sii_record_type") or "")
    if record_type not in SII_RECORD_TYPES:
        return None
    try:
        payload = json.loads(str(row.get("statement") or "{}"))
    except json.JSONDecodeError:
        return record_type, {"_parse_error": True}
    return record_type, payload


def project_sii_evidence(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    identities: dict[str, dict[str, Any]] = {}
    proposals: dict[str, dict[str, Any]] = {}
    outcomes: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    for row in sorted(records, key=lambda item: (float(item.get("created_at", 0) or 0), str(item.get("evidence_id", "")))):
        if row.get("status", "active") != "active":
            continue
        parsed = _parse_sii_record(row)
        if parsed is None:
            continue
        record_type, payload = parsed
        if payload.get("_parse_error"):
            issues.append({"code": "SII_RECORD_PARSE_ERROR", "evidence_id": row.get("evidence_id"), "record_type": record_type})
            continue
        try:
            if record_type == "IDENTITY":
                identity = ProposerIdentity.from_dict(payload["identity"])
                prior = identities.get(identity.proposer_id)
                candidate = {"identity": identity.to_dict(), "evidence_id": row.get("evidence_id")}
                if prior and prior["identity"]["fingerprint"] != identity.fingerprint:
                    issues.append({"code": "SII_IDENTITY_COLLISION", "proposer_id": identity.proposer_id, "evidence_id": row.get("evidence_id")})
                    continue
                identities[identity.proposer_id] = candidate
            elif record_type == "PROPOSAL":
                proposal = StructuredProposal.from_dict(payload["proposal"])
                compiled_ids = _uniq(payload.get("compiled_artifact_ids", ()))
                prior = proposals.get(proposal.proposal_id)
                candidate = {"proposal": proposal.to_dict(), "compiled_artifact_ids": list(compiled_ids), "evidence_id": row.get("evidence_id")}
                if prior and prior["proposal"]["fingerprint"] != proposal.fingerprint:
                    issues.append({"code": "SII_PROPOSAL_COLLISION", "proposal_id": proposal.proposal_id, "evidence_id": row.get("evidence_id")})
                    continue
                proposals[proposal.proposal_id] = candidate
            else:
                outcome = OutcomeMeasurement.from_dict(payload["outcome"])
                outcomes.append({
                    "outcome": outcome.to_dict(),
                    "measured_savings": _jsonable(payload.get("measured_savings", {})),
                    "reasoning_states": _jsonable(payload.get("reasoning_states", {})),
                    "evidence_id": row.get("evidence_id"),
                    "created_at": row.get("created_at"),
                })
        except Exception as exc:
            issues.append({"code": f"SII_{record_type}_INVALID", "evidence_id": row.get("evidence_id"), "detail": f"{type(exc).__name__}: {exc}"})
    return {
        "contract": sii_contract(),
        "valid": not issues,
        "issues": issues,
        "identities": identities,
        "proposals": proposals,
        "outcomes": outcomes,
        "projection_fingerprint": semantic_fingerprint({"identities": identities, "proposals": proposals, "outcomes": outcomes, "issues": issues}),
    }


def _sum_reuse_metrics(evidence_records: Mapping[str, Mapping[str, Any]], evidence_ids: Sequence[str]) -> dict[str, int]:
    values = ReuseMetrics().to_dict()
    for evidence_id in evidence_ids:
        try:
            row = evidence_records[evidence_id]
        except KeyError:
            raise KeyError(f"unknown reuse metrics evidence: {evidence_id}") from None
        if row.get("kind") != "reuse_metrics" or row.get("source") != REUSE_CONTRACT_ID:
            raise ValueError(f"evidence is not an AASM reuse metrics record: {evidence_id}")
        try:
            metrics = ReuseMetrics(**json.loads(str(row.get("statement") or "{}")))
        except Exception as exc:
            raise ValueError(f"invalid reuse metrics evidence {evidence_id}: {exc}") from exc
        for key, value in metrics.to_dict().items():
            values[key] += int(value)
    return values


def _performance_from_projection(projection: Mapping[str, Any], proposer_id: str, *, window: int = 50) -> PerformanceVector:
    if window <= 0:
        raise ValueError("performance window must be positive")
    proposals = {
        proposal_id: row
        for proposal_id, row in projection["proposals"].items()
        if row["proposal"]["proposer_id"] == proposer_id
    }
    rows = [row for row in projection["outcomes"] if row["outcome"]["proposal_id"] in proposals][-window:]
    if not rows:
        return PerformanceVector(proposer_id=proposer_id, projection_window=window)
    pass_count = sum(1 for row in rows if row["outcome"]["verification_verdict"] == "PASS")
    fail_count = sum(1 for row in rows if row["outcome"]["verification_verdict"] == "FAIL")
    inconclusive = sum(1 for row in rows if row["outcome"]["verification_verdict"] == "INCONCLUSIVE")
    binary_total = pass_count + fail_count
    brier_values: list[float] = []
    verified_proposals = reuse_positive = repair_count = learned_positive = 0
    saved_input = saved_output = model_calls = tool_calls = solver_runs = actual_tokens = 0
    authorized_artifacts: set[str] = set()
    reusable_artifacts: set[str] = set()
    for row in rows:
        outcome = row["outcome"]
        proposal = proposals[outcome["proposal_id"]]["proposal"]
        verdict = outcome["verification_verdict"]
        if verdict in {"PASS", "FAIL"}:
            y = 1.0 if verdict == "PASS" else 0.0
            brier_values.append((float(proposal["confidence"]) - y) ** 2)
        authorized = set(outcome.get("authorized_artifact_ids") or ())
        reusable = set(outcome.get("reusable_artifact_ids") or ())
        authorized_artifacts.update(authorized)
        reusable_artifacts.update(reusable)
        verified_proposals += int(bool(authorized))
        reuse_positive += int(bool(reusable) or int(outcome.get("downstream_reuse_hits", 0) or 0) > 0)
        repair_count += int(bool(outcome.get("repair_required")))
        learned_positive += int(bool(outcome.get("learned_constraint_ids")))
        savings = row.get("measured_savings") or {}
        saved_input += int(savings.get("input_units_avoided", 0) or 0)
        saved_output += int(savings.get("output_units_avoided", 0) or 0)
        model_calls += int(savings.get("model_calls_avoided", 0) or 0)
        tool_calls += int(savings.get("tool_calls_avoided", 0) or 0)
        solver_runs += int(savings.get("solver_runs_avoided", 0) or 0)
        actual_tokens += int(outcome.get("actual_input_tokens", 0) or 0) + int(outcome.get("actual_output_tokens", 0) or 0)
    brier = sum(brier_values) / len(brier_values) if brier_values else None
    saved_total = saved_input + saved_output
    return PerformanceVector(
        proposer_id=proposer_id,
        samples=len(rows),
        terminal_samples=binary_total,
        pass_count=pass_count,
        fail_count=fail_count,
        inconclusive_count=inconclusive,
        repair_count=repair_count,
        reliability_lower_bound=_wilson_lower_bound(pass_count, binary_total),
        brier_score=brier,
        calibration_score=_clamp(1.0 - brier) if brier is not None else 0.0,
        verified_utility=_safe_ratio(verified_proposals, len(rows)),
        reuse_contribution=_safe_ratio(reuse_positive, len(rows)),
        compute_efficiency=_safe_ratio(saved_total, saved_total + actual_tokens),
        conflict_learning_value=_safe_ratio(learned_positive, len(rows)),
        artifact_durability=_safe_ratio(len(reusable_artifacts.intersection(authorized_artifacts)), len(authorized_artifacts)),
        repair_rate=_safe_ratio(repair_count, len(rows)),
        measured_input_units_avoided=saved_input,
        measured_output_units_avoided=saved_output,
        measured_model_calls_avoided=model_calls,
        measured_tool_calls_avoided=tool_calls,
        measured_solver_runs_avoided=solver_runs,
        projection_window=window,
    )


class SymbioticIntelligenceInterface:
    def __init__(self, engine):
        self.engine = engine
        self.weights = DynamicWeightController()

    def _evidence_rows(self) -> list[dict[str, Any]]:
        evidence = self.engine.snapshot.evidence
        return list(evidence.get("records", [])) if isinstance(evidence, dict) else []

    def _evidence_map(self) -> dict[str, dict[str, Any]]:
        return {str(row.get("evidence_id")): row for row in self._evidence_rows() if row.get("evidence_id")}

    def projection(self) -> dict[str, Any]:
        return project_sii_evidence(self._evidence_rows())

    def _require_projection(self) -> dict[str, Any]:
        projection = self.projection()
        if not projection["valid"]:
            raise RuntimeError(f"invalid durable SII projection: {projection['issues']}")
        return projection

    def _require_evidence(self, evidence_ids: Sequence[str]) -> tuple[str, ...]:
        selected = _uniq(evidence_ids)
        known = self._evidence_map()
        missing = [value for value in selected if value not in known]
        if missing:
            raise KeyError(f"unknown evidence references: {missing}")
        return selected

    def register(self, *, principal_id: str, name: str, kind: str = "llm", provider: str = "", model_id: str = "", version: str = "", metadata: Mapping[str, Any] | None = None) -> dict[str, Any]:
        identity = ProposerIdentity(principal_id, name, kind, provider, model_id, version, dict(metadata or {}))
        projection = self._require_projection()
        existing = projection["identities"].get(identity.proposer_id)
        if existing:
            if existing["identity"]["fingerprint"] != identity.fingerprint:
                raise ValueError("principal binding already exists with different identity metadata")
            return dict(existing)
        evidence_id = _evidence_id("identity", identity.fingerprint)
        stored = self.engine.add_evidence(
            EvidenceRecord(
                kind=SII_EVENT_KIND,
                statement=canonical_semantic_json({"identity": identity.to_dict()}),
                source=SII_CONTRACT_ID,
                metadata={
                    "sii_record_type": "IDENTITY",
                    "sii_contract_id": SII_CONTRACT_ID,
                    "proposer_id": identity.proposer_id,
                    "principal_id": identity.principal_id,
                    "identity_fingerprint": identity.fingerprint,
                },
                evidence_id=evidence_id,
            ),
            reason="SII proposer identity registered",
        )
        return {"identity": identity.to_dict(), "evidence_id": stored.evidence_id}

    def submit(self, proposal: StructuredProposal | Mapping[str, Any]) -> dict[str, Any]:
        proposal = proposal if isinstance(proposal, StructuredProposal) else StructuredProposal.from_dict(proposal)
        projection = self._require_projection()
        if proposal.proposer_id not in projection["identities"]:
            raise KeyError(f"unregistered SII proposer: {proposal.proposer_id}")
        self._require_evidence(proposal.evidence_ids)
        for rejected in proposal.rejected_alternatives:
            self._require_evidence(rejected.evidence_ids)
        for artifact in proposal.artifacts:
            self._require_evidence(artifact.evidence_ids)
        existing = projection["proposals"].get(proposal.proposal_id)
        if existing:
            return {
                **dict(existing),
                "reasoning_artifacts": [self.engine.reasoning_report(artifact_id) for artifact_id in existing["compiled_artifact_ids"]],
                "resource_lease": self.resource_lease(proposal.proposer_id).to_dict(),
            }
        proposal_evidence_id = _evidence_id("proposal", proposal.fingerprint)
        compiled = [
            artifact.compile(proposer_id=proposal.proposer_id, default_scope_id=proposal.scope_id, proposal_evidence_id=proposal_evidence_id)
            for artifact in proposal.artifacts
        ]
        compiled_ids = [artifact.artifact_id for artifact in compiled]
        derived = set(proposal.evidence_ids)
        derived.add(projection["identities"][proposal.proposer_id]["evidence_id"])
        for rejected in proposal.rejected_alternatives:
            derived.update(rejected.evidence_ids)
        for artifact in proposal.artifacts:
            derived.update(artifact.evidence_ids)
        stored = self.engine.add_evidence(
            EvidenceRecord(
                kind=SII_EVENT_KIND,
                statement=canonical_semantic_json({"proposal": proposal.to_dict(), "compiled_artifact_ids": compiled_ids}),
                source=SII_CONTRACT_ID,
                confidence=float(proposal.confidence),
                derived_from=sorted(derived),
                metadata={
                    "sii_record_type": "PROPOSAL",
                    "sii_contract_id": SII_CONTRACT_ID,
                    "proposal_id": proposal.proposal_id,
                    "proposal_fingerprint": proposal.fingerprint,
                    "proposer_id": proposal.proposer_id,
                    "task_class": proposal.task_class,
                    "scope_id": proposal.scope_id,
                    "compiled_artifact_ids": compiled_ids,
                },
                evidence_id=proposal_evidence_id,
            ),
            reason="SII structured proposal submitted",
        )
        reports = [self.engine.propose_artifact(artifact, reason="SII typed reasoning consequence proposed") for artifact in compiled]
        return {
            "proposal": proposal.to_dict(),
            "proposal_evidence_id": stored.evidence_id,
            "compiled_artifact_ids": compiled_ids,
            "reasoning_artifacts": reports,
            "resource_lease": self.resource_lease(proposal.proposer_id).to_dict(),
        }

    def _reasoning_states(self, artifact_ids: Sequence[str]) -> dict[str, str]:
        return {artifact_id: str(self.engine.reasoning_report(artifact_id)["state"]) for artifact_id in _uniq(artifact_ids)}

    @staticmethod
    def _derive_verdict(states: Mapping[str, str]) -> tuple[str, str]:
        if not states:
            return "INCONCLUSIVE", "INCONCLUSIVE"
        values = set(states.values())
        if values.intersection(_FAIL_REASONING_STATES):
            return "FAIL", "REFUTED"
        if values.issubset(_PASS_REASONING_STATES):
            return "PASS", "AUTHORIZED" if values == {"AUTHORIZED"} else "VERIFIED"
        if "STALE" in values:
            return "INCONCLUSIVE", "STALE"
        return "INCONCLUSIVE", "INCONCLUSIVE"

    def _validate_learned_constraints(self, ids: Sequence[str]) -> tuple[str, ...]:
        selected = _uniq(ids)
        if not selected:
            return selected
        begin = getattr(self.engine, "_begin_calculus", None)
        if begin is None:
            raise RuntimeError("runtime does not expose calculus state for learned-constraint validation")
        calculus = begin()
        constraints = calculus.get("constraints") or {}
        known = set(constraints if isinstance(constraints, dict) else ())
        missing = [value for value in selected if value not in known]
        if missing:
            raise KeyError(f"unknown learned constraints: {missing}")
        return selected

    def measure_proposal_outcome(
        self,
        proposal_id: str,
        *,
        measured_by: str,
        authority_class: str,
        reuse_metrics_evidence_ids: Sequence[str] = (),
        evidence_ids: Sequence[str] = (),
        learned_constraint_ids: Sequence[str] = (),
        repair_required: bool = False,
        actual_input_tokens: int = 0,
        actual_output_tokens: int = 0,
        downstream_reuse_hits: int = 0,
        disposition: str | None = None,
        verification_verdict: str | None = None,
        reusable_artifact_ids: Sequence[str] = (),
        metadata: Mapping[str, Any] | None = None,
    ) -> SymbioticFeedback:
        projection = self._require_projection()
        try:
            proposal_entry = projection["proposals"][proposal_id]
        except KeyError:
            raise KeyError(f"unknown SII proposal: {proposal_id}") from None
        proposer_id = proposal_entry["proposal"]["proposer_id"]
        if measured_by == proposer_id:
            raise ValueError("a proposal producer cannot measure its own SII outcome")
        if authority_class not in MEASUREMENT_AUTHORITIES:
            raise PermissionError("SII outcome measurement requires VERIFIER, POLICY, or CONTROLLER authority")
        evidence_ids = self._require_evidence(evidence_ids)
        reuse_metrics_evidence_ids = self._require_evidence(reuse_metrics_evidence_ids)
        learned_constraint_ids = self._validate_learned_constraints(learned_constraint_ids)
        artifact_ids = tuple(proposal_entry["compiled_artifact_ids"])
        states = self._reasoning_states(artifact_ids)
        derived_verdict, derived_disposition = self._derive_verdict(states)
        verdict = verification_verdict or derived_verdict
        final_disposition = disposition or derived_disposition
        if artifact_ids:
            if verification_verdict is not None and verification_verdict != derived_verdict:
                raise ValueError(f"measurement verdict {verification_verdict} contradicts durable reasoning state-derived verdict {derived_verdict}")
            if disposition is not None and disposition != derived_disposition:
                raise ValueError(f"measurement disposition {disposition} contradicts durable reasoning state-derived disposition {derived_disposition}")
        authorized = tuple(artifact_id for artifact_id, state in states.items() if state == "AUTHORIZED")
        reusable = _uniq(reusable_artifact_ids)
        unauthorized_reuse = [value for value in reusable if value not in authorized]
        if unauthorized_reuse:
            raise ValueError(f"only AUTHORIZED reasoning artifacts may receive SII reusable credit: {unauthorized_reuse}")
        measured_savings = _sum_reuse_metrics(self._evidence_map(), reuse_metrics_evidence_ids)
        measurement = OutcomeMeasurement(
            proposal_id=proposal_id,
            measured_by=measured_by,
            authority_class=authority_class,
            disposition=final_disposition,
            verification_verdict=verdict,
            artifact_ids=artifact_ids,
            authorized_artifact_ids=authorized,
            reusable_artifact_ids=reusable,
            reuse_metrics_evidence_ids=tuple(reuse_metrics_evidence_ids),
            evidence_ids=tuple(evidence_ids),
            learned_constraint_ids=learned_constraint_ids,
            repair_required=repair_required,
            actual_input_tokens=int(actual_input_tokens),
            actual_output_tokens=int(actual_output_tokens),
            downstream_reuse_hits=int(downstream_reuse_hits),
            metadata=dict(metadata or {}),
        )
        existing_for_proposal = [row for row in projection["outcomes"] if row["outcome"]["proposal_id"] == proposal_id]
        if existing_for_proposal:
            exact = [row for row in existing_for_proposal if row["outcome"]["outcome_id"] == measurement.outcome_id]
            if not exact:
                raise ValueError("SII proposal already has a measured outcome; record later reuse as telemetry rather than a second scoreable sample")
            perf = self.performance(proposer_id)
            lease = self.resource_lease(proposer_id)
            savings = exact[-1].get("measured_savings") or {}
            return SymbioticFeedback(
                proposal_id,
                exact[-1]["evidence_id"],
                perf,
                lease,
                {key: int(value) for key, value in savings.items() if key.endswith("_avoided")},
                self._suggest_next(perf),
                f"SII outcome already recorded | resource tier {lease.resource_tier}",
            )
        derived_from = set(evidence_ids)
        derived_from.update(reuse_metrics_evidence_ids)
        derived_from.add(proposal_entry["evidence_id"])
        for artifact_id in artifact_ids:
            report = self.engine.reasoning_report(artifact_id)
            if report.get("proposal_evidence_id"):
                derived_from.add(report["proposal_evidence_id"])
            history = report.get("history") or []
            if history:
                derived_from.add(history[-1]["evidence_id"])
        outcome_evidence_id = _evidence_id("outcome", measurement.fingerprint)
        stored = self.engine.add_evidence(
            EvidenceRecord(
                kind=SII_EVENT_KIND,
                statement=canonical_semantic_json({"outcome": measurement.to_dict(), "measured_savings": measured_savings, "reasoning_states": states}),
                source=SII_CONTRACT_ID,
                derived_from=sorted(derived_from),
                metadata={
                    "sii_record_type": "OUTCOME",
                    "sii_contract_id": SII_CONTRACT_ID,
                    "outcome_id": measurement.outcome_id,
                    "outcome_fingerprint": measurement.fingerprint,
                    "proposal_id": proposal_id,
                    "proposer_id": proposer_id,
                    "measured_by": measured_by,
                    "measurement_authority_class": authority_class,
                    "verification_verdict": verdict,
                    "disposition": final_disposition,
                },
                evidence_id=outcome_evidence_id,
            ),
            reason="SII measured proposal outcome recorded",
        )
        perf = self.performance(proposer_id)
        lease = self.resource_lease(proposer_id)
        return SymbioticFeedback(
            proposal_id,
            stored.evidence_id,
            perf,
            lease,
            {key: int(value) for key, value in measured_savings.items() if key.endswith("_avoided")},
            self._suggest_next(perf),
            f"SII measured outcome {verdict} | utility {lease.contextual_utility:.3f} | resource tier {lease.resource_tier}",
        )

    def performance(self, proposer_id: str, *, window: int = 50) -> PerformanceVector:
        projection = self._require_projection()
        if proposer_id not in projection["identities"]:
            raise KeyError(f"unknown SII proposer: {proposer_id}")
        return _performance_from_projection(projection, proposer_id, window=window)

    def resource_lease(self, proposer_id: str, *, phase: str = "normal", formal_goal: bool = False, window: int = 50) -> ResourceLease:
        perf = self.performance(proposer_id, window=window)
        profile = self.weights.select(phase=phase, measured_reuse_rate=perf.reuse_contribution, formal_goal=formal_goal)
        utility = self.weights.compute(perf, profile)
        if perf.terminal_samples >= 25 and utility >= 0.82:
            return ResourceLease(proposer_id, 3, utility, profile.name, 32768, 8, ("default", "formal", "portfolio"), True, True, 1.0, message="High verified marginal value: expanded compute/search lease")
        if perf.terminal_samples >= 12 and utility >= 0.68:
            return ResourceLease(proposer_id, 2, utility, profile.name, 16384, 4, ("default", "formal"), True, False, .75, message="Established verified value: expanded context/search lease")
        return ResourceLease(proposer_id, 1, utility, profile.name, 8192, 2, ("default",), False, False, .40, message="Standard compute/search lease; authority remains PROPOSER")

    def context_for(
        self,
        proposer_id: str,
        *,
        scope_id: str,
        query: str = "",
        phase: str = "normal",
        formal_goal: bool = False,
        allowed_privacy_levels: Sequence[str] = ("AGENT", "USER", "SHARED", "PUBLIC"),
        memory_kinds: Sequence[str] = (),
        objective_node_ids: Sequence[str] = (),
        max_memory_items: int = 20,
        max_frontier_items: int = 20,
    ) -> dict[str, Any]:
        projection = self._require_projection()
        try:
            identity = projection["identities"][proposer_id]["identity"]
        except KeyError:
            raise KeyError(f"unknown SII proposer: {proposer_id}") from None
        lease = self.resource_lease(proposer_id, phase=phase, formal_goal=formal_goal)
        request = ContextProjectionRequest(
            scope_id=scope_id,
            query=query,
            allowed_privacy_levels=tuple(allowed_privacy_levels),
            memory_kinds=tuple(memory_kinds),
            objective_node_ids=tuple(objective_node_ids),
            max_memory_items=max_memory_items,
            max_frontier_items=max_frontier_items,
            max_chars=max(0, lease.context_budget_tokens * 4),
            metadata={
                "principal_id": identity["principal_id"],
                "sii_proposer_id": proposer_id,
                "sii_contract_id": SII_CONTRACT_ID,
                "resource_tier": lease.resource_tier,
            },
        )
        return {
            "contract": sii_contract(),
            "proposer": identity,
            "resource_lease": lease.to_dict(),
            "context_projection": self.engine.context_projection(request),
            "reasoning_frontier": self.engine.reasoning_frontier(request),
            "note": "Context budget is a resource projection; returned facts retain their original AASM epistemic state and authority.",
        }

    @staticmethod
    def _suggest_next(perf: PerformanceVector) -> tuple[str, ...]:
        suggestions: list[str] = []
        if perf.terminal_samples < 12:
            suggestions.append("Accumulate independently verified outcomes")
        if perf.calibration_score < .70:
            suggestions.append("Improve confidence calibration")
        if perf.verified_utility < .50:
            suggestions.append("Produce fewer, higher-value typed reasoning artifacts")
        if perf.reuse_contribution < .30:
            suggestions.append("Reuse existing AASM memory/artifacts before regenerating work")
        if perf.compute_efficiency < .25:
            suggestions.append("Reduce redundant model/tool/solver work")
        if perf.repair_rate > .30:
            suggestions.append("Reduce repair-inducing proposals")
        return tuple(suggestions or ("Continue current verified trajectory",))

    def report(self, proposer_id: str | None = None, *, phase: str = "normal", formal_goal: bool = False, window: int = 50) -> dict[str, Any]:
        projection = self._require_projection()
        if proposer_id is None:
            rows = {}
            for value in sorted(projection["identities"]):
                perf = self.performance(value, window=window)
                lease = self.resource_lease(value, phase=phase, formal_goal=formal_goal, window=window)
                rows[value] = {
                    "identity": projection["identities"][value]["identity"],
                    "performance": perf.to_dict(),
                    "resource_lease": lease.to_dict(),
                    "next_best_actions": list(self._suggest_next(perf)),
                }
            return {"contract": sii_contract(), "projection_fingerprint": projection["projection_fingerprint"], "valid": projection["valid"], "issues": projection["issues"], "proposers": rows}
        if proposer_id not in projection["identities"]:
            raise KeyError(proposer_id)
        perf = self.performance(proposer_id, window=window)
        lease = self.resource_lease(proposer_id, phase=phase, formal_goal=formal_goal, window=window)
        return {
            "contract": sii_contract(),
            "projection_fingerprint": projection["projection_fingerprint"],
            "identity": projection["identities"][proposer_id]["identity"],
            "performance": perf.to_dict(),
            "resource_lease": lease.to_dict(),
            "next_best_actions": list(self._suggest_next(perf)),
        }


def create_sii(engine) -> SymbioticIntelligenceInterface:
    return SymbioticIntelligenceInterface(engine)


__all__ = [
    "SII_CONTRACT_ID",
    "SII_CONTRACT_VERSION",
    "SII_STABILITY",
    "ArtifactProposal",
    "DynamicWeightController",
    "OutcomeMeasurement",
    "PerformanceVector",
    "ProposerIdentity",
    "RejectedAlternative",
    "ResourceLease",
    "StructuredProposal",
    "SymbioticFeedback",
    "SymbioticIntelligenceInterface",
    "WeightProfile",
    "create_sii",
    "project_sii_evidence",
    "sii_contract",
]
