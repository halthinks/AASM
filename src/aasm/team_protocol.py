from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class TeamRole(str, Enum):
    PLANNER = "PLANNER"
    BUILDER = "BUILDER"
    VERIFIER = "VERIFIER"


class PlannerDirective(str, Enum):
    CONTINUE = "CONTINUE"
    REPAIR = "REPAIR"
    INVESTIGATE = "INVESTIGATE"
    PAUSE = "PAUSE"
    PLAN_INTERRUPT = "PLAN_INTERRUPT"


@dataclass
class TeamMember:
    member_id: str
    role: str
    capabilities: list[str] = field(default_factory=list)
    enabled: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.member_id:
            raise ValueError("member_id is required")
        if self.role not in {x.value for x in TeamRole}:
            raise ValueError(f"invalid team role: {self.role}")
        self.capabilities = sorted(set(self.capabilities))


@dataclass
class BuilderOutput:
    builder_id: str
    task_id: str
    summary: str
    output: dict[str, Any] = field(default_factory=dict)
    evidence_ids: list[str] = field(default_factory=list)
    changed_files: list[str] = field(default_factory=list)
    tests: dict[str, Any] = field(default_factory=dict)
    assumptions: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.builder_id or not self.task_id:
            raise ValueError("builder_id and task_id are required")


@dataclass
class VerifierReport:
    verifier_id: str
    task_id: str
    builder_output_id: str
    recommendation: str
    accepted: bool = False
    tests_passed: bool | None = None
    assumption_changed: bool = False
    unexpected_output: bool = False
    blocking: bool = False
    evidence_ids: list[str] = field(default_factory=list)
    findings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.verifier_id or not self.task_id or not self.builder_output_id:
            raise ValueError("verifier_id, task_id, and builder_output_id are required")
        if self.recommendation not in {x.value for x in PlannerDirective}:
            raise ValueError(f"invalid recommendation: {self.recommendation}")


@dataclass
class PlannerDecision:
    planner_id: str
    task_id: str
    directive: str
    reason: str
    verifier_report_id: str | None = None
    plan_revision_before: int = 0
    plan_revision_after: int = 0
    plan_patch: dict[str, Any] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.planner_id or not self.task_id:
            raise ValueError("planner_id and task_id are required")
        if self.directive not in {x.value for x in PlannerDirective}:
            raise ValueError(f"invalid directive: {self.directive}")
        if not self.reason:
            raise ValueError("planner decision reason is required")

    def to_dict(self):
        return asdict(self)


class PlannerBuilderVerifierPolicy:
    """Role and directive invariants for the executable PBV profile."""

    @staticmethod
    def member(members: list[dict[str, Any]], member_id: str) -> dict[str, Any]:
        item = next((x for x in members if x.get("member_id") == member_id), None)
        if item is None:
            raise KeyError(member_id)
        if not item.get("enabled", True):
            raise PermissionError(f"team member is disabled: {member_id}")
        return item

    @classmethod
    def require_role(cls, members: list[dict[str, Any]], member_id: str, role: str):
        item = cls.member(members, member_id)
        if item.get("role") != role:
            raise PermissionError(f"{member_id} has role {item.get('role')}, requires {role}")
        return item

    @staticmethod
    def validate_plan_change(directive: str, plan_patch: dict[str, Any] | None):
        if plan_patch is not None and directive != PlannerDirective.PLAN_INTERRUPT.value:
            raise ValueError("authoritative plan mutation requires PLAN_INTERRUPT")
        if directive == PlannerDirective.PLAN_INTERRUPT.value and not plan_patch:
            raise ValueError("PLAN_INTERRUPT requires an explicit plan_patch")

    @staticmethod
    def recommended_directive(report: VerifierReport) -> str:
        # The verifier does not authorize the response; this provides a deterministic
        # recommendation that the Planner must still accept or override explicitly.
        if report.blocking:
            return PlannerDirective.PAUSE.value
        if report.assumption_changed or report.unexpected_output:
            return PlannerDirective.PLAN_INTERRUPT.value
        if report.tests_passed is False:
            return PlannerDirective.REPAIR.value
        if not report.accepted:
            return PlannerDirective.INVESTIGATE.value
        return PlannerDirective.CONTINUE.value
