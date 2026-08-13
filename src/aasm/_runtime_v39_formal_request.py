from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence

from .calculus import ObligationRecord
from .evidence import EvidenceRecord
from .resources import TaskDemand
from .semantic_result import semantic_fingerprint
from .typed_capabilities import FORMAL_STATEMENT_CONTRACT_ID, FORMAL_VERIFICATION_CONTRACT_ID, CapabilityContract, CapabilityProvider, FormalStatement, FormalVerificationPolicy, FormalVerificationRequest, FormalVerificationResult, aggregate_formal_results, formal_verification_contract, pattern_document
from ._runtime_v39_typed import _records, _document


class FormalRequestRuntimeMixin:
    def formal_statement_report(self, formal_statement_id: str | None = None) -> dict[str, Any]:
        statements = {}
        for row in _records(self.snapshot, "formal_statement"):
            statement = FormalStatement.from_dict(_document(row)); statements[statement.formal_statement_id] = {"formal_statement": statement.to_dict(), "evidence_id": row["evidence_id"]}
        if formal_statement_id is not None:
            if formal_statement_id not in statements: raise KeyError(formal_statement_id)
            return {"contract": formal_verification_contract(), **deepcopy(statements[formal_statement_id])}
        return {"contract": formal_verification_contract(), "statements": statements}

    def propose_formal_statement(self, statement: FormalStatement | Mapping[str, Any], *, reason: str = "formalization proposed") -> dict[str, Any]:
        statement = statement if isinstance(statement, FormalStatement) else FormalStatement.from_dict(statement); artifacts = self.reasoning_report().get("artifacts", {})
        missing = sorted(set(statement.source_artifact_ids) - set(artifacts))
        if missing: raise KeyError(f"formalization references unknown reasoning artifacts: {missing}")
        if statement.source_artifact_ids:
            expected = {aid: str(artifacts[aid]["artifact"]["fingerprint"]) for aid in statement.source_artifact_ids}
            if statement.source_artifact_fingerprints != expected: raise ValueError("formalization source artifact fingerprints do not match current exact artifacts")
        existing = self.formal_statement_report()["statements"]
        if statement.formal_statement_id in existing:
            prior = FormalStatement.from_dict(existing[statement.formal_statement_id]["formal_statement"])
            if prior.fingerprint != statement.fingerprint: raise ValueError(f"formal statement ID collision: {statement.formal_statement_id}")
            return {"contract": formal_verification_contract(), **existing[statement.formal_statement_id], "already_recorded": True}
        derived = [artifacts[aid]["proposal_evidence_id"] for aid in statement.source_artifact_ids]
        stored = self.add_evidence(EvidenceRecord(kind="formal_statement", statement=pattern_document(statement), source=FORMAL_STATEMENT_CONTRACT_ID, derived_from=sorted(set(derived)), metadata={"formal_record_type": "STATEMENT", "formal_statement_contract_id": FORMAL_STATEMENT_CONTRACT_ID, "formal_statement_id": statement.formal_statement_id, "formal_statement_fingerprint": statement.fingerprint, "source_fingerprint": statement.source_fingerprint, "compiler_id": statement.compiler_id, "compiler_version": statement.compiler_version, "logic": statement.logic, "query_mode": statement.query_mode, "formalization_authority": "PROPOSAL_ONLY"}), reason=reason)
        return {"contract": formal_verification_contract(), "formal_statement": statement.to_dict(), "evidence_id": stored.evidence_id, "already_recorded": False}

    def formalize_artifact(self, artifact_id: str, *, logic: str, query_mode: str, canonical_source: str, declarations: Sequence[str] = (), assumptions: Sequence[str] = (), conjecture: str = "", compiler_id: str = "explicit", compiler_version: str = "1", environment_fingerprint: str = "", metadata: Mapping[str, Any] | None = None, reason: str = "reasoning artifact formalized") -> dict[str, Any]:
        entry = self.reasoning_report(artifact_id)
        statement = FormalStatement(logic=logic, query_mode=query_mode, canonical_source=canonical_source, source_artifact_ids=(artifact_id,), source_artifact_fingerprints={artifact_id: str(entry["artifact"]["fingerprint"])}, declarations=tuple(declarations), assumptions=tuple(assumptions), conjecture=conjecture, compiler_id=compiler_id, compiler_version=compiler_version, environment_fingerprint=environment_fingerprint, metadata=deepcopy(dict(metadata or {})))
        return self.propose_formal_statement(statement, reason=reason)

    def formal_verification_report(self, request_id: str | None = None) -> dict[str, Any]:
        requests, results = {}, {}
        for row in _records(self.snapshot, "formal_verification_request"):
            request = FormalVerificationRequest.from_dict(_document(row)); requests[request.request_id] = {"request": request.to_dict(), "evidence_id": row["evidence_id"]}
        for row in _records(self.snapshot, "formal_verification_result"):
            result = FormalVerificationResult.from_dict(_document(row)); results.setdefault(result.request_id, []).append({"result": result.to_dict(), "evidence_id": row["evidence_id"]})
        for rows in results.values(): rows.sort(key=lambda item: item["result"]["result_id"])
        if request_id is not None:
            if request_id not in requests: raise KeyError(request_id)
            request = FormalVerificationRequest.from_dict(requests[request_id]["request"]); parsed = [FormalVerificationResult.from_dict(item["result"]) for item in results.get(request_id, [])]
            return {"contract": formal_verification_contract(), **deepcopy(requests[request_id]), "results": deepcopy(results.get(request_id, [])), "aggregate": aggregate_formal_results(request.policy, parsed)}
        return {"contract": formal_verification_contract(), "requests": requests, "results": results}

    def request_formal_verification(self, formal_statement_id: str, capability_id: str, *, requester_id: str, linked_artifact_id: str | None = None, capability_version: str | None = None, timeout_ms: int = 30_000, required_providers: Sequence[str] = (), policy: FormalVerificationPolicy | Mapping[str, Any] | None = None, priority: int = 0, reason: str = "formal verification requested") -> dict[str, Any]:
        statement_row = self.formal_statement_report(formal_statement_id); statement = FormalStatement.from_dict(statement_row["formal_statement"]); capability = CapabilityContract.from_dict(self.capability_report(capability_id)["capability"]["contract"])
        if capability.capability_type != "VERIFIER": raise ValueError("formal verification requires a VERIFIER capability")
        if capability_version is not None and capability.version != capability_version: raise ValueError("requested capability version does not match admitted contract")
        if statement.logic not in capability.supported_logics: raise ValueError("formal statement logic is unsupported by selected capability")
        if statement.query_mode not in capability.query_modes: raise ValueError("formal query mode is unsupported by selected capability")
        if linked_artifact_id is not None and linked_artifact_id not in statement.source_artifact_ids: raise ValueError("linked reasoning artifact must be one of the formalization source artifacts")
        provider_ids = tuple(sorted(set(map(str, required_providers)))); known_providers = self.capability_report()["providers"]
        for provider_id in provider_ids:
            if provider_id not in known_providers: raise KeyError(f"unknown required formal provider: {provider_id}")
            provider = CapabilityProvider.from_dict(known_providers[provider_id]["provider"])
            if provider.capability_id != capability.capability_id or provider.capability_version != capability.version: raise ValueError(f"required provider {provider_id} is not bound to selected capability")
            if statement.logic not in provider.supported_logics or statement.query_mode not in provider.query_modes: raise ValueError(f"required provider {provider_id} cannot execute the formal request")
        policy_obj = policy if isinstance(policy, FormalVerificationPolicy) else FormalVerificationPolicy(**deepcopy(dict(policy or {})))
        if policy_obj.required_independent_results > 1 and len(provider_ids) < policy_obj.required_independent_results: raise ValueError("multi-result formal policy requires explicit independent required_providers")
        obligation_id = "formal-obligation-" + semantic_fingerprint({"formal_statement_id": formal_statement_id, "capability_id": capability.capability_id, "capability_version": capability.version, "linked_artifact_id": linked_artifact_id, "providers": list(provider_ids), "policy": policy_obj.to_dict()})[:20]
        request = FormalVerificationRequest(formal_statement=statement, capability_id=capability.capability_id, capability_version=capability.version, obligation_id=obligation_id, timeout_ms=timeout_ms, required_providers=provider_ids, policy=policy_obj, linked_artifact_id=linked_artifact_id, metadata={"requester_id": requester_id})
        existing_request = self.formal_verification_report()["requests"].get(request.request_id)
        if obligation_id not in self.calculus_report()["obligations"]:
            source_scope = {"scope_id": "root"}
            if linked_artifact_id: source_scope = deepcopy(self.reasoning_report(linked_artifact_id)["artifact"].get("scope") or source_scope)
            self.register_obligation(ObligationRecord(obligation_id=obligation_id, statement=f"formal verification of {formal_statement_id}", status="AVAILABLE", required_evidence_types=["formal_verification_result"], artifact_ids=[linked_artifact_id] if linked_artifact_id else list(statement.source_artifact_ids), scope=source_scope), reason="formal verification obligation registered")
        if linked_artifact_id:
            entry = self.reasoning_report(linked_artifact_id); already_requested = any(request.verifier_id in row.get("verifier_ids", []) for row in entry.get("verification_requests", []))
            if not already_requested: self.request_verification(linked_artifact_id, verifier_ids=[request.verifier_id], requester_id=requester_id, authority_class="PROPOSER", reason="formal verifier requested for reasoning artifact")
        if existing_request is None:
            stored = self.add_evidence(EvidenceRecord(kind="formal_verification_request", statement=pattern_document(request), source=FORMAL_VERIFICATION_CONTRACT_ID, derived_from=[statement_row["evidence_id"]], metadata={"formal_record_type": "REQUEST", "formal_verification_contract_id": FORMAL_VERIFICATION_CONTRACT_ID, "request_id": request.request_id, "request_fingerprint": request.fingerprint, "formal_statement_id": formal_statement_id, "formal_statement_fingerprint": statement.fingerprint, "capability_id": capability.capability_id, "capability_version": capability.version, "obligation_id": obligation_id, "verifier_id": request.verifier_id}), reason=reason); request_evidence_id = stored.evidence_id
        else:
            prior = FormalVerificationRequest.from_dict(existing_request["request"])
            if prior.fingerprint != request.fingerprint: raise ValueError(f"formal request ID collision: {request.request_id}")
            request_evidence_id = existing_request["evidence_id"]
        resources = deepcopy(self.snapshot.resources); queue = resources.setdefault("tasks", []); tasks = []
        for provider_id in provider_ids or (None,):
            task_id = request.request_id if provider_id is None else f"{request.request_id}:{provider_id}"; required = [request.capability_token]
            if provider_id is not None: required.append(CapabilityProvider.from_dict(self.capability_report()["providers"][provider_id]["provider"]).provider_token)
            task = TaskDemand(task_id=task_id, required_capabilities=required, demand=1.0, priority=priority, allowed_kinds=["formal-verifier"], metadata={"formal_request_id": request.request_id, "formal_request_fingerprint": request.fingerprint, "formal_statement_id": formal_statement_id, "formal_statement_fingerprint": statement.fingerprint, "obligation_id": obligation_id, "required_provider": provider_id})
            if not any(row.get("task_id") == task.task_id for row in queue): queue.append(deepcopy(task.__dict__))
            tasks.append(deepcopy(task.__dict__))
        self.patch_snapshot({"resources": resources}, "formal verification tasks queued")
        return {"contract": formal_verification_contract(), "request": request.to_dict(), "request_evidence_id": request_evidence_id, "obligation": deepcopy(self.calculus_report()["obligations"][obligation_id]), "tasks": tasks, "aggregate": {"status": "INCONCLUSIVE", "reason": "no_results", "verification_strength": None}}

    @staticmethod
    def _allowed_formal_task_ids(request: FormalVerificationRequest) -> set[str]:
        return {f"{request.request_id}:{provider_id}" for provider_id in request.required_providers} if request.required_providers else {request.request_id}

    def _validate_formal_lease(self, lease_id: str, request: FormalVerificationRequest) -> dict[str, Any]:
        lease = next((deepcopy(row) for row in self.list_leases() if row.get("lease_id") == lease_id), None)
        if lease is None: raise KeyError(lease_id)
        if lease.get("task_id") not in self._allowed_formal_task_ids(request): raise ValueError("formal result lease does not belong to request")
        if lease.get("status") == "COMPLETED": return lease
        if lease.get("status") != "ACTIVE": raise ValueError(f"formal result lease is not ACTIVE: {lease.get('status')}")
        from .model import now
        if float(lease.get("expires_at", 0)) <= now(): raise ValueError("formal result lease expired before result commit")
        newer = [row for row in self.list_leases() if row.get("task_id") == lease.get("task_id") and int(row.get("attempt", 0)) > int(lease.get("attempt", 0)) and row.get("status") == "ACTIVE"]
        if newer: raise ValueError("formal result lease was superseded by a newer attempt")
        return lease

    def _formal_result_rows(self, request_id: str): return self.formal_verification_report(request_id)["results"]
