from __future__ import annotations

from pathlib import Path

import pytest

from aasm import (
    AASMEngine,
    CapabilityProvider,
    Claim,
    ExecutableFormalWorker,
    FormalStatement,
    FormalVerificationPolicy,
    FormalVerificationRequest,
    FormalVerificationResult,
    PatternMachine,
    ProcessResult,
    ReasoningProducer,
    ScopedLegalTransition,
    SolverIdentity,
    TypedEventSchema,
    __version__,
    aggregate_formal_results,
    canonicalize_solver_status,
    default_formal_providers,
    run_typed_capability_conformance,
    validate_public_api_contract,
)
from aasm.cli import build_parser
from aasm.persistence.sqlite import SQLiteStore
from aasm.model import ProblemSpec


SMT_SOURCE = "(set-logic QF_UF)\n(assert false)\n(check-sat)\n"


def claim_fixture(engine: AASMEngine):
    artifact = Claim("component invariant holds", ReasoningProducer("agent-v39", "PROPOSER"))
    engine.propose_artifact(artifact)
    formal = engine.formalize_artifact(
        artifact.artifact_id,
        logic="smtlib2",
        query_mode="VALIDITY",
        canonical_source=SMT_SOURCE,
        conjecture="component invariant holds",
        compiler_id="fixture.compiler",
        compiler_version="1.0.0",
    )
    return artifact, formal["formal_statement"]


def provider_by_id(provider_id: str) -> CapabilityProvider:
    return next(row for row in default_formal_providers() if row.provider_id == provider_id)


def install_provider(engine: AASMEngine, provider_id: str):
    provider = provider_by_id(provider_id)
    return engine.register_formal_provider_runtime(
        provider,
        authority_id="policy-v39",
        authority_class="POLICY",
        worker_id=f"worker-{provider_id}",
    )


def make_result(request: dict, provider_id: str, status: str = "PROVED") -> FormalVerificationResult:
    return FormalVerificationResult(
        request_id=request["request_id"],
        request_fingerprint=request["fingerprint"],
        formal_statement_fingerprint=request["formal_statement"]["fingerprint"],
        canonical_status=status,
        solver=SolverIdentity(
            provider_id,
            version="fixture-1",
            container_digest=f"sha256:{provider_id}-fixture",
            invocation=(provider_id,),
        ),
        raw_status="unsat" if status == "PROVED" else "sat",
        time_ms=3,
        verification_strength="SOLVER_VERDICT",
        raw_output_sha256="f" * 64,
    )


def progress_guard(engine: AASMEngine, obligation_id: str):
    engine.enable_obligation(obligation_id)
    engine.set_obligation_status(obligation_id, "IN_PROGRESS")
    engine.set_obligation_status(obligation_id, "VERIFYING")
    engine.set_obligation_status(obligation_id, "VERIFIED")


def test_v39_contract_version_and_public_surface():
    assert __version__ == "0.44.0"
    report = validate_public_api_contract()
    assert report["valid"] is True, report
    assert report["contract"]["contract_version"] == "0.20.0"
    assert report["contract"]["typed_protocol"]["direct_pattern_register"] == "REJECTED"
    assert report["contract"]["capability_abi"]["lease_boundary"] == "AASM_TASK_LEASE"
    assert report["contract"]["formal_verification"]["solver_authority"] == "EVIDENCE_ONLY"
    assert report["contract"]["formal_verification"]["lean_rejection"] == "NOT_A_REFUTATION"


