from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Mapping

from .calculus import DecisionRecord, ObligationRecord
from .hierarchical_memory import MEMORY_OPERATIONS, MemoryObject
from .semantic_result import semantic_fingerprint


@dataclass
class MemoryOperationDecision(DecisionRecord):
    operation: str = "STORE"
    memory_id: str = ""
    target_memory_ids: list[str] = field(default_factory=list)
    proposed_memory: dict[str, Any] | None = None
    proposer_id: str = ""

    def __post_init__(self):
        super().__post_init__()
        if self.operation not in MEMORY_OPERATIONS:
            raise ValueError(f"invalid memory operation: {self.operation}")
        if not self.memory_id or not self.proposer_id:
            raise ValueError("memory operation requires memory_id and proposer_id")
        self.target_memory_ids = sorted(set(map(str, self.target_memory_ids)))
        if self.operation != "FORGET" and not self.proposed_memory:
            raise ValueError("non-forget memory operation requires proposed_memory")
        if self.proposed_memory is not None:
            parsed = MemoryObject.from_dict(deepcopy(self.proposed_memory))
            if parsed.memory_id != self.memory_id:
                raise ValueError("memory operation decision memory_id mismatch")
            self.proposed_memory = parsed.to_dict()

    @property
    def operation_fingerprint(self) -> str:
        return semantic_fingerprint(self.to_dict())


@dataclass
class MemoryOperationObligation(ObligationRecord):
    operation: str = "STORE"
    memory_id: str = ""
    memory_decision_id: str = ""
    privacy_level: str = "AGENT"
    retention_policy: str = "permanent"

    def __post_init__(self):
        super().__post_init__()
        if self.operation not in MEMORY_OPERATIONS:
            raise ValueError(f"invalid memory operation: {self.operation}")
        if not self.memory_id or not self.memory_decision_id:
            raise ValueError("memory obligation requires memory and decision IDs")


def memory_decision_id(operation: str, memory_id: str, proposer_id: str, payload: Mapping[str, Any] | None = None) -> str:
    return "memory-decision-" + semantic_fingerprint({"operation": operation, "memory_id": memory_id, "proposer_id": proposer_id, "payload": deepcopy(dict(payload or {}))})[:20]


def memory_obligation_id(decision_id: str) -> str:
    return "memory-obligation-" + semantic_fingerprint(decision_id)[:20]


__all__ = ["MemoryOperationDecision", "MemoryOperationObligation", "memory_decision_id", "memory_obligation_id"]
