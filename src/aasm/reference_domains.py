from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Callable

from .evidence import EvidenceRecord
from .hierarchical_memory import ContextProjectionRequest
from .model import ProblemSpec
from .reasoning import Claim, ReasoningProducer
from .reuse_model import ReuseCandidate, ReuseRequest
from .runtime_v41 import AASMEngine
from .solver_types import SolverStepRequest

REFERENCE_DOMAIN_CONTRACT_ID = "aasm.reference-domains.v1"
REFERENCE_DOMAIN_CONTRACT_VERSION = "0.1.0"
REFERENCE_DOMAIN_IDS = (
    "constraint-solving",
    "software-repair",
    "research-synthesis",
    "formal-reasoning",
    "long-horizon-memory",
)


def reference_domain_contract() -> dict[str, Any]:
    return {
        "contract_id": REFERENCE_DOMAIN_CONTRACT_ID,
        "contract_version": REFERENCE_DOMAIN_CONTRACT_VERSION,
        "authority": "REFERENCE_HARNESS_ONLY",
        "kernel_changes": "NONE",
        "network_required": False,
        "model_key_required": False,
        "domains": list(REFERENCE_DOMAIN_IDS),
        "required_boundaries": [
            "durable_reuse_survives_hot_index_deletion",
            "invalid_or_inapplicable_reuse_is_rejected",
            "solver_skips_only_after_validated_reuse",
            "reasoning_truth_change_invalidates_reuse",
            "memory_privacy_and_revocation_invalidate_reuse",
            "replay_matches_persisted_state",
        ],
    }


@dataclass(frozen=True)
class ReferenceDomainResult:
    domain_id: str
    checks: dict[str, bool]
    details: dict[str, Any] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return bool(self.checks) and all(self.checks.values())

    def to_dict(self) -> dict[str, Any]:
        return {
            "domain_id": self.domain_id,
            "passed": self.passed,
            "checks": dict(sorted(self.checks.items())),
            "details": self.details,
        }


def _reasons(result: dict[str, Any]) -> set[str]:
    return {
        str(reason)
        for rejection in result.get("rejections", [])
        for reason in rejection.get("reasons", [])
    }


def _replay_exact(engine: AASMEngine) -> bool:
    return engine.replay().canonical_hash() == engine.snapshot.canonical_hash()


def _seed_evidence(engine: AASMEngine, kind: str, statement: str) -> EvidenceRecord:
    return engine.add_evidence(
        EvidenceRecord(kind=kind, statement=statement, source=REFERENCE_DOMAIN_CONTRACT_ID),
        reason="v0.42 reference-domain fixture",
    )


def _register(
    engine: AASMEngine,
    request: ReuseRequest,
    source_type: str,
    source_id: str,
    *,
    created_at: float | None = None,
    verification_strength: str = "",
    reusable_modes: tuple[str, ...] = ("EXACT",),
) -> ReuseCandidate:
    candidate = ReuseCandidate(
        kind=request.kind,
        request_fingerprint=request.fingerprint,
        source=engine.canonical_reuse_ref(source_type, source_id),
        semantic_payload=request.semantic_payload,
        environment_fingerprint=request.environment_fingerprint,
        dependency_fingerprints=request.dependency_fingerprints,
        created_at=created_at,
        effect_class=request.effect_class,
        verification_strength=verification_strength,
        reusable_modes=reusable_modes,
    )
    engine.register_reuse_candidate(
        candidate,
        authority_id="reference-policy",
        authority_class="POLICY",
    )
    return candidate