def test_typed_pattern_requires_policy_and_invalid_payload_has_no_durable_side_effect():
    engine = AASMEngine(ProblemSpec("typed pattern"))
    schema = TypedEventSchema(
        "READY",
        {
            "type": "object",
            "required": ["ok"],
            "properties": {"ok": {"type": "boolean"}},
            "additionalProperties": False,
        },
        guards=("guard.ready",),
    )
    pattern = PatternMachine(
        "fixture-pattern",
        "1.0.0",
        "root",
        ("INIT", "DONE"),
        "INIT",
        (ScopedLegalTransition("INIT", "READY", "DONE", "ready"),),
        (schema,),
    )
    with pytest.raises(PermissionError, match="POLICY or CONTROLLER"):
        engine.admit_typed_pattern(pattern, authority_id="agent", authority_class="PROPOSER")
    engine.admit_typed_pattern(pattern, authority_id="policy", authority_class="POLICY")
    before = len(engine.events)
    with pytest.raises(ValueError, match="expected JSON type"):
        engine.propose_typed_transition(pattern.pattern_id, "READY", {"ok": "yes"}, proposer_id="agent")
    assert len(engine.events) == before


def test_unknown_pattern_scope_is_rejected_before_durable_admission():
    engine = AASMEngine(ProblemSpec("typed unknown scope"))
    schema = TypedEventSchema("READY", {"type": "object"})
    pattern = PatternMachine(
        "unknown-scope-pattern",
        "1.0.0",
        "missing-scope",
        ("INIT", "DONE"),
        "INIT",
        (ScopedLegalTransition("INIT", "READY", "DONE", "ready"),),
        (schema,),
    )
    before = len(engine.events)
    with pytest.raises(KeyError, match="unknown typed pattern scope"):
        engine.admit_typed_pattern(pattern, authority_id="policy", authority_class="POLICY")
    assert len(engine.events) == before

def test_typed_transition_compiles_guards_to_obligations_and_only_policy_activates():
    engine = AASMEngine(ProblemSpec("typed transition"))
    schema = TypedEventSchema(
        "READY",
        {"type": "object", "required": ["ok"], "properties": {"ok": {"type": "boolean"}}},
        guards=("guard.ready",),
    )
    pattern = PatternMachine(
        "fixture-pattern",
        "1.0.0",
        "root",
        ("INIT", "DONE"),
        "INIT",
        (ScopedLegalTransition("INIT", "READY", "DONE", "ready"),),
        (schema,),
    )
    engine.admit_typed_pattern(pattern, authority_id="policy", authority_class="POLICY")
    proposed = engine.propose_typed_transition(pattern.pattern_id, "READY", {"ok": True}, proposer_id="agent")
    decision_id = proposed["proposal"]["decision_id"]
    obligation_id = proposed["proposal"]["obligation_ids"][0]
    assert engine.calculus_report()["decisions"][decision_id]["status"] == "PROPOSED"
    with pytest.raises(ValueError, match="obligations are incomplete"):
        engine.authorize_typed_transition(decision_id, authority_id="policy", authority_class="POLICY")
    progress_guard(engine, obligation_id)
    with pytest.raises(PermissionError, match="POLICY or CONTROLLER"):
        engine.authorize_typed_transition(decision_id, authority_id="agent", authority_class="PROPOSER")
    authorized = engine.authorize_typed_transition(decision_id, authority_id="policy", authority_class="POLICY")
    assert authorized["activation"]["decision"]["status"] == "ACTIVE"
    assert engine.calculus_report()["active_values"][f"typed.pattern.{pattern.pattern_id}.state"] == "DONE"


def test_capability_provider_requires_admitted_contract_and_resource_tokens():
    engine = AASMEngine(ProblemSpec("capability provider"))
    engine.install_default_formal_capability_contracts(authority_id="policy", authority_class="POLICY")
    provider = provider_by_id("z3")
    with pytest.raises(KeyError, match="unknown capability resource"):
        engine.register_capability_provider(provider, authority_id="policy", authority_class="POLICY")
    installed = install_provider(engine, "z3")
    assert installed["provider"]["provider"]["provider_id"] == "z3"
    report = engine.capability_report("formal.smt")
    assert "z3" in report["providers"]
    resource = next(row for row in engine.list_resources() if row["resource_id"] == provider.resource_id)
    assert provider.capability_token in resource["capabilities"]
    assert provider.provider_token in resource["capabilities"]


