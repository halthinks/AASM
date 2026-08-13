from __future__ import annotations

from .semantic_result import semantic_fingerprint
from .typed_protocol import TypedEventSchema, ScopedLegalTransition, PatternMachine
from .formal_models import FormalStatement, FormalVerificationPolicy, FormalVerificationRequest, typed_protocol_contract, capability_abi_contract, formal_verification_contract, parse_vampire_status
from .formal_workers import ProcessResult, ExecutableFormalWorker, aggregate_formal_results


def run_typed_capability_conformance() -> dict:
    checks: dict[str, bool] = {}
    schema = TypedEventSchema("READY", {"type": "object", "required": ["ok"], "properties": {"ok": {"type": "boolean"}}, "additionalProperties": False}, guards=("guard.ready",))
    transition = ScopedLegalTransition("INIT", "READY", "DONE", "accept_ready")
    pattern = PatternMachine("fixture", "1.0.0", "root", ("DONE", "INIT"), "INIT", (transition,), (schema,))
    schema.validate({"ok": True}); checks["typed_payload_validates"] = True
    try:
        schema.validate({"ok": "yes"}); checks["typed_payload_rejects_invalid"] = False
    except ValueError:
        checks["typed_payload_rejects_invalid"] = True
    checks["pattern_is_deterministic"] = pattern.transition_for("INIT", "READY").to_state == "DONE"

    statement = FormalStatement("smtlib2", "VALIDITY", "(set-logic QF_UF)\n(assert false)\n(check-sat)")
    policy = FormalVerificationPolicy(required_independent_results=2)
    request = FormalVerificationRequest(statement, "formal.smt", "0.1.0", "obl-fixture", required_providers=("z3", "cvc5"), policy=policy)
    def runner(argv, stdin_text, timeout_ms, mode): return ProcessResult(0, "unsat\n", "", 3)
    z3 = ExecutableFormalWorker("z3", "z3", version="fixture", container_digest="sha256:fixture-z3", runner=runner).run(request)
    cvc5 = ExecutableFormalWorker("cvc5", "cvc5", version="fixture", container_digest="sha256:fixture-cvc5", runner=runner).run(request)
    checks["smt_validity_unsat_means_proved"] = z3.canonical_status == "PROVED"
    aggregate = aggregate_formal_results(policy, [z3, cvc5])
    checks["multi_solver_agreement_not_voting"] = aggregate["status"] == "PROVED" and aggregate["verification_strength"] == "MULTI_SOLVER_AGREEMENT" and aggregate["solver_voting"] == "NOT_USED"
    checks["vampire_szs_parsed"] = parse_vampire_status("% SZS status Theorem for X") == "Theorem"
    checks["formalization_fingerprinted"] = bool(statement.fingerprint and statement.source_fingerprint)
    checks["solver_is_evidence_only"] = formal_verification_contract()["solver_authority"] == "EVIDENCE_ONLY"
    status = "PASS" if all(checks.values()) else "FAIL"
    report = {"contract": typed_protocol_contract(), "capability_abi": capability_abi_contract(), "formal_verification": formal_verification_contract(), "checks": checks, "status": status}
    report["report_fingerprint"] = semantic_fingerprint(report)
    return report


__all__ = ["run_typed_capability_conformance"]