def _constraint_solving() -> ReferenceDomainResult:
    engine = AASMEngine(ProblemSpec("v0.42 constraint-solving stress"))
    source = _seed_evidence(engine, "subproblem_result", "x=4,y=6 satisfies the bounded fixture")
    request = ReuseRequest(
        kind="SUBPROBLEM_RESULT",
        semantic_payload={"constraints": ["x+y=10", "x<y"], "solution": {"x": 4, "y": 6}},
        environment_fingerprint="constraint-engine-v1",
        dependency_fingerprints=("constraint-set-v1",),
    )
    _register(engine, request, "EVIDENCE", source.evidence_id)
    hot_hit = engine.lookup_reuse(request)
    engine._reuse_hot_index().clear()
    durable_hit = engine.lookup_reuse(request)
    mismatched_environment = engine.lookup_reuse(ReuseRequest(
        kind=request.kind,
        semantic_payload=request.semantic_payload,
        environment_fingerprint="constraint-engine-v2",
        dependency_fingerprints=request.dependency_fingerprints,
    ))
    step = engine.solver_step(SolverStepRequest(scope_id="root"), reuse_request=request)
    checks = {
        "exact_reuse_hit": hot_hit["hit"] is True,
        "hot_index_deletion_does_not_change_truth": durable_hit["hit"] is True,
        "environment_change_rejects_reuse": (
            mismatched_environment["hit"] is False
            and "environment_mismatch" in _reasons(mismatched_environment)
        ),
        "solver_skips_only_after_reuse_certificate": (
            step["phase"] == "REUSE"
            and step["action"] == "SKIP_EXECUTION"
            and bool(step["reuse_certificate_id"])
        ),
        "replay_exact": _replay_exact(engine),
    }
    return ReferenceDomainResult(
        "constraint-solving",
        checks,
        {
            "reuse_mode": (durable_hit.get("validation") or {}).get("mode"),
            "solver_action": step["action"],
            "rejections": sorted(_reasons(mismatched_environment)),
        },
    )


def _software_repair() -> ReferenceDomainResult:
    engine = AASMEngine(ProblemSpec("v0.42 software-repair stress"))
    source = _seed_evidence(engine, "tool_observation", "test_widget fails because parser contract changed")
    request = ReuseRequest(
        kind="TOOL_OBSERVATION",
        semantic_payload={"test": "test_widget", "diagnosis": "parser-contract-change"},
        environment_fingerprint="repo-tree-a",
        dependency_fingerprints=("lockfile-a", "parser-a"),
        freshness_seconds=60.0,
        as_of=120.0,
        effect_class="READ_ONLY_FRESHNESS_BOUND",
    )
    _register(engine, request, "EVIDENCE", source.evidence_id, created_at=100.0)
    fresh = engine.lookup_reuse(request)
    expired = engine.lookup_reuse(ReuseRequest(
        kind=request.kind,
        semantic_payload=request.semantic_payload,
        environment_fingerprint=request.environment_fingerprint,
        dependency_fingerprints=request.dependency_fingerprints,
        freshness_seconds=60.0,
        as_of=200.0,
        effect_class=request.effect_class,
    ))
    dependency_changed = engine.lookup_reuse(ReuseRequest(
        kind=request.kind,
        semantic_payload=request.semantic_payload,
        environment_fingerprint=request.environment_fingerprint,
        dependency_fingerprints=("lockfile-b", "parser-a"),
        freshness_seconds=60.0,
        as_of=120.0,
        effect_class=request.effect_class,
    ))
    effectful = engine.lookup_reuse(ReuseRequest(
        kind=request.kind,
        semantic_payload=request.semantic_payload,
        environment_fingerprint=request.environment_fingerprint,
        dependency_fingerprints=request.dependency_fingerprints,
        effect_class="NON_IDEMPOTENT_EFFECT",
    ))
    checks = {
        "fresh_observation_reused": fresh["hit"] is True,
        "expired_observation_rejected": (
            expired["hit"] is False and "freshness_requirement_failed" in _reasons(expired)
        ),
        "dependency_change_rejected": (
            dependency_changed["hit"] is False
            and "dependency_fingerprint_mismatch" in _reasons(dependency_changed)
        ),
        "non_idempotent_effect_never_reused": (
            effectful["hit"] is False
            and "non_idempotent_effect_never_reused" in _reasons(effectful)
        ),
        "replay_exact": _replay_exact(engine),
    }
    return ReferenceDomainResult(
        "software-repair",
        checks,
        {
            "expired_reasons": sorted(_reasons(expired)),
            "dependency_reasons": sorted(_reasons(dependency_changed)),
            "effect_reasons": sorted(_reasons(effectful)),
        },
    )