def test_invalid_provider_runtime_is_rejected_before_resource_or_worker_side_effects():
    engine = AASMEngine(ProblemSpec("provider atomic validation"))
    engine.install_default_formal_capability_contracts(authority_id="policy", authority_class="POLICY")
    bad = CapabilityProvider(
        "bad-z3",
        "formal.smt",
        "9.9.9",
        "bad-z3-resource",
        "z3",
        ("smtlib2",),
        ("VALIDITY",),
    )
    before_resources = engine.list_resources()
    before_workers = engine.list_workers()
    before_events = len(engine.events)
    with pytest.raises(ValueError, match="version does not match"):
        engine.register_formal_provider_runtime(bad, authority_id="policy", authority_class="POLICY")
    assert engine.list_resources() == before_resources
    assert engine.list_workers() == before_workers
    assert len(engine.events) == before_events


def test_formalization_binds_exact_reasoning_artifact_fingerprint():
    engine = AASMEngine(ProblemSpec("formalization provenance"))
    artifact = Claim("x", ReasoningProducer("agent", "PROPOSER"))
    engine.propose_artifact(artifact)
    entry = engine.reasoning_report(artifact.artifact_id)
    good = FormalStatement(
        "smtlib2",
        "VALIDITY",
        SMT_SOURCE,
        source_artifact_ids=(artifact.artifact_id,),
        source_artifact_fingerprints={artifact.artifact_id: entry["artifact"]["fingerprint"]},
    )
    assert engine.propose_formal_statement(good)["formal_statement"]["fingerprint"] == good.fingerprint
    bad = FormalStatement(
        "smtlib2",
        "VALIDITY",
        SMT_SOURCE + "; different\n",
        source_artifact_ids=(artifact.artifact_id,),
        source_artifact_fingerprints={artifact.artifact_id: "0" * 64},
    )
    with pytest.raises(ValueError, match="fingerprints do not match"):
        engine.propose_formal_statement(bad)


def test_solver_semantics_do_not_confuse_sat_or_lean_failure_with_refutation():
    assert canonicalize_solver_status("VALIDITY", "z3", "unsat") == "PROVED"
    assert canonicalize_solver_status("VALIDITY", "z3", "sat") == "COUNTERMODEL"
    assert canonicalize_solver_status("SATISFIABILITY", "z3", "sat") == "SAT"
    assert canonicalize_solver_status("VALIDITY", "lean4", "Rejected", returncode=1) == "UNKNOWN"


def test_executable_worker_normalizes_solver_output_without_raw_output_identity():
    statement = FormalStatement("smtlib2", "VALIDITY", SMT_SOURCE)
    request = FormalVerificationRequest(statement, "formal.smt", "0.1.0", "formal-obligation-fixture")
    worker = ExecutableFormalWorker(
        "z3",
        "z3",
        version="fixture-1",
        container_digest="sha256:fixture",
        runner=lambda argv, stdin, timeout, mode: ProcessResult(0, "unsat\n", "diagnostic\n", 4),
    )
    result = worker.run(request)
    assert result.canonical_status == "PROVED"
    assert result.verification_strength == "SOLVER_VERDICT"
    assert len(result.raw_output_sha256) == 64
    assert result.solver.container_digest == "sha256:fixture"


def test_default_policy_rejects_unidentified_solver_result():
    statement = FormalStatement("smtlib2", "VALIDITY", SMT_SOURCE)
    request = FormalVerificationRequest(statement, "formal.smt", "0.1.0", "obl")
    unidentified = FormalVerificationResult(
        request.request_id,
        request.fingerprint,
        statement.fingerprint,
        "PROVED",
        SolverIdentity("z3"),
        "unsat",
        1,
    )
    aggregate = aggregate_formal_results(request.policy, [unidentified])
    assert aggregate["status"] == "INCONCLUSIVE"
    assert aggregate["reason"] == "solver_identity_required"


