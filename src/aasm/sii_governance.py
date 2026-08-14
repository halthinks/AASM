from __future__ import annotations

"""Governed Symbiotic Intelligence Interface for AASM v0.47.

The v0.43 SII module remains the durable proposal/outcome substrate.  This
module closes its two explicit graduation gaps without creating a second
scheduler, truth store, reducer, or authority plane:

* proposer and measurement identities are bound by POLICY/CONTROLLER into
  durable AASM Evidence before they may participate;
* versioned scoring policy compiles measured utility into concrete resource
  budgets that can be enforced by the existing context, capability, scheduler,
  TaskLease, and native-solver paths.

Utility can buy compute/search/context.  It can never buy truth, canonical-state
mutation, self verification, or the removal of verification required by policy.
"""

from copy import deepcopy
from dataclasses import asdict, dataclass, field, replace
from typing import Any, Mapping, Sequence
import json

from .advanced_optimization import (
    ADVANCED_CAPABILITIES,
    AdvancedConvexProblem,
    AdvancedMILPProblem,
    CPSATSchedulingProblem,
    FastSATProblem,
    IncrementalSATProblem,
    advanced_problem_from_dict,
)
from .evidence import EvidenceRecord
from .hierarchical_memory import ContextProjectionRequest
from .semantic_result import canonical_semantic_json, semantic_fingerprint
from .sii import (
    MEASUREMENT_AUTHORITIES,
    PerformanceVector,
    StructuredProposal,
    create_sii,
)


SII_GOVERNED_CONTRACT_ID = "aasm.sii.v1"
SII_GOVERNED_CONTRACT_VERSION = "0.3.0"
SII_GOVERNED_STABILITY = "GOVERNED_ENFORCED"
SII_GOVERNANCE_EVENT_KIND = "sii_governance"
SII_GOVERNANCE_RECORD_TYPES = ("PRINCIPAL", "SCORING_POLICY", "POLICY_ACTIVATION", "RESOURCE_LEASE", "ENFORCEMENT")
SII_PRINCIPAL_AUTHORITY_CLASSES = ("PROPOSER", "VERIFIER", "POLICY", "CONTROLLER")
SII_SCORING_METRICS = (
    "reliability",
    "calibration",
    "verified_utility",
    "reuse_contribution",
    "compute_efficiency",
    "conflict_learning_value",
    "artifact_durability",
)


def _uniq(values: Sequence[str]) -> tuple[str, ...]:
    return tuple(sorted(set(map(str, values))))


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, float(value)))


def _eid(label: str, fingerprint: str) -> str:
    return f"evidence-sii-v47-{label}-{fingerprint[:20]}"


def _normalize_weights(weights: Mapping[str, float]) -> dict[str, float]:
    unknown = sorted(set(weights) - set(SII_SCORING_METRICS))
    missing = sorted(set(SII_SCORING_METRICS) - set(weights))
    if unknown or missing:
        raise ValueError(f"SII scoring weights require exact metric set; missing={missing} unknown={unknown}")
    values = {str(key): float(value) for key, value in weights.items()}
    if any(value < 0 for value in values.values()):
        raise ValueError("SII scoring weights must be non-negative")
    total = sum(values.values())
    if total <= 0:
        raise ValueError("SII scoring weights require positive total")
    return {key: value / total for key, value in sorted(values.items())}


@dataclass(frozen=True)
class SIIPrincipalBinding:
    principal_id: str
    authority_class: str
    can_propose: bool = False
    can_measure: bool = False
    active: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.principal_id.strip():
            raise ValueError("SII governed principal_id is required")
        if self.authority_class not in SII_PRINCIPAL_AUTHORITY_CLASSES:
            raise ValueError(f"invalid governed SII authority class: {self.authority_class}")
        if self.can_measure and self.authority_class not in MEASUREMENT_AUTHORITIES:
            raise ValueError("SII measurement principals must be VERIFIER, POLICY, or CONTROLLER")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "principal_id": self.principal_id,
            "authority_class": self.authority_class,
            "can_propose": bool(self.can_propose),
            "can_measure": bool(self.can_measure),
            "active": bool(self.active),
            "metadata": deepcopy(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(self.identity_payload())

    @property
    def binding_id(self) -> str:
        return f"sii-principal-{semantic_fingerprint({'principal_id': self.principal_id})[:20]}"

    def to_dict(self) -> dict[str, Any]:
        return {"binding_id": self.binding_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SIIPrincipalBinding":
        payload = deepcopy(dict(value)); payload.pop("binding_id", None); payload.pop("fingerprint", None); return cls(**payload)


@dataclass(frozen=True)
class SIIResourceBudget:
    context_budget_tokens: int
    max_parallel_candidates: int
    scheduler_priority: int
    solver_timeout_ms: int
    sat_conflict_budget: int
    sat_decision_budget: int
    cp_sat_deterministic_time: float
    cp_sat_search_workers: int
    milp_node_limit: int
    convex_timeout_ms: int
    formal_timeout_ms: int
    max_model_calls: int
    portfolio_width: int
    allowed_advanced_kinds: tuple[str, ...] = tuple(ADVANCED_CAPABILITIES)

    def __post_init__(self):
        positive_ints = (
            "context_budget_tokens", "max_parallel_candidates", "scheduler_priority",
            "solver_timeout_ms", "sat_conflict_budget", "sat_decision_budget",
            "cp_sat_search_workers", "milp_node_limit", "convex_timeout_ms",
            "formal_timeout_ms", "max_model_calls", "portfolio_width",
        )
        for name in positive_ints:
            if int(getattr(self, name)) <= 0:
                raise ValueError(f"SII budget {name} must be positive")
        if float(self.cp_sat_deterministic_time) <= 0:
            raise ValueError("SII cp_sat_deterministic_time must be positive")
        unknown = sorted(set(self.allowed_advanced_kinds) - set(ADVANCED_CAPABILITIES))
        if unknown:
            raise ValueError(f"SII budget references unknown advanced kinds: {unknown}")
        object.__setattr__(self, "allowed_advanced_kinds", _uniq(self.allowed_advanced_kinds))

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), "allowed_advanced_kinds": list(self.allowed_advanced_kinds)}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SIIResourceBudget":
        payload = deepcopy(dict(value)); payload["allowed_advanced_kinds"] = tuple(payload.get("allowed_advanced_kinds") or tuple(ADVANCED_CAPABILITIES)); return cls(**payload)


