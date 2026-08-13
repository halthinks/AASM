from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import hashlib
from typing import Any, Mapping, Sequence

from .evidence import EvidenceRecord
from .reasoning import Counterexample, Invariant, Lemma, ReasoningProducer
from .typed_capabilities import (
    FORMAL_VERIFICATION_CONTRACT_ID,
    CapabilityProvider,
    FormalVerificationRequest,
    FormalVerificationResult,
    aggregate_formal_results,
    canonicalize_solver_status,
    formal_verification_contract,
    pattern_document,
)

_CONCLUSIVE = {"PROVED", "COUNTERMODEL", "DISPROVED", "SAT", "UNSAT"}


class FormalResultRuntimeMixin:
    def _advance_formal_obligation(
        self,
        request: FormalVerificationRequest,
        aggregate: Mapping[str, Any],
        result_evidence_ids: Sequence[str],
    ) -> None:
        obligation = self.calculus_report()["obligations"][request.obligation_id]
        status = obligation.get("status")
        if status == "AVAILABLE":
            self.enable_obligation(request.obligation_id, reason="formal verification obligation enabled")
            status = "ENABLED"
        if status == "ENABLED":
            self.set_obligation_status(request.obligation_id, "IN_PROGRESS", reason="formal verification worker started")
            status = "IN_PROGRESS"
        if status == "IN_PROGRESS":
            self.set_obligation_status(request.obligation_id, "VERIFYING", reason="formal verification results under policy evaluation")
            status = "VERIFYING"
        if aggregate.get("status") in _CONCLUSIVE:
            if status == "BLOCKED":
                self.enable_obligation(request.obligation_id, reason="formal verification obligation reopened after conclusive retry")
                self.set_obligation_status(request.obligation_id, "IN_PROGRESS", reason="formal verification retry accepted")
                self.set_obligation_status(request.obligation_id, "VERIFYING", reason="formal verification retry under policy evaluation")
                status = "VERIFYING"
            if status == "VERIFYING":
                self.set_obligation_status(
                    request.obligation_id,
                    "VERIFIED",
                    evidence_ids=list(result_evidence_ids),
                    reason="formal verification policy satisfied",
                )
        else:
            enough_results = len(self._formal_result_rows(request.request_id)) >= max(
                1,
                len(request.required_providers) if request.required_providers else request.policy.required_independent_results,
            )
            if status == "VERIFYING" and enough_results:
                self.set_obligation_status(
                    request.obligation_id,
                    "BLOCKED",
                    reason="formal verification policy remained inconclusive",
                )

    def _apply_formal_epistemic_result(
        self,
        request: FormalVerificationRequest,
        aggregate: Mapping[str, Any],
        result_evidence_ids: Sequence[str],
    ) -> dict[str, Any]:
        status = str(aggregate.get("status"))
        if status not in {"PROVED", "COUNTERMODEL", "DISPROVED"}:
            return {"epistemic_action": "NONE", "artifact_id": None}
        if request.linked_artifact_id:
            entry = self.reasoning_report(request.linked_artifact_id)
            prior = [row for row in entry.get("verifications", []) if row.get("actor_id") == request.verifier_id]
            if not prior:
                verdict = "PASS" if status == "PROVED" else "FAIL"
                self.record_verification(
                    request.linked_artifact_id,
                    verifier_id=request.verifier_id,
                    verdict=verdict,
                    evidence_ids=list(result_evidence_ids),
                    authority_class="VERIFIER",
                    reason="formal verification policy result recorded",
                    metadata={
                        "formal_request_id": request.request_id,
                        "formal_status": status,
                        "verification_strength": aggregate.get("verification_strength"),
                        "solver_voting": "NOT_USED",
                    },
                )
            if status in {"COUNTERMODEL", "DISPROVED"}:
                source = self.reasoning_report(request.linked_artifact_id)["artifact"]
                artifact = Counterexample(
                    f"Formal counterexample to: {source['statement']}",
                    ReasoningProducer(request.verifier_id, "VERIFIER"),
                    premise_artifact_ids=(request.linked_artifact_id,),
                    evidence_ids=tuple(result_evidence_ids),
                    scope=deepcopy(source.get("scope") or {}),
                    metadata={"formal_request_id": request.request_id, "verification_strength": aggregate.get("verification_strength")},
                )
                current = self.reasoning_report().get("artifacts", {})
                if artifact.artifact_id not in current:
                    self.propose_artifact(artifact, reason="formal counterexample proposed")
                return {"epistemic_action": "COUNTEREXAMPLE_PROPOSED", "artifact_id": artifact.artifact_id}
            return {"epistemic_action": "VERIFICATION_RECORDED", "artifact_id": request.linked_artifact_id}

        if status == "PROVED":
            producer = ReasoningProducer(request.verifier_id, "VERIFIER")
            kwargs = {
                "evidence_ids": tuple(result_evidence_ids),
                "premise_artifact_ids": tuple(request.formal_statement.source_artifact_ids),
                "metadata": {
                    "formal_request_id": request.request_id,
                    "formal_statement_id": request.formal_statement.formal_statement_id,
                    "verification_strength": aggregate.get("verification_strength"),
                },
            }
            statement_text = request.formal_statement.conjecture or request.formal_statement.canonical_source
            artifact = Invariant(statement_text, producer, **kwargs) if request.formal_statement.query_mode == "INVARIANT" else Lemma(statement_text, producer, **kwargs)
        else:
            artifact = Counterexample(
                f"Countermodel for formal statement {request.formal_statement.formal_statement_id}",
                ReasoningProducer(request.verifier_id, "VERIFIER"),
                evidence_ids=tuple(result_evidence_ids),
                metadata={
                    "formal_request_id": request.request_id,
                    "formal_statement_id": request.formal_statement.formal_statement_id,
                    "verification_strength": aggregate.get("verification_strength"),
                },
            )
        current = self.reasoning_report().get("artifacts", {})
        if artifact.artifact_id not in current:
            self.propose_artifact(artifact, reason="formal reasoning artifact proposed")
        return {"epistemic_action": "ARTIFACT_PROPOSED", "artifact_id": artifact.artifact_id}

    @staticmethod
    def _validate_provider_result_semantics(provider: CapabilityProvider, request: FormalVerificationRequest, result: FormalVerificationResult) -> None:
        if result.verification_strength == "MULTI_SOLVER_AGREEMENT":
            raise ValueError("MULTI_SOLVER_AGREEMENT is an aggregate strength, not an individual provider result")
        if result.verification_strength == "TRUSTED_KERNEL" and provider.capability_id != "formal.proof_kernel":
            raise ValueError("TRUSTED_KERNEL strength requires a formal.proof_kernel provider")
        if (result.certificate_checked or result.verification_strength == "CHECKED_CERTIFICATE") and provider.capability_id != "formal.certificate_checker":
            raise ValueError("certificate-checked strength requires a formal.certificate_checker provider")
        implementation = provider.implementation.strip().lower()
        semantic_solver = "lean4" if implementation in {"lean", "lean4"} else implementation
        raw = result.raw_status.strip().lower()
        if result.canonical_status == "TIMEOUT":
            if raw != "timeout": raise ValueError("formal timeout result requires raw_status=timeout")
            return
        if result.canonical_status == "ERROR":
            return
        if semantic_solver in {"z3", "cvc5", "vampire", "lean4"}:
            returncode = 0
            if semantic_solver == "lean4" and raw not in {"accepted", "ok", "proved"}: returncode = 1
            expected = canonicalize_solver_status(request.formal_statement.query_mode, semantic_solver, result.raw_status, returncode=returncode)
            if expected != result.canonical_status:
                raise ValueError(f"formal result canonical status mismatch: provider semantics require {expected}, found {result.canonical_status}")

    def commit_formal_verification_result(
        self,
        result: FormalVerificationResult | Mapping[str, Any],
        *,
        lease_id: str,
        proof_object: str | None = None,
        raw_output: str | None = None,
        reason: str = "formal verification result committed",
    ) -> dict[str, Any]:
        result = result if isinstance(result, FormalVerificationResult) else FormalVerificationResult.from_dict(result)
        request_row = self.formal_verification_report(result.request_id)
        request = FormalVerificationRequest.from_dict(request_row["request"])
        if result.request_fingerprint != request.fingerprint: raise ValueError("formal result request fingerprint mismatch")
        if result.formal_statement_fingerprint != request.formal_statement.fingerprint: raise ValueError("formal result formalization fingerprint mismatch")
        lease = self._validate_formal_lease(lease_id, request)
        provider_id = result.solver.solver_id
        providers = self.capability_report()["providers"]
        if provider_id not in providers: raise KeyError(f"unadmitted formal provider: {provider_id}")
        provider = CapabilityProvider.from_dict(providers[provider_id]["provider"])
        if provider.capability_id != request.capability_id or provider.capability_version != request.capability_version: raise ValueError("formal result provider does not implement request capability")
        required_provider = None
        if ":" in str(lease.get("task_id", "")): required_provider = str(lease["task_id"]).rsplit(":", 1)[-1]
        if required_provider and required_provider != provider_id: raise ValueError("formal result provider does not match provider-specific leased task")
        if request.required_providers and provider_id not in request.required_providers: raise ValueError("formal result came from provider not required by request")
        expected_version = str(provider.metadata.get("solver_version", "") or "")
        expected_binary = str(provider.metadata.get("binary_sha256", "") or "")
        expected_container = str(provider.metadata.get("container_digest", "") or "")
        if expected_version and result.solver.version != expected_version: raise ValueError("formal result solver version does not match admitted provider")
        if expected_binary and result.solver.binary_sha256 != expected_binary: raise ValueError("formal result binary digest does not match admitted provider")
        if expected_container and result.solver.container_digest != expected_container: raise ValueError("formal result container digest does not match admitted provider")
        self._validate_provider_result_semantics(provider, request, result)

        if proof_object is not None:
            proof_hash = hashlib.sha256(proof_object.encode("utf-8")).hexdigest()
            if result.proof_object_sha256 and result.proof_object_sha256 != proof_hash: raise ValueError("proof object hash does not match formal result")
            result = replace(result, proof_object_sha256=proof_hash)
        if raw_output is not None:
            raw_hash = hashlib.sha256(raw_output.encode("utf-8")).hexdigest()
            if result.raw_output_sha256 and result.raw_output_sha256 != raw_hash: raise ValueError("raw output hash does not match formal result")
            result = replace(result, raw_output_sha256=raw_hash)

        for row in request_row["results"]:
            prior = FormalVerificationResult.from_dict(row["result"])
            if prior.result_id == result.result_id:
                if prior.fingerprint != result.fingerprint: raise ValueError(f"formal result ID collision: {result.result_id}")
                if lease.get("status") == "ACTIVE":
                    from .workers import LeaseStatus
                    self._finish_lease(lease_id, LeaseStatus.COMPLETED.value, result={"formal_result_id": result.result_id, "already_committed": True}, reason="formal worker lease completed after idempotent result replay")
                refreshed = self.formal_verification_report(result.request_id)
                return {"contract": formal_verification_contract(), "result": prior.to_dict(), "result_evidence_id": row["evidence_id"], "aggregate": refreshed["aggregate"], "already_committed": True}
        if lease.get("status") == "COMPLETED":
            raise ValueError("completed formal lease cannot commit a new result")

        derived = [request_row["evidence_id"]]
        proof_evidence_id = None
        raw_evidence_id = None
        if proof_object is not None:
            stored = self.add_evidence(EvidenceRecord(kind="formal_proof_object", statement=proof_object, source=FORMAL_VERIFICATION_CONTRACT_ID, derived_from=[request_row["evidence_id"]], metadata={"formal_record_type": "PROOF_OBJECT", "formal_verification_contract_id": FORMAL_VERIFICATION_CONTRACT_ID, "request_id": request.request_id, "proof_object_sha256": result.proof_object_sha256, "semantic_identity": "SEPARATE_CONTENT_HASH"}), reason="formal proof object recorded")
            proof_evidence_id = stored.evidence_id; derived.append(stored.evidence_id)
        if raw_output is not None:
            stored = self.add_evidence(EvidenceRecord(kind="formal_raw_output", statement=raw_output, source=FORMAL_VERIFICATION_CONTRACT_ID, derived_from=[request_row["evidence_id"]], metadata={"formal_record_type": "RAW_OUTPUT", "formal_verification_contract_id": FORMAL_VERIFICATION_CONTRACT_ID, "request_id": request.request_id, "raw_output_sha256": result.raw_output_sha256, "semantic_identity": "DIAGNOSTIC_ONLY"}), reason="formal raw solver output recorded")
            raw_evidence_id = stored.evidence_id; derived.append(stored.evidence_id)

        stored_result = self.add_evidence(EvidenceRecord(kind="formal_verification_result", statement=pattern_document(result), source=FORMAL_VERIFICATION_CONTRACT_ID, derived_from=sorted(set(derived)), metadata={"formal_record_type": "RESULT", "formal_verification_contract_id": FORMAL_VERIFICATION_CONTRACT_ID, "request_id": request.request_id, "result_id": result.result_id, "result_fingerprint": result.fingerprint, "formal_statement_fingerprint": result.formal_statement_fingerprint, "solver_id": result.solver.solver_id, "solver_fingerprint": result.solver.fingerprint, "canonical_status": result.canonical_status, "verification_strength": result.verification_strength, "evidence_type": "formal_verification_result", "obligation_id": request.obligation_id, "solver_authority": "EVIDENCE_ONLY"}), reason=reason)
        refreshed = self.formal_verification_report(request.request_id)
        result_evidence_ids = [row["evidence_id"] for row in refreshed["results"]]
        aggregate = refreshed["aggregate"]
        self._advance_formal_obligation(request, aggregate, result_evidence_ids)
        epistemic = self._apply_formal_epistemic_result(request, aggregate, result_evidence_ids)

        from .workers import LeaseStatus
        if lease.get("status") == "ACTIVE":
            status = LeaseStatus.FAILED.value if result.canonical_status == "ERROR" else LeaseStatus.COMPLETED.value
            self._finish_lease(lease_id, status, result={"formal_result_id": result.result_id, "request_id": request.request_id, "canonical_status": result.canonical_status} if status == LeaseStatus.COMPLETED.value else None, error=("; ".join(result.diagnostics) or "formal worker error") if status == LeaseStatus.FAILED.value else None, reason="formal worker result accepted")

        return {"contract": formal_verification_contract(), "result": result.to_dict(), "result_evidence_id": stored_result.evidence_id, "proof_evidence_id": proof_evidence_id, "raw_output_evidence_id": raw_evidence_id, "aggregate": aggregate, "epistemic": epistemic, "obligation": deepcopy(self.calculus_report()["obligations"][request.obligation_id]), "already_committed": False}