def test_multi_solver_policy_is_agreement_not_majority_voting_and_updates_v37_only_after_policy():
    engine = AASMEngine(ProblemSpec("multi solver"))
    artifact, statement = claim_fixture(engine)
    engine.install_default_formal_capability_contracts(authority_id="policy", authority_class="POLICY")
    install_provider(engine, "z3")
    install_provider(engine, "cvc5")
    requested = engine.request_formal_verification(
        statement["formal_statement_id"],
        "formal.smt",
        requester_id="agent-v39",
        linked_artifact_id=artifact.artifact_id,
        required_providers=["z3", "cvc5"],
        policy=FormalVerificationPolicy(required_independent_results=2),
    )
    request = requested["request"]

    z3_lease = engine.claim_next_task("worker-z3", lease_seconds=60)
    first = engine.commit_formal_verification_result(make_result(request, "z3"), lease_id=z3_lease["lease_id"])
    assert first["aggregate"]["status"] == "INCONCLUSIVE"
    assert engine.calculus_report()["obligations"][request["obligation_id"]]["status"] == "VERIFYING"
    assert engine.reasoning_report(artifact.artifact_id)["state"] == "VERIFICATION_REQUESTED"

    cvc5_lease = engine.claim_next_task("worker-cvc5", lease_seconds=60)
    second = engine.commit_formal_verification_result(make_result(request, "cvc5"), lease_id=cvc5_lease["lease_id"])
    assert second["aggregate"]["status"] == "PROVED"
    assert second["aggregate"]["verification_strength"] == "MULTI_SOLVER_AGREEMENT"
    assert second["aggregate"]["solver_voting"] == "NOT_USED"
    assert engine.calculus_report()["obligations"][request["obligation_id"]]["status"] == "VERIFIED"
    assert engine.reasoning_report(artifact.artifact_id)["state"] == "VERIFIED"


def test_solver_disagreement_is_inconclusive_not_voted():
    statement = FormalStatement("smtlib2", "VALIDITY", SMT_SOURCE)
    policy = FormalVerificationPolicy(required_independent_results=2)
    request = FormalVerificationRequest(statement, "formal.smt", "0.1.0", "obl", required_providers=("z3", "cvc5"), policy=policy)
    z3 = make_result(request.to_dict(), "z3", "PROVED")
    cvc5 = make_result(request.to_dict(), "cvc5", "COUNTERMODEL")
    aggregate = aggregate_formal_results(policy, [z3, cvc5])
    assert aggregate["status"] == "INCONCLUSIVE"
    assert aggregate["reason"] == "solver_disagreement"


def test_formal_result_requires_existing_lease_and_admitted_provider():
    engine = AASMEngine(ProblemSpec("formal lease"))
    artifact, statement = claim_fixture(engine)
    engine.install_default_formal_capability_contracts(authority_id="policy", authority_class="POLICY")
    install_provider(engine, "z3")
    requested = engine.request_formal_verification(statement["formal_statement_id"], "formal.smt", requester_id="agent-v39", linked_artifact_id=artifact.artifact_id, required_providers=["z3"])
    result = make_result(requested["request"], "z3")
    with pytest.raises(KeyError):
        engine.commit_formal_verification_result(result, lease_id="missing-lease")


def test_provider_cannot_forge_kernel_strength_or_canonical_solver_semantics():
    engine = AASMEngine(ProblemSpec("formal semantic hardening"))
    artifact, statement = claim_fixture(engine)
    engine.install_default_formal_capability_contracts(authority_id="policy", authority_class="POLICY")
    install_provider(engine, "z3")
    requested = engine.request_formal_verification(statement["formal_statement_id"], "formal.smt", requester_id="agent-v39", linked_artifact_id=artifact.artifact_id, required_providers=["z3"])
    request = requested["request"]
    lease = engine.claim_next_task("worker-z3", lease_seconds=60)
    forged_strength = FormalVerificationResult(
        request["request_id"], request["fingerprint"], request["formal_statement"]["fingerprint"],
        "PROVED", SolverIdentity("z3", version="fixture-1", container_digest="sha256:z3-fixture"),
        "unsat", 1, verification_strength="TRUSTED_KERNEL",
    )
    with pytest.raises(ValueError, match="TRUSTED_KERNEL"):
        engine.commit_formal_verification_result(forged_strength, lease_id=lease["lease_id"])
    forged_status = FormalVerificationResult(
        request["request_id"], request["fingerprint"], request["formal_statement"]["fingerprint"],
        "PROVED", SolverIdentity("z3", version="fixture-1", container_digest="sha256:z3-fixture"),
        "sat", 1, verification_strength="SOLVER_VERDICT",
    )
    with pytest.raises(ValueError, match="canonical status mismatch"):
        engine.commit_formal_verification_result(forged_status, lease_id=lease["lease_id"])
    assert next(row for row in engine.list_leases() if row["lease_id"] == lease["lease_id"])["status"] == "ACTIVE"