@dataclass(frozen=True)
class SIITierRule:
    tier: int
    min_terminal_samples: int
    min_utility: float
    budget: SIIResourceBudget | Mapping[str, Any]

    def __post_init__(self):
        if int(self.tier) <= 0 or int(self.min_terminal_samples) < 0:
            raise ValueError("SII tier and sample threshold must be non-negative/positive")
        if not 0.0 <= float(self.min_utility) <= 1.0:
            raise ValueError("SII tier utility threshold must be in [0,1]")
        budget = self.budget if isinstance(self.budget, SIIResourceBudget) else SIIResourceBudget.from_dict(self.budget)
        object.__setattr__(self, "budget", budget)

    def to_dict(self) -> dict[str, Any]:
        return {"tier": int(self.tier), "min_terminal_samples": int(self.min_terminal_samples), "min_utility": float(self.min_utility), "budget": self.budget.to_dict()}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SIITierRule":
        return cls(**deepcopy(dict(value)))


@dataclass(frozen=True)
class SIIScoringPolicy:
    name: str
    version: str
    profiles: dict[str, dict[str, float]]
    tiers: tuple[SIITierRule | Mapping[str, Any], ...]
    projection_window: int = 50
    exploration_reuse_below: float = 0.25
    exploitation_reuse_above: float = 0.60
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.name.strip() or not self.version.strip():
            raise ValueError("SII scoring policy name/version are required")
        profiles = {str(name): _normalize_weights(weights) for name, weights in sorted(self.profiles.items())}
        required_profiles = {"default", "exploration", "exploitation", "formal"}
        if set(profiles) != required_profiles:
            raise ValueError(f"SII scoring policy profiles must be exactly {sorted(required_profiles)}")
        tiers = tuple(row if isinstance(row, SIITierRule) else SIITierRule.from_dict(row) for row in self.tiers)
        if not tiers:
            raise ValueError("SII scoring policy requires at least one tier")
        tiers = tuple(sorted(tiers, key=lambda row: row.tier))
        if [row.tier for row in tiers] != list(range(1, len(tiers) + 1)):
            raise ValueError("SII tier numbers must be contiguous from 1")
        if tiers[0].min_terminal_samples != 0 or tiers[0].min_utility != 0.0:
            raise ValueError("SII tier 1 must be the unconditional baseline")
        if int(self.projection_window) <= 0:
            raise ValueError("SII scoring projection_window must be positive")
        if not 0 <= float(self.exploration_reuse_below) <= float(self.exploitation_reuse_above) <= 1:
            raise ValueError("SII reuse profile thresholds are invalid")
        object.__setattr__(self, "profiles", profiles)
        object.__setattr__(self, "tiers", tiers)

    def identity_payload(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "profiles": deepcopy(self.profiles),
            "tiers": [row.to_dict() for row in self.tiers],
            "projection_window": int(self.projection_window),
            "exploration_reuse_below": float(self.exploration_reuse_below),
            "exploitation_reuse_above": float(self.exploitation_reuse_above),
            "metadata": deepcopy(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(self.identity_payload())

    @property
    def policy_id(self) -> str:
        return f"sii-policy-{semantic_fingerprint({'name': self.name, 'version': self.version})[:20]}"

    def to_dict(self) -> dict[str, Any]:
        return {"policy_id": self.policy_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SIIScoringPolicy":
        payload = deepcopy(dict(value)); payload.pop("policy_id", None); payload.pop("fingerprint", None); return cls(**payload)

    def profile_name(self, performance: PerformanceVector, *, phase: str = "normal", formal_goal: bool = False) -> str:
        if formal_goal:
            return "formal"
        if phase == "explore":
            return "exploration"
        if phase == "exploit":
            return "exploitation"
        if phase not in {"normal", "formal"}:
            raise ValueError(f"unknown SII scoring phase: {phase}")
        if performance.reuse_contribution < self.exploration_reuse_below:
            return "exploration"
        if performance.reuse_contribution > self.exploitation_reuse_above:
            return "exploitation"
        return "default"

    def utility(self, performance: PerformanceVector, *, phase: str = "normal", formal_goal: bool = False) -> tuple[float, str]:
        profile_name = self.profile_name(performance, phase=phase, formal_goal=formal_goal)
        weights = self.profiles[profile_name]
        values = {
            "reliability": performance.reliability_lower_bound,
            "calibration": performance.calibration_score,
            "verified_utility": performance.verified_utility,
            "reuse_contribution": performance.reuse_contribution,
            "compute_efficiency": performance.compute_efficiency,
            "conflict_learning_value": performance.conflict_learning_value,
            "artifact_durability": performance.artifact_durability,
        }
        return _clamp(sum(weights[key] * float(values[key]) for key in SII_SCORING_METRICS)), profile_name

    def tier_for(self, performance: PerformanceVector, utility: float) -> SIITierRule:
        selected = self.tiers[0]
        for row in self.tiers:
            if performance.terminal_samples >= row.min_terminal_samples and utility >= row.min_utility:
                selected = row
        return selected


def default_sii_scoring_policy() -> SIIScoringPolicy:
    profiles = {
        "default": {"reliability": .25, "calibration": .15, "verified_utility": .20, "reuse_contribution": .15, "compute_efficiency": .15, "conflict_learning_value": .05, "artifact_durability": .05},
        "exploration": {"reliability": .15, "calibration": .10, "verified_utility": .20, "reuse_contribution": .15, "compute_efficiency": .10, "conflict_learning_value": .15, "artifact_durability": .15},
        "exploitation": {"reliability": .25, "calibration": .10, "verified_utility": .15, "reuse_contribution": .25, "compute_efficiency": .20, "conflict_learning_value": .025, "artifact_durability": .025},
        "formal": {"reliability": .30, "calibration": .15, "verified_utility": .20, "reuse_contribution": .05, "compute_efficiency": .05, "conflict_learning_value": .15, "artifact_durability": .10},
    }
    tier1 = SIIResourceBudget(8192, 2, 40, 15_000, 10_000, 20_000, 1.0, 1, 500, 15_000, 15_000, 2, 1)
    tier2 = SIIResourceBudget(16384, 4, 75, 45_000, 50_000, 100_000, 5.0, 2, 5_000, 45_000, 45_000, 4, 2)
    tier3 = SIIResourceBudget(32768, 8, 100, 120_000, 250_000, 500_000, 20.0, 4, 25_000, 120_000, 120_000, 8, 4)
    return SIIScoringPolicy(
        "default-governed",
        "1.0.0",
        profiles,
        (
            SIITierRule(1, 0, 0.0, tier1),
            SIITierRule(2, 12, 0.68, tier2),
            SIITierRule(3, 25, 0.82, tier3),
        ),
        metadata={"release": "0.47.0", "authority_reward": "NEVER"},
    )


@dataclass(frozen=True)
class GovernedResourceLease:
    proposer_id: str
    principal_id: str
    policy_id: str
    policy_version: str
    resource_tier: int
    contextual_utility: float
    weight_profile: str
    performance_samples: int
    terminal_samples: int
    budget: SIIResourceBudget | Mapping[str, Any]
    authority_class: str = "PROPOSER"
    direct_truth_promotion: bool = False
    direct_state_mutation: bool = False
    self_verification: bool = False
    mandatory_verification_override: str = "REQUIRED_VERIFICATION_NEVER_REDUCED"
    enforcement: str = "AASM_CONTEXT_CAPABILITY_SCHEDULER_TASKLEASE_NATIVE_BUDGETS_V047"

    def __post_init__(self):
        budget = self.budget if isinstance(self.budget, SIIResourceBudget) else SIIResourceBudget.from_dict(self.budget)
        object.__setattr__(self, "budget", budget)
        if self.authority_class != "PROPOSER" or self.direct_truth_promotion or self.direct_state_mutation or self.self_verification:
            raise ValueError("governed SII resource lease cannot carry epistemic/state authority")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "proposer_id": self.proposer_id,
            "principal_id": self.principal_id,
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
            "resource_tier": int(self.resource_tier),
            "contextual_utility": float(self.contextual_utility),
            "weight_profile": self.weight_profile,
            "performance_samples": int(self.performance_samples),
            "terminal_samples": int(self.terminal_samples),
            "budget": self.budget.to_dict(),
            "authority_class": self.authority_class,
            "direct_truth_promotion": self.direct_truth_promotion,
            "direct_state_mutation": self.direct_state_mutation,
            "self_verification": self.self_verification,
            "mandatory_verification_override": self.mandatory_verification_override,
            "enforcement": self.enforcement,
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(self.identity_payload())

    @property
    def lease_id(self) -> str:
        return f"sii-resource-lease-{self.fingerprint[:20]}"

    def to_dict(self) -> dict[str, Any]:
        return {"lease_id": self.lease_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "GovernedResourceLease":
        payload = deepcopy(dict(value)); payload.pop("lease_id", None); payload.pop("fingerprint", None); return cls(**payload)


@dataclass(frozen=True)
class GovernedSymbioticFeedback:
    proposal_id: str
    outcome_evidence_id: str
    performance: PerformanceVector
    resource_lease: GovernedResourceLease
    measured_savings: dict[str, int]
    next_best_actions: tuple[str, ...]
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "outcome_evidence_id": self.outcome_evidence_id,
            "performance": self.performance.to_dict(),
            "resource_lease": self.resource_lease.to_dict(),
            "measured_savings": deepcopy(self.measured_savings),
            "next_best_actions": list(self.next_best_actions),
            "message": self.message,
        }


def governed_sii_contract() -> dict[str, Any]:
    return {
        "contract_id": SII_GOVERNED_CONTRACT_ID,
        "contract_version": SII_GOVERNED_CONTRACT_VERSION,
        "stability": SII_GOVERNED_STABILITY,
        "legacy_participation_substrate": "aasm.sii.v1/0.2.0",
        "principal_binding": "DURABLE_POLICY_OR_CONTROLLER_ADMISSION",
        "measurement_identity_binding": "RESOLVED_FROM_DURABLE_PRINCIPAL_BINDING",
        "scoring_policy": "VERSIONED_DURABLE_POLICY",
        "resource_reward": "COMPUTE_SEARCH_CONTEXT_ONLY",
        "resource_enforcement": "EXISTING_CONTEXT_CAPABILITY_SCHEDULER_TASKLEASE_NATIVE_SOLVER_PATHS",
        "scheduler": "EXISTING_AASM_CAPABILITY_SCHEDULER",
        "task_lease": "EXISTING_AASM_TASKLEASE",
        "solver_budgets": ["timeout", "sat_conflicts", "sat_decisions", "cp_sat_deterministic_time", "cp_sat_workers", "milp_nodes", "portfolio_width"],
        "context_budget": "V0.40_CONTEXT_PROJECTION_MAX_CHARS",
        "parallel_budget": "OUTSTANDING_SII_TASK_LIMIT",
        "mandatory_verification": "NEVER_REDUCED_BY_SII",
        "truth_promotion": "EXISTING_AASM_EPISTEMIC_ADMISSION_ONLY",
        "authority_reward": "NEVER",
        "self_verification": "REJECTED",
        "direct_state_mutation": "REJECTED",
        "raw_chain_of_thought": "NOT_REQUIRED_OR_STORED",
        "metric_source": "DURABLE_OUTCOMES_AND_VALIDATED_REUSE_METRICS",
        "kernel": "V0.46_RUNTIME_EXTENDED_WITH_GOVERNANCE_MIXIN_ONLY",
    }


def _governance_projection(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    principals: dict[str, dict[str, Any]] = {}
    policies: dict[str, dict[str, Any]] = {}
    activations: list[dict[str, Any]] = []
    leases: dict[str, dict[str, Any]] = {}
    enforcement: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    ordered = sorted(records, key=lambda row: (float(row.get("created_at", 0) or 0), str(row.get("evidence_id", ""))))
    for row in ordered:
        if row.get("status", "active") != "active" or row.get("kind") != SII_GOVERNANCE_EVENT_KIND or row.get("source") != SII_GOVERNED_CONTRACT_ID:
            continue
        metadata = row.get("metadata") or {}
        record_type = str(metadata.get("sii_governance_record_type") or "")
        if record_type not in SII_GOVERNANCE_RECORD_TYPES:
            issues.append({"code": "UNKNOWN_SII_GOVERNANCE_RECORD", "evidence_id": row.get("evidence_id")}); continue
        try:
            payload = json.loads(str(row.get("statement") or "{}"))
            if record_type == "PRINCIPAL":
                binding = SIIPrincipalBinding.from_dict(payload["binding"])
                prior = principals.get(binding.principal_id)
                if prior and prior["binding"]["fingerprint"] != binding.fingerprint:
                    issues.append({"code": "SII_PRINCIPAL_REBIND_COLLISION", "principal_id": binding.principal_id, "evidence_id": row.get("evidence_id")}); continue
                principals[binding.principal_id] = {"binding": binding.to_dict(), "evidence_id": row.get("evidence_id")}
            elif record_type == "SCORING_POLICY":
                policy = SIIScoringPolicy.from_dict(payload["policy"])
                prior = policies.get(policy.policy_id)
                if prior and prior["policy"]["fingerprint"] != policy.fingerprint:
                    issues.append({"code": "SII_POLICY_ID_COLLISION", "policy_id": policy.policy_id, "evidence_id": row.get("evidence_id")}); continue
                policies[policy.policy_id] = {"policy": policy.to_dict(), "evidence_id": row.get("evidence_id")}
            elif record_type == "POLICY_ACTIVATION":
                activations.append({**payload, "evidence_id": row.get("evidence_id"), "created_at": row.get("created_at")})
            elif record_type == "RESOURCE_LEASE":
                lease = GovernedResourceLease.from_dict(payload["lease"])
                leases[lease.lease_id] = {"lease": lease.to_dict(), "evidence_id": row.get("evidence_id")}
            else:
                enforcement.append({**payload, "evidence_id": row.get("evidence_id"), "created_at": row.get("created_at")})
        except Exception as exc:
            issues.append({"code": f"SII_GOVERNANCE_{record_type}_INVALID", "evidence_id": row.get("evidence_id"), "detail": f"{type(exc).__name__}: {exc}"})
    active_policy_id = activations[-1]["policy_id"] if activations else None
    if active_policy_id is not None and active_policy_id not in policies:
        issues.append({"code": "SII_ACTIVE_POLICY_MISSING", "policy_id": active_policy_id})
    return {
        "contract": governed_sii_contract(),
        "valid": not issues,
        "issues": issues,
        "principals": principals,
        "policies": policies,
        "activations": activations,
        "active_policy_id": active_policy_id,
        "leases": leases,
        "enforcement": enforcement,
        "projection_fingerprint": semantic_fingerprint({"principals": principals, "policies": policies, "activations": activations, "leases": leases, "enforcement": enforcement, "issues": issues}),
    }


def enforce_advanced_problem_budget(problem, lease: GovernedResourceLease):
    if isinstance(problem, Mapping):
        problem = advanced_problem_from_dict(problem)
    kind = problem.to_dict()["kind"]
    budget = lease.budget
    if kind not in budget.allowed_advanced_kinds:
        raise PermissionError(f"SII resource lease does not permit advanced kind {kind}")
    if isinstance(problem, FastSATProblem):
        return problem
    if isinstance(problem, IncrementalSATProblem):
        conflict = min(int(problem.conflict_budget or budget.sat_conflict_budget), budget.sat_conflict_budget)
        decision = min(int(problem.decision_budget or budget.sat_decision_budget), budget.sat_decision_budget)
        return replace(problem, conflict_budget=conflict, decision_budget=decision)
    if isinstance(problem, CPSATSchedulingProblem):
        deterministic = min(float(problem.deterministic_time_limit or budget.cp_sat_deterministic_time), budget.cp_sat_deterministic_time)
        workers = min(int(problem.search_workers), budget.cp_sat_search_workers)
        return replace(problem, search_workers=max(1, workers), deterministic_time_limit=deterministic)
    if isinstance(problem, AdvancedMILPProblem):
        nodes = min(int(problem.node_limit if problem.node_limit is not None else budget.milp_node_limit), budget.milp_node_limit)
        return replace(problem, node_limit=nodes)
    if isinstance(problem, AdvancedConvexProblem):
        return problem
    raise TypeError(f"unsupported governed advanced problem: {type(problem)!r}")


class GovernedSymbioticIntelligenceInterface:
    def __init__(self, engine):
        self.engine = engine
        self.legacy = create_sii(engine)

    def _records(self) -> list[dict[str, Any]]:
        evidence = self.engine.snapshot.evidence
        return list(evidence.get("records", [])) if isinstance(evidence, dict) else []

    def projection(self) -> dict[str, Any]:
        projection = _governance_projection(self._records())
        if not projection["valid"]:
            raise RuntimeError(f"invalid governed SII projection: {projection['issues']}")
        return projection

    def bind_principal(self, binding: SIIPrincipalBinding | Mapping[str, Any], *, authority_id: str, authority_class: str) -> dict[str, Any]:
        if authority_class not in {"POLICY", "CONTROLLER"}:
            raise PermissionError("SII principal binding requires POLICY or CONTROLLER authority")
        binding = binding if isinstance(binding, SIIPrincipalBinding) else SIIPrincipalBinding.from_dict(binding)
        projection = self.projection(); existing = projection["principals"].get(binding.principal_id)
        if existing:
            if existing["binding"]["fingerprint"] != binding.fingerprint:
                raise ValueError("governed SII principal is already bound differently")
            return {**deepcopy(existing), "already_recorded": True}
        stored = self.engine.add_evidence(EvidenceRecord(
            SII_GOVERNANCE_EVENT_KIND,
            canonical_semantic_json({"binding": binding.to_dict(), "admitted_by": authority_id, "admission_authority_class": authority_class}),
            source=SII_GOVERNED_CONTRACT_ID,
            metadata={"sii_governance_record_type": "PRINCIPAL", "contract_version": SII_GOVERNED_CONTRACT_VERSION, "principal_id": binding.principal_id, "binding_id": binding.binding_id, "admitted_by": authority_id, "admission_authority_class": authority_class},
            evidence_id=_eid("principal", binding.fingerprint),
        ), reason="governed SII principal binding admitted")
        return {"binding": binding.to_dict(), "evidence_id": stored.evidence_id, "already_recorded": False}

    def principal(self, principal_id: str) -> dict[str, Any]:
        projection = self.projection()
        if principal_id not in projection["principals"]:
            raise KeyError(f"unbound governed SII principal: {principal_id}")
        return deepcopy(projection["principals"][principal_id])

    def admit_scoring_policy(self, policy: SIIScoringPolicy | Mapping[str, Any], *, authority_id: str, authority_class: str) -> dict[str, Any]:
        if authority_class not in {"POLICY", "CONTROLLER"}:
            raise PermissionError("SII scoring policy admission requires POLICY or CONTROLLER authority")
        policy = policy if isinstance(policy, SIIScoringPolicy) else SIIScoringPolicy.from_dict(policy)
        projection = self.projection(); existing = projection["policies"].get(policy.policy_id)
        if existing:
            if existing["policy"]["fingerprint"] != policy.fingerprint:
                raise ValueError("SII scoring policy ID collision")
            return {**deepcopy(existing), "already_recorded": True}
        stored = self.engine.add_evidence(EvidenceRecord(
            SII_GOVERNANCE_EVENT_KIND,
            canonical_semantic_json({"policy": policy.to_dict(), "admitted_by": authority_id, "admission_authority_class": authority_class}),
            source=SII_GOVERNED_CONTRACT_ID,
            metadata={"sii_governance_record_type": "SCORING_POLICY", "contract_version": SII_GOVERNED_CONTRACT_VERSION, "policy_id": policy.policy_id, "policy_version": policy.version, "policy_fingerprint": policy.fingerprint},
            evidence_id=_eid("policy", policy.fingerprint),
        ), reason="governed SII scoring policy admitted")
        return {"policy": policy.to_dict(), "evidence_id": stored.evidence_id, "already_recorded": False}

    def activate_scoring_policy(self, policy_id: str, *, authority_id: str, authority_class: str) -> dict[str, Any]:
        if authority_class not in {"POLICY", "CONTROLLER"}:
            raise PermissionError("SII scoring policy activation requires POLICY or CONTROLLER authority")
        projection = self.projection()
        if policy_id not in projection["policies"]:
            raise KeyError(f"unknown SII scoring policy: {policy_id}")
        current = projection.get("active_policy_id")
        if current == policy_id:
            return {"policy_id": policy_id, "already_active": True, "evidence_id": projection["activations"][-1]["evidence_id"]}
        policy_evidence = projection["policies"][policy_id]["evidence_id"]
        payload = {"policy_id": policy_id, "activated_by": authority_id, "activation_authority_class": authority_class, "previous_policy_id": current}
        fingerprint = semantic_fingerprint(payload)
        stored = self.engine.add_evidence(EvidenceRecord(
            SII_GOVERNANCE_EVENT_KIND,
            canonical_semantic_json(payload),
            source=SII_GOVERNED_CONTRACT_ID,
            derived_from=[policy_evidence],
            metadata={"sii_governance_record_type": "POLICY_ACTIVATION", "contract_version": SII_GOVERNED_CONTRACT_VERSION, "policy_id": policy_id, "activated_by": authority_id, "activation_authority_class": authority_class},
            evidence_id=_eid("activation", fingerprint),
        ), reason="governed SII scoring policy activated")
        return {**payload, "evidence_id": stored.evidence_id, "already_active": False}

    def install_default_policy(self, *, authority_id: str, authority_class: str) -> dict[str, Any]:
        policy = default_sii_scoring_policy(); admitted = self.admit_scoring_policy(policy, authority_id=authority_id, authority_class=authority_class); activated = self.activate_scoring_policy(policy.policy_id, authority_id=authority_id, authority_class=authority_class); return {"policy": policy.to_dict(), "admission": admitted, "activation": activated}

    def active_policy(self) -> SIIScoringPolicy:
        projection = self.projection(); policy_id = projection.get("active_policy_id")
        if not policy_id:
            raise RuntimeError("no governed SII scoring policy is active")
        return SIIScoringPolicy.from_dict(projection["policies"][policy_id]["policy"])

    def register_proposer(self, *, principal_id: str, name: str, kind: str = "llm", provider: str = "", model_id: str = "", version: str = "", metadata: Mapping[str, Any] | None = None) -> dict[str, Any]:
        binding = SIIPrincipalBinding.from_dict(self.principal(principal_id)["binding"])
        if not binding.active or not binding.can_propose:
            raise PermissionError("governed principal is not admitted to propose through SII")
        registered = self.legacy.register(principal_id=principal_id, name=name, kind=kind, provider=provider, model_id=model_id, version=version, metadata={**dict(metadata or {}), "governed_sii": True, "principal_binding_id": binding.binding_id})
        return {**registered, "principal_binding": binding.to_dict(), "contract": governed_sii_contract()}

    def _proposer_principal(self, proposer_id: str) -> str:
        projection = self.legacy.projection()
        try:
            return str(projection["identities"][proposer_id]["identity"]["principal_id"])
        except KeyError:
            raise KeyError(f"unknown SII proposer: {proposer_id}") from None

    def performance(self, proposer_id: str, *, window: int | None = None) -> PerformanceVector:
        policy = self.active_policy(); return self.legacy.performance(proposer_id, window=int(window or policy.projection_window))

    def resource_lease(self, proposer_id: str, *, phase: str = "normal", formal_goal: bool = False, persist: bool = False) -> dict[str, Any]:
        principal_id = self._proposer_principal(proposer_id); binding = SIIPrincipalBinding.from_dict(self.principal(principal_id)["binding"])
        if not binding.active or not binding.can_propose:
            raise PermissionError("inactive/unadmitted SII proposer principal")
        policy = self.active_policy(); performance = self.legacy.performance(proposer_id, window=policy.projection_window); utility, profile = policy.utility(performance, phase=phase, formal_goal=formal_goal); tier = policy.tier_for(performance, utility)
        lease = GovernedResourceLease(proposer_id, principal_id, policy.policy_id, policy.version, tier.tier, utility, profile, performance.samples, performance.terminal_samples, tier.budget)
        projection = self.projection(); existing = projection["leases"].get(lease.lease_id)
        if existing:
            return {"lease": lease.to_dict(), "evidence_id": existing["evidence_id"], "already_recorded": True}
        if not persist:
            return {"lease": lease.to_dict(), "evidence_id": None, "already_recorded": False}
        policy_evidence = projection["policies"][policy.policy_id]["evidence_id"]; principal_evidence = projection["principals"][principal_id]["evidence_id"]
        stored = self.engine.add_evidence(EvidenceRecord(
            SII_GOVERNANCE_EVENT_KIND,
            canonical_semantic_json({"lease": lease.to_dict()}),
            source=SII_GOVERNED_CONTRACT_ID,
            derived_from=sorted({policy_evidence, principal_evidence}),
            metadata={"sii_governance_record_type": "RESOURCE_LEASE", "contract_version": SII_GOVERNED_CONTRACT_VERSION, "lease_id": lease.lease_id, "proposer_id": proposer_id, "principal_id": principal_id, "policy_id": policy.policy_id, "resource_tier": tier.tier, "authority_reward": "NEVER"},
            evidence_id=_eid("lease", lease.fingerprint),
        ), reason="governed SII resource lease issued")
        return {"lease": lease.to_dict(), "evidence_id": stored.evidence_id, "already_recorded": False}

    def submit(self, proposal: StructuredProposal | Mapping[str, Any], *, phase: str = "normal") -> dict[str, Any]:
        proposal = proposal if isinstance(proposal, StructuredProposal) else StructuredProposal.from_dict(proposal)
        principal_id = self._proposer_principal(proposal.proposer_id); binding = SIIPrincipalBinding.from_dict(self.principal(principal_id)["binding"])
        if not binding.active or not binding.can_propose:
            raise PermissionError("governed principal is not admitted to submit SII proposals")
        submitted = self.legacy.submit(proposal); governed = self.resource_lease(proposal.proposer_id, phase=phase, persist=True)
        submitted["resource_lease"] = governed["lease"]; submitted["resource_lease_evidence_id"] = governed["evidence_id"]; submitted["contract"] = governed_sii_contract(); return submitted

    def measure_proposal_outcome(self, proposal_id: str, *, measured_by_principal_id: str, **kwargs) -> GovernedSymbioticFeedback:
        binding = SIIPrincipalBinding.from_dict(self.principal(measured_by_principal_id)["binding"])
        if not binding.active or not binding.can_measure or binding.authority_class not in MEASUREMENT_AUTHORITIES:
            raise PermissionError("principal is not durably admitted as an SII measurement authority")
        legacy_projection = self.legacy.projection()
        try:
            proposer_id = legacy_projection["proposals"][proposal_id]["proposal"]["proposer_id"]
        except KeyError:
            raise KeyError(f"unknown SII proposal: {proposal_id}") from None
        if self._proposer_principal(proposer_id) == measured_by_principal_id:
            raise ValueError("a governed SII principal cannot measure its own proposal")
        feedback = self.legacy.measure_proposal_outcome(proposal_id, measured_by=measured_by_principal_id, authority_class=binding.authority_class, **kwargs)
        governed = GovernedResourceLease.from_dict(self.resource_lease(proposer_id, persist=True)["lease"])
        return GovernedSymbioticFeedback(feedback.proposal_id, feedback.outcome_evidence_id, feedback.performance, governed, feedback.measured_savings, feedback.next_best_actions, f"{feedback.message} | governed policy {governed.policy_version}")

    def context_for(self, proposer_id: str, *, scope_id: str, query: str = "", phase: str = "normal", formal_goal: bool = False, allowed_privacy_levels: Sequence[str] = ("AGENT", "USER", "SHARED", "PUBLIC"), memory_kinds: Sequence[str] = (), objective_node_ids: Sequence[str] = (), max_memory_items: int = 20, max_frontier_items: int = 20) -> dict[str, Any]:
        governed = self.resource_lease(proposer_id, phase=phase, formal_goal=formal_goal, persist=True); lease = GovernedResourceLease.from_dict(governed["lease"])
        request = ContextProjectionRequest(scope_id=scope_id, query=query, allowed_privacy_levels=tuple(allowed_privacy_levels), memory_kinds=tuple(memory_kinds), objective_node_ids=tuple(objective_node_ids), max_memory_items=max_memory_items, max_frontier_items=max_frontier_items, max_chars=lease.budget.context_budget_tokens * 4, metadata={"principal_id": lease.principal_id, "sii_proposer_id": proposer_id, "sii_resource_lease_id": lease.lease_id, "sii_policy_id": lease.policy_id, "resource_tier": lease.resource_tier})
        return {"contract": governed_sii_contract(), "resource_lease": lease.to_dict(), "resource_lease_evidence_id": governed["evidence_id"], "context_projection": self.engine.context_projection(request), "reasoning_frontier": self.engine.reasoning_frontier(request), "note": "SII limits context size only; every returned fact retains its original epistemic state and authority."}

    def outstanding_discretionary_tasks(self, proposer_id: str) -> int:
        resources = self.engine.snapshot.resources if isinstance(self.engine.snapshot.resources, dict) else {}
        tasks = [row for row in resources.get("tasks", []) if (row.get("metadata") or {}).get("sii_proposer_id") == proposer_id]
        leases = self.engine.list_leases(); total = 0
        for task in tasks:
            task_leases = [row for row in leases if row.get("task_id") == task.get("task_id")]
            if not task_leases or any(row.get("status") == "ACTIVE" for row in task_leases):
                total += 1
            elif not any(row.get("status") in {"COMPLETED", "FAILED"} for row in task_leases):
                total += 1
        return total

    def record_enforcement(self, lease: GovernedResourceLease, *, target_kind: str, target_id: str, request_evidence_ids: Sequence[str] = (), detail: Mapping[str, Any] | None = None) -> dict[str, Any]:
        projection = self.projection(); lease_row = projection["leases"].get(lease.lease_id)
        if not lease_row:
            raise KeyError("governed SII resource lease must be durably issued before enforcement")
        payload = {"lease_id": lease.lease_id, "proposer_id": lease.proposer_id, "principal_id": lease.principal_id, "target_kind": target_kind, "target_id": target_id, "detail": deepcopy(dict(detail or {}))}
        fingerprint = semantic_fingerprint(payload)
        evidence_id = _eid("enforcement", fingerprint)
        existing = next((row for row in projection["enforcement"] if row.get("lease_id") == lease.lease_id and row.get("target_kind") == target_kind and row.get("target_id") == target_id and semantic_fingerprint({k: row.get(k) for k in ("lease_id", "proposer_id", "principal_id", "target_kind", "target_id", "detail")}) == fingerprint), None)
        if existing:
            return {**payload, "evidence_id": existing["evidence_id"], "already_recorded": True}
        stored = self.engine.add_evidence(EvidenceRecord(SII_GOVERNANCE_EVENT_KIND, canonical_semantic_json(payload), source=SII_GOVERNED_CONTRACT_ID, derived_from=sorted(set([lease_row["evidence_id"], *request_evidence_ids])), metadata={"sii_governance_record_type": "ENFORCEMENT", "contract_version": SII_GOVERNED_CONTRACT_VERSION, "lease_id": lease.lease_id, "proposer_id": lease.proposer_id, "target_kind": target_kind, "target_id": target_id, "authority_reward": "NEVER"}, evidence_id=evidence_id), reason="governed SII resource budget enforced")
        return {**payload, "evidence_id": stored.evidence_id, "already_recorded": False}


def create_governed_sii(engine) -> GovernedSymbioticIntelligenceInterface:
    return GovernedSymbioticIntelligenceInterface(engine)


__all__ = [
    "SII_GOVERNED_CONTRACT_ID", "SII_GOVERNED_CONTRACT_VERSION", "SII_GOVERNED_STABILITY",
    "SIIPrincipalBinding", "SIIResourceBudget", "SIITierRule", "SIIScoringPolicy",
    "GovernedResourceLease", "GovernedSymbioticFeedback", "default_sii_scoring_policy",
    "governed_sii_contract", "enforce_advanced_problem_budget",
    "GovernedSymbioticIntelligenceInterface", "create_governed_sii",
]
