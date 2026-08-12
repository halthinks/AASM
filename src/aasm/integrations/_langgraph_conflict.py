from __future__ import annotations

"""Conflict learning and recovery mappings for the thin LangGraph adapter."""

from typing import Any, Mapping, Sequence

from ..calculus import ConflictRecord, ExplanationRecord
from ._langgraph_types import (
    LANGGRAPH_ADAPTER_ID, _RECOVERY_RECORDED, LangGraphRecoveryAction,
    LangGraphRecoveryResult,
    _json_safe, _stable_id,
)


class LangGraphConflictMixin:
    def record_conflict(
        self,
        engine: Any,
        *,
        statement: str,
        implicated_decision_ids: Sequence[str],
        observed_at_obligation_id: str | None = None,
        conflict_id: str | None = None,
        learn: bool = True,
        backjump: bool = True,
    ) -> dict[str, Any]:
        decision_ids = sorted(set(str(value) for value in implicated_decision_ids))
        if not decision_ids:
            raise ValueError("at least one implicated decision is required")
        calculus = engine.calculus_report()
        missing = [decision_id for decision_id in decision_ids if decision_id not in calculus["decisions"]]
        if missing:
            raise KeyError(f"unknown implicated decisions: {missing}")
        selected_conflict = conflict_id or _stable_id(
            "conflict", engine.snapshot.machine_id, statement, decision_ids
        )
        evidence = self.record_evidence(
            engine,
            kind="contradiction",
            statement=statement,
            source="langgraph",
            evidence_type="langgraph_contradiction",
            evidence_id=_stable_id("evidence", selected_conflict, "contradiction"),
            metadata={"conflict_id": selected_conflict},
        )
        current = engine.calculus_report()
        if selected_conflict not in current["conflicts"]:
            engine.raise_conflict(
                ConflictRecord(
                    selected_conflict,
                    "ASSUMPTION_CONFLICT",
                    [evidence.evidence_id],
                    implicated_decision_ids=decision_ids,
                    observed_at_obligation_id=observed_at_obligation_id,
                    scope={"integration": LANGGRAPH_ADAPTER_ID},
                ),
                reason="LangGraph contradiction raised through canonical AASM calculus",
            )
        explanation_id = _stable_id("explanation", selected_conflict, decision_ids)
        current = engine.calculus_report()
        if explanation_id not in current["explanations"]:
            literals = [
                {
                    "subject": current["decisions"][decision_id]["subject"],
                    "op": "EQ",
                    "value": current["decisions"][decision_id]["value"],
                    "decision_id": decision_id,
                }
                for decision_id in decision_ids
            ]
            engine.register_explanation(
                ExplanationRecord(
                    explanation_id,
                    selected_conflict,
                    literals,
                    [evidence.evidence_id],
                    status="VALIDATED",
                    minimality="IRREDUCIBLE" if len(literals) == 1 else "NONE",
                    certificate={
                        "type": "langgraph_contradiction",
                        "adapter_id": LANGGRAPH_ADAPTER_ID,
                    },
                ),
                reason="LangGraph conflict explanation registered",
            )
        constraint_id = _stable_id("constraint", explanation_id)
        certificate_id = _stable_id("certificate", constraint_id)
        if learn:
            current = engine.calculus_report()
            if constraint_id not in current["constraints"]:
                engine.learn_constraint(
                    explanation_id,
                    constraint_id,
                    strength="HARD",
                    reason="LangGraph conflict projected as learned no-good",
                )
                engine.register_projection_certificate(
                    constraint_id,
                    certificate_id=certificate_id,
                    reason="LangGraph learned no-good certificate registered",
                )
                verification = engine.verify_projection_certificate(
                    certificate_id,
                    reason="LangGraph learned no-good certificate verified",
                )
                if not verification["valid"]:
                    raise ValueError("projection certificate verification failed")
                engine.promote_constraint_hard(
                    constraint_id,
                    certificate_id,
                    reason="LangGraph learned no-good promoted to hard",
                )
        recovery = None
        if backjump:
            conflict = engine.calculus_report()["conflicts"][selected_conflict]
            if conflict.get("status") != "RESOLVED":
                recovery = engine.backjump_conflict(
                    selected_conflict,
                    explanation_id=explanation_id,
                    reason="LangGraph contradiction caused causal AASM backjump",
                )
        return {
            "conflict_id": selected_conflict,
            "explanation_id": explanation_id,
            "constraint_id": constraint_id if learn else None,
            "certificate_id": certificate_id if learn else None,
            "evidence_id": evidence.evidence_id,
            "recovery": recovery,
        }

    def recover(
        self,
        engine: Any,
        action: str | LangGraphRecoveryAction,
        *,
        reason: str,
        conflict_id: str | None = None,
        target: str | None = None,
        update: Mapping[str, Any] | None = None,
        at_sequence: int | None = None,
    ) -> LangGraphRecoveryResult:
        selected = LangGraphRecoveryAction(action).value
        aasm_result: dict[str, Any] = {}
        fork_machine_id: str | None = None
        if selected == LangGraphRecoveryAction.BACKJUMP.value:
            if not conflict_id:
                raise ValueError("BACKJUMP requires conflict_id")
            aasm_result = engine.backjump_conflict(conflict_id, reason=reason)
        elif selected == LangGraphRecoveryAction.RESTART.value:
            aasm_result = engine.restart_search(reason=reason)
        elif selected == LangGraphRecoveryAction.FORK.value:
            sequence = engine.current_sequence() if at_sequence is None else int(at_sequence)
            forked = engine.fork(sequence)
            fork_machine_id = forked.snapshot.machine_id
            aasm_result = {
                "source_machine_id": engine.snapshot.machine_id,
                "source_sequence": sequence,
                "fork_machine_id": fork_machine_id,
            }
        elif selected == LangGraphRecoveryAction.PAUSE.value:
            aasm_result = {"pause_required": True, "checkpoint_control": "LANGGRAPH"}
        elif selected == LangGraphRecoveryAction.REPAIR.value:
            aasm_result = {"repair_required": True}
        elif selected == LangGraphRecoveryAction.CONTINUE.value:
            aasm_result = {"continue": True}
        result = LangGraphRecoveryResult(
            selected,
            engine.snapshot.machine_id,
            reason,
            conflict_id=conflict_id,
            target=target,
            update=_json_safe(dict(update or {})),
            fork_machine_id=fork_machine_id,
            aasm_result=_json_safe(aasm_result),
        )
        engine.emit(
            _RECOVERY_RECORDED,
            engine.state_value,
            engine.state_value,
            reason,
            data=result.to_dict(),
        )
        return result

