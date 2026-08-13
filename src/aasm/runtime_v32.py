from __future__ import annotations

from copy import deepcopy
import json
from typing import Any, Sequence

from .runtime_v31 import AASMEngine as V31Engine, default_profile_registry
from .trace_conformance import project_trace, semantic_trace_check, build_trace_corpus, export_provenance, verify_provenance_export, create_selective_provenance_export
from .workers import LeaseStatus
from .evidence import EvidenceRecord
from ._runtime_v37_reasoning import ReasoningRuntimeMixin
from ._runtime_v38_dependencies import SemanticDependencyRuntimeMixin
from .semantic_result import DomainPackage, ProblemDefinition, ProblemModel, ProblemInstance, SEMANTIC_PROBLEM_CONTRACT_ID, canonical_semantic_json, semantic_problem_contract, semantic_problem_document, semantic_problem_from_document, validate_problem_instance


class AASMEngine(SemanticDependencyRuntimeMixin, ReasoningRuntimeMixin, V31Engine):
    """v0.38 runtime: semantic dependency and truth maintenance over one event/reducer path."""

    def _finish_lease(self, lease_id: str, status: str, *, result=None, error=None, at_time=None, reason="lease finished"):
        from .model import now
        ts = now() if at_time is None else float(at_time)
        lease = next((row for row in self.snapshot.resources.get("leases", []) if row.get("lease_id") == lease_id), None)
        if lease is None:
            raise KeyError(lease_id)
        if status in {LeaseStatus.COMPLETED.value, LeaseStatus.FAILED.value}:
            if lease.get("status") != LeaseStatus.ACTIVE.value:
                raise ValueError(f"Lease {lease_id} cannot accept a worker result from status {lease.get('status')}")
            if float(lease.get("expires_at", 0)) <= ts:
                super()._finish_lease(lease_id, LeaseStatus.EXPIRED.value, at_time=ts, reason="stale worker result arrived after lease expiry")
                raise ValueError(f"Lease {lease_id} expired before worker result completion")
            newer = [row for row in self.snapshot.resources.get("leases", []) if row.get("task_id") == lease.get("task_id") and int(row.get("attempt", 0)) > int(lease.get("attempt", 0)) and row.get("status") == LeaseStatus.ACTIVE.value]
            if newer:
                raise ValueError(f"Lease {lease_id} is stale; task {lease.get('task_id')} is owned by newer attempt(s) {sorted(row.get('lease_id') for row in newer)}")
        return super()._finish_lease(lease_id, status, result=deepcopy(result), error=error, at_time=ts, reason=reason)

    def trace_projection(self) -> dict[str, Any]: return project_trace(self.events)
    def semantic_trace_report(self) -> dict[str, Any]: return semantic_trace_check(self.events)
    def provenance_export(self, destination: str, *, key: bytes | str, signer_id: str = "local") -> dict[str, Any]: return export_provenance(self, destination, key=key, signer_id=signer_id)
    def provenance_verify(self, source: str, *, key: bytes | str, signer_id: str | None = None) -> dict[str, Any]: return verify_provenance_export(source, key=key, signer_id=signer_id)
    def provenance_select(self, source: str, destination: str, names: Sequence[str], *, key: bytes | str, signer_id: str = "local") -> dict[str, Any]: return create_selective_provenance_export(source, destination, names, key=key, signer_id=signer_id)

    def admit_semantic_problem(self, domain: DomainPackage, definition: ProblemDefinition, model: ProblemModel, instance: ProblemInstance, *, reason: str = "semantic problem admitted") -> dict[str, Any]:
        report = validate_problem_instance(domain, definition, model, instance)
        if not report["valid"]: raise ValueError(f"semantic problem rejected: {report['errors']}")
        current = self.semantic_problem_report()
        if current.get("configured"):
            current_instance = current["problem_instance"]
            if current_instance.get("instance_id") == instance.instance_id and current_instance.get("fingerprint") == instance.fingerprint: return current
            raise ValueError("a semantic problem is already bound; use an explicit future migration path")
        document = semantic_problem_document(domain, definition, model, instance)
        evidence = EvidenceRecord(kind="semantic_problem", statement=canonical_semantic_json(document), source=SEMANTIC_PROBLEM_CONTRACT_ID, metadata={"semantic_contract_id": SEMANTIC_PROBLEM_CONTRACT_ID, "semantic_fingerprint": instance.fingerprint, "domain_package_id": domain.package_id, "domain_package_fingerprint": domain.fingerprint, "instance_id": instance.instance_id, "scope_id": "root"})
        stored = self.add_evidence(evidence, reason=reason); out = self.semantic_problem_report(); out["admission_evidence_id"] = stored.evidence_id; return out

    def semantic_problem_report(self) -> dict[str, Any]:
        records = self.snapshot.evidence.get("records", []) if isinstance(self.snapshot.evidence, dict) else []
        selected = [row for row in records if row.get("kind") == "semantic_problem" and row.get("status") == "active" and (row.get("metadata") or {}).get("semantic_contract_id") == SEMANTIC_PROBLEM_CONTRACT_ID]
        if not selected: return {"contract": semantic_problem_contract(), "configured": False}
        row = selected[-1]; document = json.loads(row["statement"]); domain, definition, model, instance = semantic_problem_from_document(document); report = validate_problem_instance(domain, definition, model, instance)
        return {"contract": semantic_problem_contract(), "configured": True, "evidence_id": row["evidence_id"], "valid": report["valid"], "validation": report, "domain_package": domain.to_dict(), "problem_definition": definition.to_dict(), "problem_model": model.to_dict(), "problem_instance": instance.to_dict()}

    def semantic_domain_report(self) -> dict[str, Any]:
        report = self.semantic_problem_report(); return {"contract": report["contract"], "configured": report.get("configured", False), "domain_package": report.get("domain_package"), "problem_model": report.get("problem_model")}

    def semantic_compiler_report(self) -> dict[str, Any]:
        from .domain_adapters import semantic_compiler_contract
        return semantic_compiler_contract()

    def compile_and_admit_semantic(self, source: Any, *, environment=None, compiler=None, cache=None, policy=None, source_name: str | None = None) -> dict[str, Any]:
        from .domain_adapters import compile_and_admit
        return compile_and_admit(self, source, environment=environment, compiler=compiler, cache=cache, policy=policy, source_name=source_name)

    def inspect_machine(self, surface: str = "summary") -> Any:
        if surface == "trace": return self.trace_projection()
        if surface == "trace-semantic": return self.semantic_trace_report()
        if surface == "provenance": return {"contract": "aasm.provenance.v1", "exportable": True, "source_trace_sha256": self.trace_projection()["source_trace_sha256"]}
        if surface in {"problem", "semantic-problem"}: return self.semantic_problem_report()
        if surface in {"domain", "semantic-domain"}: return self.semantic_domain_report()
        if surface in {"compiler", "semantic-compiler"}: return self.semantic_compiler_report()
        if surface in {"reasoning", "reasoning-artifacts", "epistemic"}: return self.reasoning_report()
        if surface in {"reasoning-contract", "epistemic-contract"}: return self.reasoning_contract_report()
        if surface in {"dependencies", "semantic-dependencies"}: return self.semantic_dependency_graph()
        if surface == "truth-maintenance": return self.truth_maintenance_report()
        if surface == "reactive-obligations": return self.reactive_obligation_report()
        if surface == "semantic-memory-signals": return self.semantic_memory_projection_signals()
        return super().inspect_machine(surface)


__all__ = ["AASMEngine", "default_profile_registry", "build_trace_corpus"]