def test_completed_lease_only_allows_exact_idempotent_result_replay():
    engine = AASMEngine(ProblemSpec("completed lease replay"))
    artifact, statement = claim_fixture(engine)
    engine.install_default_formal_capability_contracts(authority_id="policy", authority_class="POLICY")
    install_provider(engine, "z3")
    requested = engine.request_formal_verification(statement["formal_statement_id"], "formal.smt", requester_id="agent-v39", linked_artifact_id=artifact.artifact_id, required_providers=["z3"])
    request = requested["request"]
    lease = engine.claim_next_task("worker-z3", lease_seconds=60)
    first_result = make_result(request, "z3", "PROVED")
    first = engine.commit_formal_verification_result(first_result, lease_id=lease["lease_id"])
    replay = engine.commit_formal_verification_result(first_result, lease_id=lease["lease_id"])
    assert replay["already_committed"] is True
    assert replay["result_evidence_id"] == first["result_evidence_id"]
    with pytest.raises(ValueError, match="completed formal lease cannot commit a new result"):
        engine.commit_formal_verification_result(make_result(request, "z3", "COUNTERMODEL"), lease_id=lease["lease_id"])


def test_sqlite_restart_preserves_formal_request_result_and_verified_epistemic_state(tmp_path: Path):
    path = tmp_path / "v39.db"
    store = SQLiteStore(str(path))
    engine = AASMEngine(ProblemSpec("formal restart"), store=store)
    machine_id = engine.snapshot.machine_id
    artifact, statement = claim_fixture(engine)
    engine.install_default_formal_capability_contracts(authority_id="policy", authority_class="POLICY")
    install_provider(engine, "z3")
    requested = engine.request_formal_verification(statement["formal_statement_id"], "formal.smt", requester_id="agent-v39", linked_artifact_id=artifact.artifact_id, required_providers=["z3"])
    lease = engine.claim_next_task("worker-z3", lease_seconds=60)
    committed = engine.commit_formal_verification_result(make_result(requested["request"], "z3"), lease_id=lease["lease_id"])
    assert committed["aggregate"]["status"] == "PROVED"
    store.close()

    resumed_store = SQLiteStore(str(path))
    resumed = AASMEngine.resume(machine_id, resumed_store)
    assert resumed.formal_verification_report(requested["request"]["request_id"])["aggregate"]["status"] == "PROVED"
    assert resumed.reasoning_report(artifact.artifact_id)["state"] == "VERIFIED"
    assert resumed.replay().canonical_hash() == resumed.snapshot.canonical_hash()
    resumed_store.close()


def test_v39_conformance_and_cli_are_visible():
    report = run_typed_capability_conformance()
    assert report["status"] == "PASS", report
    assert all(report["checks"].values())
    help_text = build_parser().format_help()
    for name in (
        "typed-protocol-contract", "capability-abi-contract", "formal-verification-contract",
        "typed-capability-conformance", "typed-pattern-add", "typed-transition-propose",
        "typed-transition-authorize", "capability-add", "capability-provider-add",
        "formal-blueprint", "formal-default-contracts", "formal-provider-runtime",
        "formalize", "formal-request", "formal-report", "formal-result",
    ):
        assert name in help_text
