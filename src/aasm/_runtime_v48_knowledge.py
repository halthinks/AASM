from __future__ import annotations

from copy import deepcopy
import json
from typing import Any, Mapping, Sequence

from .calculus import DecisionRecord, ObligationRecord
from .cross_run_knowledge import (
    CROSS_RUN_ADMISSION_CONTRACT_ID,
    CROSS_RUN_KNOWLEDGE_CONTRACT_ID,
    CROSS_RUN_PRINCIPAL_MAP_CONTRACT_ID,
    CrossRunAdmissionContext,
    CrossRunKnowledgeBundle,
    CrossRunKnowledgeEnvelope,
    CrossRunKnowledgeSignal,
    CrossRunPrincipalMap,
    cross_run_document,
    cross_run_knowledge_contract,
    validate_cross_run_envelope,
)
from .evidence import EvidenceRecord
from .reuse_model import ReuseCandidate, ReuseRequest
from .semantic_result import canonical_semantic_json, semantic_fingerprint


class CrossRunKnowledgeRuntimeMixin:
    """v0.48 receiving-run admission and cross-run long-term knowledge.

    Foreign source authority is provenance only. This mixin records admitted
    foreign knowledge as Evidence and then delegates semantic/procedural memory
    and execution reuse to the existing v0.40/v0.41 governed pathways.
    """

    def cross_run_knowledge_contract_report(self) -> dict[str, Any]:
        return cross_run_knowledge_contract()

    def _cross_run_now(self) -> float:
        records = self.snapshot.evidence.get("records", [])
        events = getattr(self, "events", [])
        values = [float(row.get("created_at", 0) or 0) for row in records]
        values.extend(float(getattr(row, "ts", 0) or 0) for row in events)
        return max(values or [0.0])

    def _cross_run_export_records(self) -> list[dict[str, Any]]:
        rows = []
        for evidence in self.snapshot.evidence.get("records", []):
            if evidence.get("kind") != "cross_run_knowledge_export":
                continue
            try:
                bundle = CrossRunKnowledgeBundle.from_dict(json.loads(str(evidence.get("statement") or "{}")))
            except Exception:
                continue
            rows.append({"bundle": bundle, "evidence_id": str(evidence.get("evidence_id")), "created_at": float(evidence.get("created_at", 0) or 0)})
        return rows

    def export_cross_run_knowledge(
        self,
        memory_ids: Sequence[str],
        *,
        principal_id: str = "",
        applicability_scope_ids: Sequence[str] = ("root",),
        environment_fingerprint: str = "",
        dependency_fingerprints: Sequence[str] = (),
        freshness_seconds: float | None = None,
        source_run_id: str | None = None,
        record: bool = True,
        metadata: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        run_id = str(source_run_id or self.snapshot.machine_id)
        projection = self.hierarchical_memory_report()
        reasoning = self.reasoning_report().get("artifacts", {})
        envelopes = []
        for memory_id in sorted(set(map(str, memory_ids))):
            row = projection.get("memories", {}).get(memory_id)
            if row is None:
                raise KeyError(memory_id)
            if row.get("status") != "ACTIVE":
                raise ValueError(f"cross-run export requires ACTIVE memory: {memory_id} is {row.get('status')}")
            memory = row["memory"]
            meta = deepcopy(memory.get("metadata") or {})
            privacy_level = str(memory.get("privacy_level") or "AGENT")
            privacy_principal = str(meta.get("privacy_principal_id") or "")
            if privacy_level in {"AGENT", "USER"} and principal_id != privacy_principal:
                raise PermissionError("private cross-run export requires matching privacy principal")
            source_artifacts = tuple(memory.get("semantic_artifact_ids") or ())
            source_fingerprints = {f"MEMORY:{memory_id}": str(memory["fingerprint"])}
            artifact_states = {}
            strengths = []
            for artifact_id in source_artifacts:
                artifact = reasoning.get(artifact_id)
                if artifact is None:
                    raise KeyError(f"missing semantic artifact during export: {artifact_id}")
                source_fingerprints[f"ARTIFACT:{artifact_id}"] = str(artifact["artifact"]["fingerprint"])
                artifact_states[artifact_id] = str(artifact.get("state"))
                signal = (row.get("semantic_signals") or {}).get(artifact_id, {})
                strength = str(signal.get("verification_strength") or "")
                if strength:
                    strengths.append(strength)
            strength_rank = {"": 0, "SOLVER_VERDICT": 1, "MULTI_SOLVER_AGREEMENT": 2, "CHECKED_CERTIFICATE": 3, "TRUSTED_KERNEL": 4}
            verification_strength = min(strengths, key=lambda item: strength_rank.get(item, 0)) if strengths else ""
            kind_map = {
                "SEMANTIC": "SEMANTIC",
                "PROCEDURAL": "PROCEDURAL",
                "EPISODIC": "OBSERVATION",
                "WORKING": "SUMMARY",
                "SENSORY": "OBSERVATION",
            }
            knowledge_kind = str(meta.get("cross_run_knowledge_kind") or kind_map.get(str(memory.get("kind")), "SUMMARY"))
            envelope = CrossRunKnowledgeEnvelope(
                source_run_id=run_id,
                source_machine_id=str(self.snapshot.machine_id),
                source_scope_id=str(memory.get("scope_id") or "root"),
                knowledge_kind=knowledge_kind,
                content=deepcopy(memory.get("content")),
                source_memory_ids=(memory_id,),
                source_evidence_ids=tuple(memory.get("source_evidence_ids") or ()),
                source_artifact_ids=source_artifacts,
                source_fingerprints=source_fingerprints,
                source_authority_provenance={
                    "memory_created_by_decision": str(memory.get("created_by_decision") or ""),
                    "artifact_states": artifact_states,
                    "source_authority_is_provenance_only": True,
                },
                applicability_scope_ids=tuple(applicability_scope_ids),
                environment_fingerprint=str(environment_fingerprint or memory.get("compatibility_fingerprint") or ""),
                dependency_fingerprints=tuple(dependency_fingerprints or meta.get("dependency_fingerprints") or ()),
                verification_strength=verification_strength,
                privacy_level=privacy_level,
                privacy_principal_id=privacy_principal,
                retention_policy=str(memory.get("retention_policy") or "permanent"),
                freshness_seconds=freshness_seconds,
                created_at=float(row.get("created_at", 0) or 0),
                metadata={**deepcopy(dict(metadata or {})), "source_memory_kind": memory.get("kind"), "source_memory_version": memory.get("version")},
            )
            envelopes.append(envelope)
        bundle = CrossRunKnowledgeBundle(run_id, tuple(envelopes), metadata={"authority_transfer": "NEVER"})
        evidence_id = None
        if record:
            stored = self.add_evidence(EvidenceRecord(
                kind="cross_run_knowledge_export",
                statement=cross_run_document(bundle),
                source=CROSS_RUN_KNOWLEDGE_CONTRACT_ID,
                metadata={
                    "cross_run_record_type": "EXPORT",
                    "contract_id": CROSS_RUN_KNOWLEDGE_CONTRACT_ID,
                    "source_run_id": run_id,
                    "bundle_id": bundle.bundle_id,
                    "bundle_fingerprint": bundle.fingerprint,
                    "authority_transfer": "NEVER",
                },
            ), reason="cross-run knowledge bundle exported")
            evidence_id = stored.evidence_id
        return {"contract": cross_run_knowledge_contract(), "bundle": bundle.to_dict(), "export_evidence_id": evidence_id}

    def export_cross_run_delta(self, *, source_run_id: str | None = None) -> dict[str, Any]:
        run_id = str(source_run_id or self.snapshot.machine_id)
        projection = self.hierarchical_memory_report()
        signals = []
        seen = set()
        for record in self._cross_run_export_records():
            bundle = record["bundle"]
            if bundle.source_run_id != run_id:
                continue
            for envelope in bundle.envelopes:
                for memory_id in envelope.source_memory_ids:
                    current = projection.get("memories", {}).get(memory_id)
                    status = "MISSING" if current is None else str(current.get("status"))
                    if status == "ACTIVE":
                        continue
                    key = (envelope.envelope_id, status)
                    if key in seen:
                        continue
                    seen.add(key)
                    signals.append(CrossRunKnowledgeSignal(
                        source_run_id=run_id,
                        envelope_id=envelope.envelope_id,
                        envelope_fingerprint=envelope.fingerprint,
                        action="REVOKE",
                        reason=f"source memory no longer active: {status}",
                        metadata={"source_memory_id": memory_id, "source_memory_status": status},
                    ))
        bundle = CrossRunKnowledgeBundle(run_id, (), tuple(signals), metadata={"delta": True, "authority_transfer": "NEVER"})
        return {"contract": cross_run_knowledge_contract(), "bundle": bundle.to_dict()}

    def make_cross_run_signal(
        self,
        envelope_id: str,
        *,
        action: str,
        reason: str,
        authority_id: str,
        authority_class: str,
        superseded_by_envelope_id: str = "",
    ) -> dict[str, Any]:
        if authority_class not in {"POLICY", "CONTROLLER"}:
            raise PermissionError("cross-run source signal requires POLICY or CONTROLLER authority")
        source = None
        for record in self._cross_run_export_records():
            for envelope in record["bundle"].envelopes:
                if envelope.envelope_id == envelope_id:
                    source = envelope
                    break
        if source is None:
            raise KeyError(envelope_id)
        signal = CrossRunKnowledgeSignal(
            source_run_id=source.source_run_id,
            envelope_id=source.envelope_id,
            envelope_fingerprint=source.fingerprint,
            action=action,
            reason=reason,
            superseded_by_envelope_id=superseded_by_envelope_id,
            metadata={"authority_id": authority_id, "authority_class": authority_class},
        )
        return {"contract": cross_run_knowledge_contract(), "signal": signal.to_dict()}

    def inspect_cross_run_envelope(
        self,
        envelope: CrossRunKnowledgeEnvelope | Mapping[str, Any],
        *,
        target_scope_id: str = "root",
        privacy_principal_id: str = "",
        environment_fingerprint: str = "",
        dependency_fingerprints: Sequence[str] = (),
        required_strength: str = "",
        as_of: float | None = None,
        validator_id: str = "aasm.cross-run.validator",
        validator_version: str = "0.1.0",
    ) -> dict[str, Any]:
        if target_scope_id not in self.calculus_report()["scope_state"]["records"]:
            raise KeyError(f"unknown receiving scope: {target_scope_id}")
        parsed = envelope if isinstance(envelope, CrossRunKnowledgeEnvelope) else CrossRunKnowledgeEnvelope.from_dict(envelope)
        context = CrossRunAdmissionContext(
            receiving_run_id=str(self.snapshot.machine_id),
            target_scope_id=target_scope_id,
            privacy_principal_id=privacy_principal_id,
            environment_fingerprint=environment_fingerprint,
            dependency_fingerprints=tuple(dependency_fingerprints),
            required_strength=required_strength,
            as_of=float(self._cross_run_now() if as_of is None else as_of),
            validator_id=validator_id,
            validator_version=validator_version,
        )
        certificate = validate_cross_run_envelope(parsed, context)
        return {"contract": cross_run_knowledge_contract(), "envelope": parsed.to_dict(), "context": context.to_dict(), "certificate": certificate.to_dict()}

    def propose_cross_run_admission(self, envelope, *, proposer_id: str, **inspection_kwargs) -> dict[str, Any]:
        if not proposer_id:
            raise ValueError("cross-run admission requires proposer_id")
        inspected = self.inspect_cross_run_envelope(envelope, **inspection_kwargs)
        certificate = inspected["certificate"]
        if not certificate["valid"]:
            raise ValueError(f"cross-run knowledge not admissible: {certificate['reasons']}")
        parsed = CrossRunKnowledgeEnvelope.from_dict(inspected["envelope"])
        target_scope_id = str(inspected["context"]["target_scope_id"])
        seed = {
            "envelope_fingerprint": parsed.fingerprint,
            "receiving_run_id": str(self.snapshot.machine_id),
            "target_scope_id": target_scope_id,
            "validator_id": certificate["validator_id"],
            "validator_version": certificate["validator_version"],
            "proposer_id": proposer_id,
        }
        decision_id = "cross-run-admission-decision-" + semantic_fingerprint(seed)[:20]
        existing = self.calculus_report()["decisions"].get(decision_id)
        if existing is not None:
            return {"contract": cross_run_knowledge_contract(), "decision": deepcopy(existing), "certificate": certificate, "already_proposed": True}
        decision = DecisionRecord(
            decision_id=decision_id,
            subject=f"cross_run.admission:{parsed.envelope_id}",
            value={"envelope": parsed.to_dict(), "admission_certificate": certificate, "context": inspected["context"], "proposer_id": proposer_id},
            kind="EXPLICIT",
            status="PROPOSED",
            scope={"scope_id": target_scope_id},
        )
        registered = self.register_decision(decision, reason="cross-run knowledge admission proposed")
        return {"contract": cross_run_knowledge_contract(), "decision": registered, "certificate": certificate, "already_proposed": False}

    def authorize_cross_run_admission(self, decision_id: str, *, authority_id: str, authority_class: str) -> dict[str, Any]:
        if authority_class not in {"POLICY", "CONTROLLER"}:
            raise PermissionError("cross-run admission authorization requires POLICY or CONTROLLER authority")
        state = self.calculus_report()
        decision = state["decisions"].get(decision_id)
        if decision is None:
            raise KeyError(decision_id)
        value = decision.get("value") or {}
        if "envelope" not in value or "admission_certificate" not in value:
            raise ValueError("decision is not a v0.48 cross-run admission")
        if not bool(value["admission_certificate"].get("valid")):
            raise ValueError("cannot authorize invalid cross-run admission certificate")
        if decision.get("status") == "PROPOSED":
            self.activate_decision(decision_id, reason="cross-run knowledge admission authorized")
        elif decision.get("status") != "ACTIVE":
            raise ValueError(f"cross-run admission cannot authorize from {decision.get('status')}")
        envelope = CrossRunKnowledgeEnvelope.from_dict(value["envelope"])
        obligation_id = "cross-run-admission-obligation-" + semantic_fingerprint(decision_id)[:20]
        state = self.calculus_report()
        if obligation_id not in state["obligations"]:
            self.register_obligation(ObligationRecord(
                obligation_id=obligation_id,
                statement=f"cross-run-admit:{envelope.envelope_id}",
                status="AVAILABLE",
                decision_dependencies=[decision_id],
                required_evidence_types=["cross_run_knowledge_admission"],
                scope=deepcopy(decision.get("scope") or {}),
            ), reason="cross-run admission obligation created")
        auth = self.add_evidence(EvidenceRecord(
            kind="cross_run_knowledge_authorization",
            statement=canonical_semantic_json({
                "decision_id": decision_id,
                "envelope_id": envelope.envelope_id,
                "authority_id": authority_id,
                "authority_class": authority_class,
            }),
            source=CROSS_RUN_ADMISSION_CONTRACT_ID,
            metadata={
                "cross_run_record_type": "AUTHORIZATION",
                "decision_id": decision_id,
                "obligation_id": obligation_id,
                "envelope_id": envelope.envelope_id,
                "authority_id": authority_id,
                "authority_class": authority_class,
                "source_authority_inherited": False,
            },
        ), reason="cross-run admission authority recorded")
        return {"contract": cross_run_knowledge_contract(), "decision": deepcopy(self.calculus_report()["decisions"][decision_id]), "obligation": deepcopy(self.calculus_report()["obligations"][obligation_id]), "authorization_evidence_id": auth.evidence_id}

    def commit_cross_run_admission(self, decision_id: str, *, worker_id: str) -> dict[str, Any]:
        if not worker_id:
            raise ValueError("cross-run admission commit requires worker_id")
        state = self.calculus_report()
        decision = state["decisions"].get(decision_id)
        if decision is None:
            raise KeyError(decision_id)
        if decision.get("status") != "ACTIVE":
            raise ValueError("cross-run admission requires ACTIVE authorized decision")
        value = decision.get("value") or {}
        envelope = CrossRunKnowledgeEnvelope.from_dict(value["envelope"])
        certificate = deepcopy(value["admission_certificate"])
        target_scope_id = str((decision.get("scope") or {}).get("scope_id") or "root")
        report = self.cross_run_knowledge_report()
        existing = report.get("envelopes", {}).get(envelope.envelope_id)
        if existing is not None:
            if existing["envelope"]["fingerprint"] != envelope.fingerprint:
                raise ValueError("cross-run envelope ID collision")
            return {"contract": cross_run_knowledge_contract(), "entry": deepcopy(existing), "already_committed": True}
        obligation_id = "cross-run-admission-obligation-" + semantic_fingerprint(decision_id)[:20]
        obligation = state["obligations"].get(obligation_id)
        if obligation is None:
            raise KeyError(obligation_id)
        if obligation["status"] == "AVAILABLE":
            self.enable_obligation(obligation_id, reason="cross-run admission worker enabled")
        if self.calculus_report()["obligations"][obligation_id]["status"] == "ENABLED":
            self.set_obligation_status(obligation_id, "IN_PROGRESS", reason="cross-run admission worker started")
        stored = self.add_evidence(EvidenceRecord(
            kind="cross_run_knowledge_admission",
            statement=cross_run_document(envelope),
            source=CROSS_RUN_ADMISSION_CONTRACT_ID,
            metadata={
                "cross_run_record_type": "ADMISSION",
                "contract_id": CROSS_RUN_KNOWLEDGE_CONTRACT_ID,
                "admission_contract_id": CROSS_RUN_ADMISSION_CONTRACT_ID,
                "envelope_id": envelope.envelope_id,
                "envelope_fingerprint": envelope.fingerprint,
                "source_run_id": envelope.source_run_id,
                "receiving_run_id": str(self.snapshot.machine_id),
                "target_scope_id": target_scope_id,
                "scope_id": target_scope_id,
                "privacy_level": envelope.privacy_level,
                "privacy_principal_id": envelope.privacy_principal_id,
                "validator_id": certificate["validator_id"],
                "validator_version": certificate["validator_version"],
                "admission_certificate_id": certificate["certificate_id"],
                "admission_certificate_fingerprint": certificate["fingerprint"],
                "source_authority_inherited": False,
                "worker_id": worker_id,
            },
        ), reason="cross-run knowledge admitted as foreign evidence")
        self.set_obligation_status(obligation_id, "VERIFYING", evidence_ids=[stored.evidence_id], reason="cross-run admission evidence under verification")
        self.set_obligation_status(obligation_id, "VERIFIED", evidence_ids=[stored.evidence_id], reason="cross-run admission evidence verified")
        self.set_obligation_status(obligation_id, "COMMITTED", evidence_ids=[stored.evidence_id], reason="cross-run admission committed")
        return {"contract": cross_run_knowledge_contract(), "entry": deepcopy(self.cross_run_knowledge_report()["envelopes"][envelope.envelope_id]), "admission_evidence_id": stored.evidence_id, "already_committed": False}

    def cross_run_knowledge_report(self, *, as_of: float | None = None) -> dict[str, Any]:
        effective_as_of = float(self._cross_run_now() if as_of is None else as_of)
        envelopes: dict[str, dict[str, Any]] = {}
        signals: dict[str, list[dict[str, Any]]] = {}
        principal_maps: dict[str, dict[str, Any]] = {}
        reputation: list[dict[str, Any]] = []
        issues = []
        for evidence in self.snapshot.evidence.get("records", []):
            kind = evidence.get("kind")
            meta = evidence.get("metadata") or {}
            try:
                if kind == "cross_run_knowledge_admission" and meta.get("cross_run_record_type") == "ADMISSION":
                    envelope = CrossRunKnowledgeEnvelope.from_dict(json.loads(str(evidence.get("statement") or "{}")))
                    if envelope.fingerprint != meta.get("envelope_fingerprint"):
                        raise ValueError("cross-run admission envelope fingerprint mismatch")
                    prior = envelopes.get(envelope.envelope_id)
                    if prior is not None and prior["envelope"]["fingerprint"] != envelope.fingerprint:
                        raise ValueError("cross-run admission envelope ID collision")
                    envelopes[envelope.envelope_id] = {
                        "envelope": envelope.to_dict(),
                        "admission_evidence_id": str(evidence.get("evidence_id")),
                        "created_at": float(evidence.get("created_at", 0) or 0),
                        "target_scope_id": str(meta.get("target_scope_id") or "root"),
                        "validator_id": str(meta.get("validator_id") or ""),
                        "validator_version": str(meta.get("validator_version") or ""),
                        "source_authority_inherited": bool(meta.get("source_authority_inherited", False)),
                    }
                elif kind == "cross_run_knowledge_signal" and meta.get("cross_run_record_type") == "SIGNAL":
                    signal = CrossRunKnowledgeSignal.from_dict(json.loads(str(evidence.get("statement") or "{}")))
                    if signal.fingerprint != meta.get("signal_fingerprint"):
                        raise ValueError("cross-run signal fingerprint mismatch")
                    signals.setdefault(signal.envelope_id, []).append({"signal": signal.to_dict(), "evidence_id": str(evidence.get("evidence_id"))})
                elif kind == "cross_run_principal_map" and meta.get("cross_run_record_type") == "PRINCIPAL_MAP":
                    mapping = CrossRunPrincipalMap.from_dict(json.loads(str(evidence.get("statement") or "{}")))
                    if mapping.fingerprint != meta.get("mapping_fingerprint"):
                        raise ValueError("cross-run principal map fingerprint mismatch")
                    principal_maps[mapping.mapping_id] = {"mapping": mapping.to_dict(), "evidence_id": str(evidence.get("evidence_id"))}
                elif kind == "cross_run_sii_reputation" and meta.get("cross_run_record_type") == "SII_REPUTATION":
                    reputation.append({"statement": deepcopy(json.loads(str(evidence.get("statement") or "{}"))), "evidence_id": str(evidence.get("evidence_id")), "metadata": deepcopy(meta)})
            except Exception as exc:
                if kind in {"cross_run_knowledge_admission", "cross_run_knowledge_signal", "cross_run_principal_map", "cross_run_sii_reputation"}:
                    issues.append(f"{evidence.get('evidence_id', '?')}: {exc}")
        for envelope_id, row in envelopes.items():
            envelope = CrossRunKnowledgeEnvelope.from_dict(row["envelope"])
            rows = sorted(signals.get(envelope_id, []), key=lambda item: item["signal"]["signal_id"])
            status = "ACTIVE"
            if rows:
                status = "SUPERSEDED" if any(item["signal"]["action"] == "SUPERSEDE" for item in rows) else "REVOKED"
            if status == "ACTIVE" and envelope.freshness_seconds is not None and effective_as_of > envelope.created_at + envelope.freshness_seconds:
                status = "STALE"
            if status == "ACTIVE" and envelope.retention_policy.startswith("ttl:") and effective_as_of > envelope.created_at + int(envelope.retention_policy.split(":", 1)[1]):
                status = "EXPIRED"
            row["status"] = status
            row["signals"] = deepcopy(rows)
        return {
            "contract": cross_run_knowledge_contract(),
            "valid": not issues,
            "issues": issues,
            "as_of": effective_as_of,
            "envelopes": deepcopy(dict(sorted(envelopes.items()))),
            "principal_maps": deepcopy(dict(sorted(principal_maps.items()))),
            "sii_reputation": deepcopy(reputation),
            "counts": {
                "total": len(envelopes),
                "active": sum(row.get("status") == "ACTIVE" for row in envelopes.values()),
                "revoked": sum(row.get("status") == "REVOKED" for row in envelopes.values()),
                "superseded": sum(row.get("status") == "SUPERSEDED" for row in envelopes.values()),
                "stale": sum(row.get("status") == "STALE" for row in envelopes.values()),
                "expired": sum(row.get("status") == "EXPIRED" for row in envelopes.values()),
            },
            "projection_fingerprint": semantic_fingerprint({key: {"envelope": row["envelope"], "status": row.get("status")} for key, row in sorted(envelopes.items())}),
        }

    def apply_cross_run_signal(self, signal: CrossRunKnowledgeSignal | Mapping[str, Any], *, authority_id: str, authority_class: str) -> dict[str, Any]:
        if authority_class not in {"POLICY", "CONTROLLER"}:
            raise PermissionError("cross-run signal admission requires POLICY or CONTROLLER authority")
        signal = signal if isinstance(signal, CrossRunKnowledgeSignal) else CrossRunKnowledgeSignal.from_dict(signal)
        report = self.cross_run_knowledge_report()
        row = report.get("envelopes", {}).get(signal.envelope_id)
        if row is None:
            raise KeyError(signal.envelope_id)
        envelope = CrossRunKnowledgeEnvelope.from_dict(row["envelope"])
        if signal.source_run_id != envelope.source_run_id or signal.envelope_fingerprint != envelope.fingerprint:
            raise ValueError("cross-run signal does not match admitted source envelope")
        for existing in row.get("signals", []):
            if existing["signal"]["signal_id"] == signal.signal_id:
                if existing["signal"]["fingerprint"] != signal.fingerprint:
                    raise ValueError("cross-run signal ID collision")
                return {"contract": cross_run_knowledge_contract(), "signal": deepcopy(existing), "already_applied": True}
        stored = self.add_evidence(EvidenceRecord(
            kind="cross_run_knowledge_signal",
            statement=cross_run_document(signal),
            source=CROSS_RUN_KNOWLEDGE_CONTRACT_ID,
            metadata={
                "cross_run_record_type": "SIGNAL",
                "signal_id": signal.signal_id,
                "signal_fingerprint": signal.fingerprint,
                "envelope_id": signal.envelope_id,
                "source_run_id": signal.source_run_id,
                "authority_id": authority_id,
                "authority_class": authority_class,
                "source_signal_admitted_by_receiving_policy": True,
            },
        ), reason="cross-run revocation/supersession signal admitted")
        return {"contract": cross_run_knowledge_contract(), "signal": signal.to_dict(), "evidence_id": stored.evidence_id, "entry": deepcopy(self.cross_run_knowledge_report()["envelopes"][signal.envelope_id]), "already_applied": False}

    def materialize_cross_run_knowledge(
        self,
        envelope_id: str,
        *,
        proposer_id: str,
        local_authorized_artifact_ids: Sequence[str] = (),
        retention_policy: str | None = None,
    ) -> dict[str, Any]:
        report = self.cross_run_knowledge_report()
        row = report.get("envelopes", {}).get(envelope_id)
        if row is None:
            raise KeyError(envelope_id)
        if row.get("status") != "ACTIVE":
            raise ValueError(f"cross-run knowledge must be ACTIVE to materialize: {row.get('status')}")
        envelope = CrossRunKnowledgeEnvelope.from_dict(row["envelope"])
        target_scope_id = str(row.get("target_scope_id") or "root")
        mapping = {
            "SEMANTIC": ("SEMANTIC", "STRUCTURED"),
            "PROCEDURAL": ("PROCEDURAL", "STRUCTURED"),
            "OBSERVATION": ("EPISODIC", "REFERENCE"),
            "SUMMARY": ("PROCEDURAL", "STRUCTURED"),
        }
        if envelope.knowledge_kind not in mapping:
            raise ValueError(f"cross-run kind is not materializable as governed memory: {envelope.knowledge_kind}")
        memory_kind, substrate = mapping[envelope.knowledge_kind]
        artifacts = tuple(sorted(set(map(str, local_authorized_artifact_ids))))
        if memory_kind == "SEMANTIC":
            if not artifacts:
                raise ValueError("cross-run semantic materialization requires local AUTHORIZED reasoning artifacts")
            reasoning = self.reasoning_report().get("artifacts", {})
            invalid = [artifact_id for artifact_id in artifacts if artifact_id not in reasoning or reasoning[artifact_id].get("state") != "AUTHORIZED"]
            if invalid:
                raise ValueError(f"cross-run semantic materialization requires local AUTHORIZED reasoning artifacts: {invalid}")
        proposed = self.propose_memory_operation(
            "STORE",
            scope_id=target_scope_id,
            proposer_id=proposer_id,
            kind=memory_kind,
            substrate=substrate,
            content={"cross_run_envelope_id": envelope.envelope_id, "source_run_id": envelope.source_run_id, "content": deepcopy(envelope.content)},
            source_evidence_ids=(row["admission_evidence_id"],),
            semantic_artifact_ids=artifacts,
            retention_policy=str(retention_policy or envelope.retention_policy),
            privacy_level=envelope.privacy_level,
            compatibility_fingerprint=envelope.environment_fingerprint if substrate == "EXECUTION_SNAPSHOT" else "",
            metadata={
                "cross_run_envelope_id": envelope.envelope_id,
                "cross_run_envelope_fingerprint": envelope.fingerprint,
                "source_run_id": envelope.source_run_id,
                "source_authority_inherited": False,
                "privacy_principal_id": envelope.privacy_principal_id,
                "cross_run_validator_id": row.get("validator_id"),
                "cross_run_validator_version": row.get("validator_version"),
            },
            reason="cross-run knowledge proposed for local governed memory materialization",
        )
        return {"contract": cross_run_knowledge_contract(), "materialization": proposed, "note": "Existing v0.40 POLICY/CONTROLLER authorization and commit remain required."}

    def register_cross_run_reuse_candidate(self, envelope_id: str, request: ReuseRequest | Mapping[str, Any], *, authority_id: str, authority_class: str) -> dict[str, Any]:
        if authority_class not in {"POLICY", "CONTROLLER"}:
            raise PermissionError("cross-run reuse candidate admission requires POLICY or CONTROLLER authority")
        request = request if isinstance(request, ReuseRequest) else ReuseRequest(**deepcopy(dict(request)))
        report = self.cross_run_knowledge_report()
        row = report.get("envelopes", {}).get(envelope_id)
        if row is None:
            raise KeyError(envelope_id)
        if row.get("status") != "ACTIVE":
            raise ValueError(f"cross-run knowledge must be ACTIVE for reuse: {row.get('status')}")
        envelope = CrossRunKnowledgeEnvelope.from_dict(row["envelope"])
        if envelope.knowledge_kind not in {"REUSE_RESULT", "SEMANTIC", "PROCEDURAL", "SUMMARY"}:
            raise ValueError(f"cross-run knowledge kind is not reusable: {envelope.knowledge_kind}")
        if request.semantic_payload != envelope.content:
            raise ValueError("v0.48 cross-run reuse requires exact semantic payload equality")
        source = self.canonical_reuse_ref(
            "EVIDENCE",
            row["admission_evidence_id"],
            privacy_level=envelope.privacy_level,
            privacy_principal_id=envelope.privacy_principal_id,
        )
        candidate = ReuseCandidate(
            kind=request.kind,
            request_fingerprint=request.fingerprint,
            source=source,
            semantic_payload=deepcopy(envelope.content),
            environment_fingerprint=envelope.environment_fingerprint,
            dependency_fingerprints=envelope.dependency_fingerprints,
            created_at=float(row.get("created_at", 0) or 0),
            effect_class=request.effect_class,
            verification_strength=envelope.verification_strength,
            reusable_modes=("EXACT",),
            metadata={
                "cross_run": True,
                "cross_run_envelope_id": envelope.envelope_id,
                "cross_run_envelope_fingerprint": envelope.fingerprint,
                "source_run_id": envelope.source_run_id,
                "receiving_run_id": str(self.snapshot.machine_id),
                "admission_validator_id": row.get("validator_id"),
                "admission_validator_version": row.get("validator_version"),
                "authority_inherited": False,
            },
        )
        registered = self.register_reuse_candidate(candidate, authority_id=authority_id, authority_class=authority_class)
        return {"contract": cross_run_knowledge_contract(), "candidate": registered, "envelope": envelope.to_dict()}

    def map_cross_run_principal(self, mapping: CrossRunPrincipalMap | Mapping[str, Any], *, authority_id: str, authority_class: str) -> dict[str, Any]:
        if authority_class not in {"POLICY", "CONTROLLER"}:
            raise PermissionError("cross-run principal mapping requires POLICY or CONTROLLER authority")
        mapping = mapping if isinstance(mapping, CrossRunPrincipalMap) else CrossRunPrincipalMap.from_dict(mapping)
        governance = self.sii_governance_report()
        principals = governance.get("principals", {})
        if mapping.local_principal_id not in principals:
            raise KeyError(f"local governed SII principal is not bound: {mapping.local_principal_id}")
        report = self.cross_run_knowledge_report()
        for row in report.get("principal_maps", {}).values():
            prior = row["mapping"]
            if prior["source_run_id"] == mapping.source_run_id and prior["source_principal_id"] == mapping.source_principal_id:
                if prior["local_principal_id"] != mapping.local_principal_id:
                    raise ValueError("stable cross-run principal cannot silently rebind")
                return {"contract": cross_run_knowledge_contract(), "mapping": deepcopy(row), "already_mapped": True}
        stored = self.add_evidence(EvidenceRecord(
            kind="cross_run_principal_map",
            statement=cross_run_document(mapping),
            source=CROSS_RUN_PRINCIPAL_MAP_CONTRACT_ID,
            metadata={
                "cross_run_record_type": "PRINCIPAL_MAP",
                "mapping_id": mapping.mapping_id,
                "mapping_fingerprint": mapping.fingerprint,
                "authority_id": authority_id,
                "authority_class": authority_class,
                "authority_transfer": "NEVER",
                "resource_entitlement_transfer": "NEVER",
            },
        ), reason="cross-run governed principal mapping admitted")
        return {"contract": cross_run_knowledge_contract(), "mapping": mapping.to_dict(), "evidence_id": stored.evidence_id, "already_mapped": False}

    def admit_cross_run_sii_reputation(self, envelope_id: str, *, local_principal_id: str, authority_id: str, authority_class: str) -> dict[str, Any]:
        if authority_class not in {"POLICY", "CONTROLLER"}:
            raise PermissionError("cross-run SII reputation admission requires POLICY or CONTROLLER authority")
        report = self.cross_run_knowledge_report()
        row = report.get("envelopes", {}).get(envelope_id)
        if row is None:
            raise KeyError(envelope_id)
        if row.get("status") != "ACTIVE":
            raise ValueError("cross-run SII reputation requires ACTIVE envelope")
        envelope = CrossRunKnowledgeEnvelope.from_dict(row["envelope"])
        if envelope.knowledge_kind != "SII_REPUTATION":
            raise ValueError("envelope is not SII_REPUTATION")
        mappings = [item["mapping"] for item in report.get("principal_maps", {}).values() if item["mapping"]["source_run_id"] == envelope.source_run_id and item["mapping"]["local_principal_id"] == local_principal_id]
        if not mappings:
            raise ValueError("cross-run SII reputation requires an admitted stable principal mapping")
        governance = self.sii_governance_report()
        if local_principal_id not in governance.get("principals", {}):
            raise KeyError(local_principal_id)
        statement = {
            "envelope_id": envelope.envelope_id,
            "source_run_id": envelope.source_run_id,
            "local_principal_id": local_principal_id,
            "performance": deepcopy(envelope.content),
            "truth_authority": "NONE",
            "resource_entitlement": "NONE",
            "accounting_plane": "CROSS_RUN_REFERENCE_ONLY",
        }
        stored = self.add_evidence(EvidenceRecord(
            kind="cross_run_sii_reputation",
            statement=canonical_semantic_json(statement),
            source=CROSS_RUN_KNOWLEDGE_CONTRACT_ID,
            derived_from=[row["admission_evidence_id"]],
            metadata={
                "cross_run_record_type": "SII_REPUTATION",
                "envelope_id": envelope.envelope_id,
                "local_principal_id": local_principal_id,
                "truth_authority": "NONE",
                "resource_entitlement": "NONE",
                "used_by_sii_resource_lease": False,
                "authority_id": authority_id,
                "authority_class": authority_class,
            },
        ), reason="cross-run SII reputation admitted to separate accounting plane")
        return {"contract": cross_run_knowledge_contract(), "reputation": statement, "evidence_id": stored.evidence_id, "note": "Cross-run reputation does not alter local SII authority or resource tiers."}


__all__ = ["CrossRunKnowledgeRuntimeMixin"]
