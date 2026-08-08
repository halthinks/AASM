from __future__ import annotations
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Iterable
import hashlib, json, time, uuid

class MachineState(str, Enum):
    INGEST="INGEST"; FORMALIZE="FORMALIZE"; CLASSIFY="CLASSIFY"; DECOMPOSE="DECOMPOSE"
    PLAN="PLAN"; SELECT="SELECT"; EXECUTE="EXECUTE"; OBSERVE="OBSERVE"; VERIFY="VERIFY"
    REPAIR="REPAIR"; BACKTRACK="BACKTRACK"; INVESTIGATE="INVESTIGATE"; COMMIT="COMMIT"
    PAUSE="PAUSE"; COMPLETE="COMPLETE"; FAIL="FAIL"

class EventType(str, Enum):
    MACHINE_CREATED="machine_created"; MACHINE_FORKED="machine_forked"; TRANSITION_COMMITTED="transition_committed"; SNAPSHOT_PATCHED="snapshot_patched"
    CHECKPOINT_CREATED="checkpoint_created"; CHECKPOINT_RESTORED="checkpoint_restored"
    GOAL_RECEIVED="goal_received"; PROPOSAL="proposal"; AUTHORIZED="authorized"; RESULT="result"
    TEST_PASSED="test_passed"; TEST_FAILED="test_failed"; INVARIANT_FAILED="invariant_failed"
    ASSUMPTION_INVALIDATED="assumption_invalidated"; DEPENDENCY_DISCOVERED="dependency_discovered"
    BETTER_PATH_FOUND="better_path_found"; RESOURCE_EXHAUSTED="resource_exhausted"
    USER_INTERRUPT="user_interrupt"; ACCEPTANCE_SATISFIED="acceptance_satisfied"
    EFFECT_PROPOSED="effect_proposed"; EFFECT_AUTHORIZED="effect_authorized"
    EFFECT_STARTED="effect_started"; EFFECT_SUCCEEDED="effect_succeeded"; EFFECT_FAILED="effect_failed"
    EFFECT_UNKNOWN="effect_unknown"; EFFECT_CANCELLED="effect_cancelled"; EFFECT_RECONCILED="effect_reconciled"
    PLAN_NODE_ADDED="plan_node_added"; PLAN_EDGE_ADDED="plan_edge_added"; PLAN_NODE_UPDATED="plan_node_updated"; PLAN_NODE_PRUNED="plan_node_pruned"
    MEMORY_PUT="memory_put"; MEMORY_INVALIDATED="memory_invalidated"
    EVIDENCE_ADDED="evidence_added"; EVIDENCE_INVALIDATED="evidence_invalidated"
    RESOURCE_REGISTERED="resource_registered"; RESOURCE_UPDATED="resource_updated"; SCHEDULE_COMPUTED="schedule_computed"
    WORKER_REGISTERED="worker_registered"; WORKER_UPDATED="worker_updated"; WORKER_HEARTBEAT="worker_heartbeat"
    QUOTA_SET="quota_set"; LEASE_CLAIMED="lease_claimed"; LEASE_HEARTBEAT="lease_heartbeat"
    LEASE_COMPLETED="lease_completed"; LEASE_FAILED="lease_failed"; LEASE_RELEASED="lease_released"; LEASE_EXPIRED="lease_expired"

@dataclass(frozen=True)
class CapabilitySet:
    values: frozenset[str] = frozenset()
    def supports(self, required: Iterable[str]) -> bool: return set(required).issubset(self.values)

@dataclass
class ProblemSpec:
    goal: str
    objective: dict[str, Any] = field(default_factory=dict)
    constraints: list[dict[str, Any]] = field(default_factory=list)
    invariants: list[dict[str, Any]] = field(default_factory=list)
    acceptance_tests: list[dict[str, Any]] = field(default_factory=list)
    features: dict[str, Any] = field(default_factory=dict)

@dataclass
class TaskEnvelope:
    task_id: str
    description: str
    required_capabilities: list[str] = field(default_factory=list)
    payload: dict[str, Any] = field(default_factory=dict)
    reversible: bool = True
    cost: float = 1.0

@dataclass
class Proposal:
    agent_id: str
    action: str
    payload: dict[str, Any] = field(default_factory=dict)
    requested_transition: str | None = None
    rationale: str = ""
    reversible: bool = True

@dataclass
class AuthorizedAction:
    proposal: Proposal
    authorization_id: str
    authority: str

@dataclass
class Result:
    agent_id: str
    ok: bool
    output: dict[str, Any] = field(default_factory=dict)
    evidence: list[str] = field(default_factory=list)
    error: str | None = None

@dataclass
class Event:
    event_id: str
    ts: float
    event_type: str
    from_state: str | None
    to_state: str | None
    reason: str
    evidence: list[str] = field(default_factory=list)
    data: dict[str, Any] = field(default_factory=dict)
    machine_id: str = ""
    sequence: int = 0
    schema_version: int = 1

@dataclass
class MachineSnapshot:
    machine_id: str
    version: int
    state: str
    problem: ProblemSpec
    graph: dict[str, Any] = field(default_factory=lambda:{"nodes":[],"edges":[]})
    frontier: list[str] = field(default_factory=list)
    visited: list[str] = field(default_factory=list)
    pruned: list[str] = field(default_factory=list)
    memory: dict[str, Any] = field(default_factory=dict)
    resources: dict[str, Any] = field(default_factory=dict)
    evidence: dict[str, Any] = field(default_factory=lambda:{"claims":[],"observations":[],"contradictions":[],"assumptions":[],"records":[]})
    metadata: dict[str, Any] = field(default_factory=dict)

    def canonical_hash(self) -> str:
        payload = asdict(self)
        payload.pop("version", None)
        raw=json.dumps(payload, sort_keys=True, separators=(",",":"), default=str).encode()
        return hashlib.sha256(raw).hexdigest()


def new_id(prefix: str) -> str: return f"{prefix}_{uuid.uuid4().hex[:12]}"
def now() -> float: return time.time()
