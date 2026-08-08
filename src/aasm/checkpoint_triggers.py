from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .change_impact import ChangeKind, ChangeSignal


@dataclass
class CheckpointTriggerPolicy:
    enabled: bool = True
    on_tests_failed: bool = True
    on_assumption_changed: bool = True
    on_unexpected_output: bool = True
    on_blocking: bool = True
    pause_affected: bool = True


@dataclass
class CheckpointTrigger:
    triggered: bool
    reason: str
    signal: ChangeSignal | None = None
    verifier_report_id: str | None = None
    task_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self):
        raw = asdict(self)
        if self.signal is not None:
            raw["signal"] = asdict(self.signal)
        return raw


class CheckpointTriggerEngine:
    """Deterministically maps verification changes into selective checkpoints.

    This decides whether changed information requires an impact checkpoint. It
    does not authorize a plan mutation; Planner authority remains separate.
    """

    def evaluate(self, report: dict[str, Any], policy: CheckpointTriggerPolicy | None = None) -> CheckpointTrigger:
        policy = policy or CheckpointTriggerPolicy()
        task_id = report.get("task_id")
        report_id = report.get("verifier_report_id")
        if not policy.enabled:
            return CheckpointTrigger(False, "automatic checkpoint triggers disabled", verifier_report_id=report_id, task_id=task_id)

        kind = None
        reason = None
        if policy.on_blocking and bool(report.get("blocking")):
            kind = ChangeKind.RISK_ESCALATED
            reason = "Verifier reported a blocking finding"
        elif policy.on_assumption_changed and bool(report.get("assumption_changed")):
            kind = ChangeKind.ASSUMPTION_CHANGED
            reason = "Verifier reported a changed assumption"
        elif policy.on_unexpected_output and bool(report.get("unexpected_output")):
            kind = ChangeKind.MATERIAL_PLAN_CHANGE
            reason = "Verifier reported unexpected output"
        elif policy.on_tests_failed and report.get("tests_passed") is False:
            kind = ChangeKind.VERIFICATION_FAILED
            reason = "Verifier reported failed tests"

        if kind is None:
            return CheckpointTrigger(False, "verification did not cross an automatic checkpoint trigger", verifier_report_id=report_id, task_id=task_id)

        signal = ChangeSignal(
            kind=kind,
            summary=reason,
            seed_nodes=[task_id] if task_id else [],
            evidence_ids=list(report.get("evidence_ids", []) or []),
            source="verifier",
            metadata={
                "verifier_report_id": report_id,
                "policy_recommendation": report.get("policy_recommendation"),
                "findings": list(report.get("findings", []) or []),
            },
        )
        return CheckpointTrigger(True, reason, signal, report_id, task_id)
