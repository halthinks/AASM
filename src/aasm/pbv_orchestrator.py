from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Callable

from .team_protocol import BuilderOutput, PlannerDecision, PlannerDirective, VerifierReport


@dataclass
class PBVCycleResult:
    builder_output: dict[str, Any]
    verifier_report: dict[str, Any]
    planner_decision: dict[str, Any]

    def to_dict(self):
        return asdict(self)


class PBVCoordinator:
    """Executable Builder -> Verifier -> Planner handoff.

    The verifier and planner are callables so they may be backed by AASM model
    executors, local agents, remote services, humans, or tests. Only the final
    PlannerDecision crosses the engine's authoritative plan-mutation boundary.
    """

    def __init__(
        self,
        engine,
        verifier: Callable[[dict[str, Any]], VerifierReport | dict[str, Any]],
        planner: Callable[[dict[str, Any]], PlannerDecision | dict[str, Any]],
    ):
        self.engine = engine
        self.verifier = verifier
        self.planner = planner

    @staticmethod
    def _verifier_record(value, *, task_id: str, builder_output_id: str):
        if isinstance(value, VerifierReport):
            record = value
        else:
            raw = dict(value)
            raw.setdefault("task_id", task_id)
            raw.setdefault("builder_output_id", builder_output_id)
            record = VerifierReport(**raw)
        if record.task_id != task_id or record.builder_output_id != builder_output_id:
            raise ValueError("Verifier response does not reference the current Builder output")
        return record

    @staticmethod
    def _planner_record(value, *, planner_id: str, task_id: str, verifier_report_id: str):
        if isinstance(value, PlannerDecision):
            record = value
        else:
            raw = dict(value)
            raw.setdefault("planner_id", planner_id)
            raw.setdefault("task_id", task_id)
            raw.setdefault("verifier_report_id", verifier_report_id)
            record = PlannerDecision(**raw)
        if record.planner_id != planner_id or record.task_id != task_id:
            raise ValueError("Planner response does not match the authoritative Planner/task")
        if record.verifier_report_id is None:
            record.verifier_report_id = verifier_report_id
        elif record.verifier_report_id != verifier_report_id:
            raise ValueError("Planner response references the wrong Verifier report")
        return record

    def process_builder_output(self, output: BuilderOutput) -> PBVCycleResult:
        built = self.engine.submit_builder_output(output)
        verifier_payload = {
            "builder_output": built,
            "plan_revision": self.engine.team_report().get("plan_revision"),
            "plan_graph": self.engine.snapshot.graph,
            "allowed_directives": [x.value for x in PlannerDirective],
            "instruction": "Verify observed output and assumptions. Recommend, but do not authorize, the next control action.",
        }
        verified = self.engine.submit_verifier_report(
            self._verifier_record(
                self.verifier(verifier_payload),
                task_id=output.task_id,
                builder_output_id=built["builder_output_id"],
            )
        )
        team = self.engine.team_report()
        checkpoint = self.engine.last_checkpoint_trigger() if hasattr(self.engine, "last_checkpoint_trigger") else None
        change_control = {
            "paused_tasks": self.engine.paused_tasks(),
            "last_impact": self.engine.last_impact(),
        } if hasattr(self.engine, "paused_tasks") else None
        fleet = self.engine.fleet_control_report() if hasattr(self.engine, "fleet_control_report") else None
        planner_payload = {
            "builder_output": built,
            "verifier_report": verified,
            "policy_recommendation": verified.get("policy_recommendation"),
            "automatic_checkpoint_trigger": checkpoint,
            "change_control": change_control,
            "fleet_control": fleet,
            "plan_revision": team.get("plan_revision"),
            "plan_graph": self.engine.snapshot.graph,
            "allowed_directives": [x.value for x in PlannerDirective],
            "instruction": "You alone own the authoritative plan. Test the new evidence against current assumptions. If an automatic checkpoint exists, resolve only nodes that are valid again. Do not mutate the plan unless PLAN_INTERRUPT includes an explicit validated plan_patch.",
        }
        decided = self.engine.planner_decide(
            self._planner_record(
                self.planner(planner_payload),
                planner_id=team["planner_id"],
                task_id=output.task_id,
                verifier_report_id=verified["verifier_report_id"],
            )
        )
        return PBVCycleResult(built, verified, decided)