def _research_synthesis() -> ReferenceDomainResult:
    engine = AASMEngine(ProblemSpec("v0.42 research-synthesis stress"))
    evidence = _seed_evidence(engine, "observation", "study delta contradicts the aggregate-only explanation")
    artifact = Claim(
        "effect is modified by prior knowledge",
        ReasoningProducer("reference-researcher", "PROPOSER"),
        evidence_ids=(evidence.evidence_id,),
    )
    engine.propose_artifact(artifact)
    engine.request_verification(
        artifact.artifact_id,
        verifier_ids=["reference-verifier"],
        requester_id="reference-researcher",
    )
    engine.record_verification(
        artifact.artifact_id,
        verifier_id="reference-verifier",
        verdict="PASS",
        evidence_ids=[evidence.evidence_id],
    )
    engine.authorize_artifact(
        artifact.artifact_id,
        authority_id="reference-policy",
        authority_class="POLICY",
    )
    request = ReuseRequest(
        kind="LLM_RESULT",
        semantic_payload={"claim": artifact.statement, "population": "reference-corpus"},
    )
    _register(engine, request, "REASONING_ARTIFACT", artifact.artifact_id)
    admitted = engine.lookup_reuse(request)
    engine.mark_stale(
        artifact.artifact_id,
        reason="reference corpus changed",
        authority_id="reference-verifier",
        evidence_ids=[evidence.evidence_id],
    )
    stale = engine.lookup_reuse(request)
    checks = {
        "authorized_reasoning_is_reusable": admitted["hit"] is True,
        "truth_change_invalidates_reasoning_reuse": (
            stale["hit"] is False and "stale_or_invalid_source" in _reasons(stale)
        ),
        "reasoning_source_is_durably_stale": engine.reasoning_report(artifact.artifact_id)["state"] == "STALE",
        "replay_exact": _replay_exact(engine),
    }
    return ReferenceDomainResult(
        "research-synthesis",
        checks,
        {
            "artifact_id": artifact.artifact_id,
            "final_reasoning_state": engine.reasoning_report(artifact.artifact_id)["state"],
            "rejections": sorted(_reasons(stale)),
        },
    )


def _formal_reasoning() -> ReferenceDomainResult:
    engine = AASMEngine(ProblemSpec("v0.42 formal-reasoning stress"))
    source = _seed_evidence(engine, "formal_verification", "two independent solvers proved the reference invariant")
    request = ReuseRequest(
        kind="FORMAL_VERIFICATION_RESULT",
        semantic_payload={"formula": "(assert (not invariant))", "status": "PROVED"},
        required_strength="MULTI_SOLVER_AGREEMENT",
    )
    weak = ReuseCandidate(
        kind=request.kind,
        request_fingerprint=request.fingerprint,
        source=engine.canonical_reuse_ref("EVIDENCE", source.evidence_id),
        semantic_payload=request.semantic_payload,
        verification_strength="SOLVER_VERDICT",
        reusable_modes=("EXACT",),
    )
    engine.register_reuse_candidate(weak, authority_id="reference-policy", authority_class="POLICY")
    weak_lookup = engine.lookup_reuse(request)
    strong = ReuseCandidate(
        kind=request.kind,
        request_fingerprint=request.fingerprint,
        source=engine.canonical_reuse_ref("EVIDENCE", source.evidence_id),
        semantic_payload=request.semantic_payload,
        verification_strength="MULTI_SOLVER_AGREEMENT",
        reusable_modes=("EXACT",),
    )
    engine.register_reuse_candidate(strong, authority_id="reference-policy", authority_class="POLICY")
    strong_lookup = engine.lookup_reuse(request)
    step = engine.solver_step(SolverStepRequest(scope_id="root"), reuse_request=request)
    checks = {
        "insufficient_verification_strength_rejected": (
            weak_lookup["hit"] is False
            and "verification_strength_mismatch" in _reasons(weak_lookup)
        ),
        "required_verification_strength_reused": strong_lookup["hit"] is True,
        "formal_reuse_skips_execution_after_certificate": (
            step["phase"] == "REUSE" and step["action"] == "SKIP_EXECUTION"
        ),
        "replay_exact": _replay_exact(engine),
    }
    return ReferenceDomainResult(
        "formal-reasoning",
        checks,
        {
            "weak_rejections": sorted(_reasons(weak_lookup)),
            "accepted_strength": (strong_lookup.get("candidate") or {}).get("verification_strength"),
            "solver_action": step["action"],
        },
    )


