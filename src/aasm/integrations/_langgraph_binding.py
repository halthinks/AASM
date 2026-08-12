from __future__ import annotations

"""Binding and authority mappings for the thin LangGraph adapter."""

from typing import Any, Mapping, Sequence

from ..calculus import DecisionRecord, ObligationRecord
from ..effects import EffectRecord, EffectSpec
from ..evidence import EvidenceRecord
from ..model import ProblemSpec
from ..persistence import MemoryStore
from ._langgraph_types import (
    LANGGRAPH_ADAPTER_ID, LANGGRAPH_ADAPTER_VERSION,
    _BIND_EVENT, _EFFECT_AUTHORIZED, _NODE_ENTERED, _NODE_FAILED,
    _NODE_SUCCEEDED, _RECOVERY_RECORDED, _ROUTE_RECORDED,
    LangGraphBinding, LangGraphRecoveryAction, LangGraphRecoveryResult,
    LangGraphRunKey, _configurable, _fingerprint, _json_safe, _stable_id,
)


class LangGraphBindingMixin:
    def __init__(
        self,
        *,
        store: Any | None = None,
        namespace: str = "default",
        binding_scope: str = "THREAD",
        authority: Any | None = None,
        engine_class: type[Any] | None = None,
    ) -> None:
        self.store = store if store is not None else MemoryStore()
        self.namespace = str(namespace)
        self.binding_scope = binding_scope.upper()
        self.authority = authority
        if engine_class is None:
            # Imported lazily so runtime_v29 can expose this adapter without a
            # module-import cycle. Instantiation occurs after module loading.
            from .. import AASMEngine as engine_class
        self.engine_class = engine_class

    @staticmethod
    def _integration_events(engine: Any, event_type: str | None = None) -> list[Any]:
        events = engine.store.load_events(engine.snapshot.machine_id)
        return [event for event in events if event_type is None or event.event_type == event_type]

    def bind(
        self,
        config: Mapping[str, Any] | None,
        *,
        goal: str = "LangGraph run governed by AASM",
        run_id: str | None = None,
    ) -> tuple[Any, LangGraphBinding]:
        key = LangGraphRunKey.from_config(
            config,
            namespace=self.namespace,
            binding_scope=self.binding_scope,
            run_id=run_id,
        )
        machine_id = key.machine_id
        created = False
        try:
            engine = self.engine_class.resume(machine_id, self.store, authority=self.authority)
        except KeyError:
            engine = self.engine_class(
                ProblemSpec(
                    goal,
                    features={
                        "integration": LANGGRAPH_ADAPTER_ID,
                        "binding_scope": key.binding_scope,
                    },
                ),
                authority=self.authority,
                store=self.store,
                machine_id=machine_id,
            )
            created = True

        binding_events = self._integration_events(engine, _BIND_EVENT)
        expected = key.to_dict()
        if binding_events:
            first = binding_events[0].data.get("binding")
            if first != expected:
                raise ValueError(
                    "deterministic LangGraph machine identity collides with a different binding"
                )
        elif not created:
            raise ValueError(
                f"machine {machine_id} exists but was not created by {LANGGRAPH_ADAPTER_ID}"
            )
        else:
            engine.emit(
                _BIND_EVENT,
                engine.state_value,
                engine.state_value,
                "LangGraph thread/run bound to canonical AASM machine",
                data={
                    "adapter_id": LANGGRAPH_ADAPTER_ID,
                    "adapter_version": LANGGRAPH_ADAPTER_VERSION,
                    "binding": expected,
                    "binding_fingerprint": key.fingerprint,
                    "checkpoint_authority": "LANGGRAPH",
                    "machine_authority": "AASM",
                },
            )
        return engine, LangGraphBinding(machine_id, key, created)

    def binding_report(
        self,
        config: Mapping[str, Any] | None,
        *,
        goal: str = "LangGraph run governed by AASM",
        run_id: str | None = None,
    ) -> dict[str, Any]:
        engine, binding = self.bind(config, goal=goal, run_id=run_id)
        return {**binding.to_dict(), "integration": self.integration_report(engine)}

    def _binding_for_engine(self, engine: Any) -> dict[str, Any]:
        events = self._integration_events(engine, _BIND_EVENT)
        if not events:
            raise ValueError("machine has no LangGraph binding event")
        return dict(events[0].data)

    def integration_report(self, engine: Any) -> dict[str, Any]:
        events = self._integration_events(engine)
        binding = next((event.data for event in events if event.event_type == _BIND_EVENT), None)
        nodes = [
            {
                "event_id": event.event_id,
                "sequence": event.sequence,
                "event_type": event.event_type,
                **dict(event.data),
            }
            for event in events
            if event.event_type in {_NODE_ENTERED, _NODE_SUCCEEDED, _NODE_FAILED}
        ]
        recoveries = [
            {"event_id": event.event_id, "sequence": event.sequence, **dict(event.data)}
            for event in events
            if event.event_type == _RECOVERY_RECORDED
        ]
        routes = [
            {"event_id": event.event_id, "sequence": event.sequence, **dict(event.data)}
            for event in events
            if event.event_type == _ROUTE_RECORDED
        ]
        effects = [
            {"event_id": event.event_id, "sequence": event.sequence, **dict(event.data)}
            for event in events
            if event.event_type == _EFFECT_AUTHORIZED
        ]
        return {
            "schema_version": 1,
            "adapter_id": LANGGRAPH_ADAPTER_ID,
            "adapter_version": LANGGRAPH_ADAPTER_VERSION,
            "machine_id": engine.snapshot.machine_id,
            "binding": binding,
            "node_events": nodes,
            "route_events": routes,
            "recovery_events": recoveries,
            "effect_events": effects,
            "checkpoint_state_authority": "LANGGRAPH",
            "machine_truth_authority": "AASM_EVENT_HISTORY",
            "direct_storage_mutation": False,
            "duplicate_scheduler": False,
            "event_count": len(events),
            "replay_snapshot_hash": engine.replay().canonical_hash(),
            "persisted_snapshot_hash": engine.snapshot.canonical_hash(),
        }

    @staticmethod
    def _existing_evidence(engine: Any, evidence_id: str) -> dict[str, Any] | None:
        return next(
            (
                dict(record)
                for record in engine.snapshot.evidence.get("records", [])
                if record.get("evidence_id") == evidence_id
            ),
            None,
        )

    def record_evidence(
        self,
        engine: Any,
        *,
        kind: str,
        statement: str,
        source: str = "langgraph",
        evidence_type: str,
        metadata: Mapping[str, Any] | None = None,
        evidence_id: str | None = None,
        supports: Sequence[str] = (),
        contradicts: Sequence[str] = (),
        derived_from: Sequence[str] = (),
        confidence: float | None = 1.0,
    ) -> Any:
        selected_id = evidence_id or _stable_id(
            "evidence",
            engine.snapshot.machine_id,
            kind,
            statement,
            source,
            evidence_type,
            metadata or {},
        )
        existing = self._existing_evidence(engine, selected_id)
        if existing is not None:
            if existing.get("statement") != statement or existing.get("kind") != kind:
                raise ValueError(f"evidence identity collision: {selected_id}")
            return engine.evidence_ledger.get(selected_id)
        return engine.add_evidence(
            EvidenceRecord(
                kind=kind,
                statement=statement,
                source=source,
                confidence=confidence,
                supports=list(supports),
                contradicts=list(contradicts),
                derived_from=list(derived_from),
                metadata={"evidence_type": evidence_type, **dict(metadata or {})},
                evidence_id=selected_id,
            ),
            reason="LangGraph evidence recorded through canonical AASM ledger",
        )

    def record_decision(
        self,
        engine: Any,
        *,
        subject: str,
        value: Any,
        decision_id: str | None = None,
        kind: str = "EXPLICIT",
        parent_ids: Sequence[str] = (),
        evidence_ids: Sequence[str] = (),
        antecedent_constraint_ids: Sequence[str] = (),
        pinned: bool = False,
        activate: bool = True,
        scope: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        selected_id = decision_id or _stable_id(
            "decision", engine.snapshot.machine_id, subject, value, scope or {}
        )
        report = engine.calculus_report()
        existing = report["decisions"].get(selected_id)
        normalized_value = _json_safe(value)
        if existing is not None:
            if existing.get("subject") != subject or existing.get("value") != normalized_value:
                raise ValueError(f"decision identity collision: {selected_id}")
            return existing
        record = DecisionRecord(
            selected_id,
            subject,
            normalized_value,
            kind="PINNED" if pinned and kind == "EXPLICIT" else kind,
            parent_ids=list(parent_ids),
            evidence_ids=list(evidence_ids),
            antecedent_constraint_ids=list(antecedent_constraint_ids),
            pinned=pinned,
            scope={"integration": LANGGRAPH_ADAPTER_ID, **dict(scope or {})},
        )
        created = engine.register_decision(
            record, reason="LangGraph decision registered through canonical AASM calculus"
        )
        if not activate:
            return created
        current_id = engine.calculus_report()["active_model"].get(subject)
        activation = engine.activate_decision(
            selected_id,
            supersede_decision_id=current_id if current_id and current_id != selected_id else None,
            reason="LangGraph decision activated through canonical AASM calculus",
        )
        return activation["decision"]

    def record_obligation(
        self,
        engine: Any,
        *,
        statement: str,
        obligation_id: str | None = None,
        decision_dependencies: Sequence[str] = (),
        dependencies: Sequence[str] = (),
        required_evidence_types: Sequence[str] = (),
        mandatory: bool = True,
        persistent: bool = True,
        scope: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        selected_id = obligation_id or _stable_id(
            "obligation", engine.snapshot.machine_id, statement, scope or {}
        )
        report = engine.calculus_report()
        existing = report["obligations"].get(selected_id)
        if existing is not None:
            if existing.get("statement") != statement:
                raise ValueError(f"obligation identity collision: {selected_id}")
            return existing
        return engine.register_obligation(
            ObligationRecord(
                selected_id,
                statement,
                decision_dependencies=list(decision_dependencies),
                dependencies=list(dependencies),
                required_evidence_types=list(required_evidence_types),
                mandatory=mandatory,
                persistent=persistent,
                scope={"integration": LANGGRAPH_ADAPTER_ID, **dict(scope or {})},
            ),
            reason="LangGraph obligation registered through canonical AASM calculus",
        )

    def authorize_effect(
        self,
        engine: Any,
        *,
        effect_type: str,
        payload: Mapping[str, Any] | None = None,
        idempotency_key: str,
        authority: str = "langgraph-adapter",
        reversible: bool = False,
    ) -> EffectRecord:
        spec = EffectSpec(
            effect_type=effect_type,
            payload=_json_safe(dict(payload or {})),
            idempotency_key=idempotency_key,
            reversible=reversible,
        )
        record = engine.propose_effect(spec)
        if record.status == "PROPOSED":
            record = engine.authorize_effect(record.spec.effect_id, authority=authority)
        engine.emit(
            _EFFECT_AUTHORIZED,
            engine.state_value,
            engine.state_value,
            "LangGraph external effect authorized by AASM",
            data={
                "effect_id": record.spec.effect_id,
                "effect_type": record.spec.effect_type,
                "idempotency_key": record.spec.idempotency_key,
                "status": record.status,
            },
        )
        return record
