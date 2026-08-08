from __future__ import annotations
from copy import deepcopy
from dataclasses import dataclass, field, asdict
from typing import Any

from .model import new_id, now


@dataclass
class EvidenceRecord:
    kind: str
    statement: str
    source: str = ""
    confidence: float | None = None
    supports: list[str] = field(default_factory=list)
    contradicts: list[str] = field(default_factory=list)
    derived_from: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    status: str = "active"
    evidence_id: str = field(default_factory=lambda: new_id("evidence"))
    created_at: float = field(default_factory=now)
    invalidated_at: float | None = None
    invalidated_reason: str | None = None


class EvidenceLedger:
    def __init__(self, initial=None):
        initial = initial or {}
        records = initial.get("records", [])
        self._records = {raw["evidence_id"]: EvidenceRecord(**deepcopy(raw)) for raw in records}

    def add(self, record: EvidenceRecord):
        if record.evidence_id in self._records:
            raise ValueError(f"Evidence record already exists: {record.evidence_id}")
        missing = [x for x in record.derived_from + record.supports + record.contradicts if x not in self._records]
        if missing:
            raise KeyError(f"Unknown evidence references: {missing}")
        self._records[record.evidence_id] = deepcopy(record)
        return deepcopy(record)

    def get(self, evidence_id: str):
        if evidence_id not in self._records:
            raise KeyError(evidence_id)
        return deepcopy(self._records[evidence_id])

    def invalidate(self, evidence_id: str, reason: str):
        record = self.get(evidence_id)
        record.status = "invalidated"
        record.invalidated_at = now()
        record.invalidated_reason = reason
        self._records[evidence_id] = deepcopy(record)
        return record

    def lineage(self, evidence_id: str):
        if evidence_id not in self._records:
            raise KeyError(evidence_id)
        out = []
        seen = set()

        def visit(eid):
            if eid in seen:
                return
            seen.add(eid)
            record = self._records[eid]
            for parent in record.derived_from:
                visit(parent)
            out.append(deepcopy(record))

        visit(evidence_id)
        return out

    def to_dict(self):
        records = [asdict(record) for record in self._records.values()]
        categories = {"claims": [], "observations": [], "contradictions": [], "assumptions": []}
        mapping = {"claim": "claims", "observation": "observations", "contradiction": "contradictions", "assumption": "assumptions"}
        for record in records:
            bucket = mapping.get(record["kind"])
            if bucket:
                categories[bucket].append(record["evidence_id"])
        categories["records"] = records
        return categories

    @classmethod
    def from_dict(cls, data):
        return cls(data)