def _long_horizon_memory() -> ReferenceDomainResult:
    engine = AASMEngine(ProblemSpec("v0.42 long-horizon-memory stress"))
    proposal = engine.propose_memory_operation(
        "STORE",
        scope_id="root",
        proposer_id="reference-agent",
        content={"decision": "retain parser contract A", "basis": "verified fixture"},
        privacy_level="USER",
        retention_policy="permanent",
        metadata={"privacy_principal_id": "user-a"},
    )
    decision_id = proposal["decision"]["decision_id"]
    memory_id = proposal["memory"]["memory_id"]
    engine.authorize_memory_operation(decision_id, authority_id="reference-policy", authority_class="POLICY")
    engine.commit_memory_operation(decision_id, worker_id="reference-worker")
    visible_a = {
        row["memory_id"]
        for row in engine.context_projection(ContextProjectionRequest(metadata={"principal_id": "user-a"}))["memory_items"]
    }
    visible_b = {
        row["memory_id"]
        for row in engine.context_projection(ContextProjectionRequest(metadata={"principal_id": "user-b"}))["memory_items"]
    }
    request = ReuseRequest(
        kind="CONTEXT_PROJECTION",
        semantic_payload={"memory_id": memory_id, "query": "parser contract"},
        privacy_level="USER",
        privacy_principal_id="user-a",
    )
    _register(engine, request, "MEMORY", memory_id)
    owner_lookup = engine.lookup_reuse(request)
    other_lookup = engine.lookup_reuse(ReuseRequest(
        kind=request.kind,
        semantic_payload=request.semantic_payload,
        privacy_level="USER",
        privacy_principal_id="user-b",
    ))
    forget = engine.propose_memory_forget(memory_id, proposer_id="user-a", reason="reference revocation")
    forget_decision = forget["decision"]["decision_id"]
    engine.authorize_memory_operation(forget_decision, authority_id="reference-policy", authority_class="POLICY")
    engine.commit_memory_operation(forget_decision, worker_id="reference-worker")
    revoked_lookup = engine.lookup_reuse(request)
    checks = {
        "owner_context_can_see_memory": memory_id in visible_a,
        "other_principal_cannot_see_memory": memory_id not in visible_b,
        "owner_can_reuse_active_memory": owner_lookup["hit"] is True,
        "other_principal_cannot_reuse_memory": (
            other_lookup["hit"] is False and "privacy_principal_mismatch" in _reasons(other_lookup)
        ),
        "revoked_memory_cannot_be_reused": (
            revoked_lookup["hit"] is False and "stale_or_invalid_source" in _reasons(revoked_lookup)
        ),
        "memory_is_durably_revoked": engine.hierarchical_memory_report()["memories"][memory_id]["status"] == "REVOKED",
        "replay_exact": _replay_exact(engine),
    }
    return ReferenceDomainResult(
        "long-horizon-memory",
        checks,
        {
            "memory_id": memory_id,
            "privacy_rejections": sorted(_reasons(other_lookup)),
            "revocation_rejections": sorted(_reasons(revoked_lookup)),
        },
    )


_RUNNERS: dict[str, Callable[[], ReferenceDomainResult]] = {
    "constraint-solving": _constraint_solving,
    "software-repair": _software_repair,
    "research-synthesis": _research_synthesis,
    "formal-reasoning": _formal_reasoning,
    "long-horizon-memory": _long_horizon_memory,
}


def run_reference_domain_stress(domain_id: str | None = None) -> dict[str, Any]:
    if domain_id is not None and domain_id not in _RUNNERS:
        raise ValueError(f"unknown reference domain: {domain_id}")
    selected = [domain_id] if domain_id else list(REFERENCE_DOMAIN_IDS)
    results = [_RUNNERS[name]().to_dict() for name in selected]
    checks_total = sum(len(row["checks"]) for row in results)
    checks_passed = sum(sum(bool(value) for value in row["checks"].values()) for row in results)
    return {
        "contract": reference_domain_contract(),
        "passed": all(row["passed"] for row in results),
        "domain_count": len(results),
        "checks_total": checks_total,
        "checks_passed": checks_passed,
        "domains": results,
    }


__all__ = [
    "REFERENCE_DOMAIN_CONTRACT_ID",
    "REFERENCE_DOMAIN_CONTRACT_VERSION",
    "REFERENCE_DOMAIN_IDS",
    "ReferenceDomainResult",
    "reference_domain_contract",
    "run_reference_domain_stress",
]
