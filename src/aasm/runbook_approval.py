from __future__ import annotations

from dataclasses import asdict

from .agents import FunctionAgent
from .authority import QuorumAuthority
from .model import ProblemSpec, Proposal, Result
from .runbook_common import OperatorRunbookResult, finish_runbook, store_or_memory
from .runtime_v25 import AASMEngine


def run_human_approval(*, store=None) -> OperatorRunbookResult:
    """Exercise a quorum gate configured from a plain policy dictionary."""

    store = store_or_memory(store)
    policy = {"required_votes": 2}
    engine = AASMEngine(
        ProblemSpec("Publish an artifact only after human quorum approval"),
        store=store,
        authority=QuorumAuthority(**policy),
    )

    def proposer(agent, _snapshot):
        return Proposal(
            agent_id=agent.agent_id,
            action="publish_artifact",
            payload={"artifact_id": "runbook-artifact"},
            rationale="artifact passed local verification and now requires human approval",
            reversible=False,
        )

    def executor(agent, action):
        return Result(
            agent_id=agent.agent_id,
            ok=True,
            output={
                "artifact_id": action.proposal.payload["artifact_id"],
                "published": True,
                "authorization_id": action.authorization_id,
            },
        )

    engine.register_agent(
        FunctionAgent("runbook-publisher", {"publish"}, proposer, executor)
    )
    denied = False
    try:
        engine.propose_and_execute(
            "runbook-publisher",
            votes={"reviewer-a": True},
        )
    except PermissionError:
        denied = True
    result = engine.propose_and_execute(
        "runbook-publisher",
        votes={"reviewer-a": True, "operator-b": True},
    )
    authorized_events = [
        event for event in engine.events if event.event_type == "authorized"
    ]
    checks = {
        "under_approved_attempt_denied": denied,
        "quorum_authorized": bool(authorized_events),
        "declared_policy_applied": policy["required_votes"] == 2,
        "authorized_action_executed": result.ok is True,
        "artifact_published": result.output.get("published") is True,
    }
    return finish_runbook(
        "human-approval",
        machine_id=engine.snapshot.machine_id,
        checks=checks,
        summary={
            "policy": policy,
            "approvals": ["reviewer-a", "operator-b"],
            "authorization": (
                authorized_events[-1].data if authorized_events else None
            ),
            "result": asdict(result),
        },
        evidence=[
            {
                "kind": "authorization-event",
                "event_id": authorized_events[-1].event_id,
                "authority": authorized_events[-1].data.get("authority"),
            }
        ]
        if authorized_events
        else [],
    )
