from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping
from .semantic_result import semantic_fingerprint
from ._semantic_projection_core import (
    SEMANTIC_EQUIVALENCE_CONTRACT_ID, SEMANTIC_EQUIVALENCE_CONTRACT_VERSION,
    EQUIVALENCE_RELATIONS, PROJECTION_FIDELITIES, PROJECTION_STATUSES,
    REVISION_RELATIONS, SemanticSubjectRef, SemanticProjectionDefinition,
    _req, _opt, _sha, _uniq, _roundtrip,
)

@dataclass(frozen=True)
class SemanticProjectionResult:
    projection_id: str
    projection_fingerprint: str
    subject: SemanticSubjectRef | Mapping[str, Any]
    status: str
    projected_fingerprint: str = ""
    evidence_ids: tuple[str, ...] = ()
    diagnostics: tuple[str, ...] = ()
    result_id: str = ""
    def __post_init__(self):
        pid, pfp = _req("projection result projection_id", self.projection_id), _sha("projection result projection_fingerprint", self.projection_fingerprint)
        subject = self.subject if isinstance(self.subject, SemanticSubjectRef) else SemanticSubjectRef.from_dict(self.subject); status = _req("projection result status", self.status).upper()
        if status not in PROJECTION_STATUSES: raise ValueError(f"unsupported semantic projection result status: {status}")
        projected = _opt(self.projected_fingerprint)
        if status == "PROJECTED": projected = _sha("projection result projected_fingerprint", projected)
        elif projected: raise ValueError("UNSUPPORTED/INDETERMINATE projection result cannot carry a projected_fingerprint")
        evidence, diagnostics = _uniq(self.evidence_ids), _uniq(self.diagnostics)
        if status != "PROJECTED" and not diagnostics: raise ValueError("non-PROJECTED semantic projection result requires diagnostics")
        for k, v in (("projection_id", pid), ("projection_fingerprint", pfp), ("subject", subject), ("status", status), ("projected_fingerprint", projected), ("evidence_ids", evidence), ("diagnostics", diagnostics)): object.__setattr__(self, k, v)
        derived = f"semantic-projection-result-{semantic_fingerprint(self.identity_payload())[:24]}"; supplied = _opt(self.result_id)
        if supplied and supplied != derived: raise ValueError("semantic projection result_id does not match canonical identity")
        object.__setattr__(self, "result_id", derived)
    def identity_payload(self): return {"projection_id": self.projection_id, "projection_fingerprint": self.projection_fingerprint, "subject": self.subject.identity_payload(), "status": self.status, "projected_fingerprint": self.projected_fingerprint, "evidence_ids": list(self.evidence_ids), "diagnostics": list(self.diagnostics)}
    @property
    def fingerprint(self): return semantic_fingerprint({"result_id": self.result_id, **self.identity_payload()})
    def to_dict(self): return {"record_type": "PROJECTION_RESULT", "result_id": self.result_id, **self.identity_payload(), "fingerprint": self.fingerprint}
    @classmethod
    def from_dict(cls, v): return _roundtrip(cls, v, ("evidence_ids", "diagnostics"))

@dataclass(frozen=True)
class SemanticEquivalenceAssessment:
    projection_id: str
    projection_fingerprint: str
    left_result_id: str
    left_result_fingerprint: str
    right_result_id: str
    right_result_fingerprint: str
    left_subject: SemanticSubjectRef | Mapping[str, Any]
    right_subject: SemanticSubjectRef | Mapping[str, Any]
    relation: str
    projection_fidelity: str
    revision_relation: str
    diagnostics: tuple[str, ...] = ()
    assessment_id: str = ""
    contract_id: str = SEMANTIC_EQUIVALENCE_CONTRACT_ID
    contract_version: str = SEMANTIC_EQUIVALENCE_CONTRACT_VERSION
    def __post_init__(self):
        if self.contract_id != SEMANTIC_EQUIVALENCE_CONTRACT_ID or self.contract_version != SEMANTIC_EQUIVALENCE_CONTRACT_VERSION: raise ValueError("unsupported semantic equivalence contract")
        vals = {"projection_id": _req("equivalence projection_id", self.projection_id), "projection_fingerprint": _sha("equivalence projection_fingerprint", self.projection_fingerprint), "left_result_id": _req("left_result_id", self.left_result_id), "left_result_fingerprint": _sha("left_result_fingerprint", self.left_result_fingerprint), "right_result_id": _req("right_result_id", self.right_result_id), "right_result_fingerprint": _sha("right_result_fingerprint", self.right_result_fingerprint)}
        vals["left_subject"] = self.left_subject if isinstance(self.left_subject, SemanticSubjectRef) else SemanticSubjectRef.from_dict(self.left_subject); vals["right_subject"] = self.right_subject if isinstance(self.right_subject, SemanticSubjectRef) else SemanticSubjectRef.from_dict(self.right_subject)
        vals["relation"] = _req("equivalence relation", self.relation).upper(); vals["projection_fidelity"] = _req("equivalence projection_fidelity", self.projection_fidelity).upper(); vals["revision_relation"] = _req("equivalence revision_relation", self.revision_relation).upper(); vals["diagnostics"] = _uniq(self.diagnostics)
        if vals["relation"] not in EQUIVALENCE_RELATIONS: raise ValueError(f"unsupported semantic equivalence relation: {vals['relation']}")
        if vals["projection_fidelity"] not in PROJECTION_FIDELITIES: raise ValueError("invalid semantic equivalence projection_fidelity")
        if vals["revision_relation"] not in REVISION_RELATIONS: raise ValueError("invalid semantic equivalence revision_relation")
        for k, v in vals.items(): object.__setattr__(self, k, v)
        derived = f"semantic-equivalence-{semantic_fingerprint(self.identity_payload())[:24]}"; supplied = _opt(self.assessment_id)
        if supplied and supplied != derived: raise ValueError("semantic equivalence assessment_id does not match canonical identity")
        object.__setattr__(self, "assessment_id", derived)
    def identity_payload(self): return {"contract_id": self.contract_id, "contract_version": self.contract_version, "projection_id": self.projection_id, "projection_fingerprint": self.projection_fingerprint, "left_result_id": self.left_result_id, "left_result_fingerprint": self.left_result_fingerprint, "right_result_id": self.right_result_id, "right_result_fingerprint": self.right_result_fingerprint, "left_subject": self.left_subject.identity_payload(), "right_subject": self.right_subject.identity_payload(), "relation": self.relation, "projection_fidelity": self.projection_fidelity, "revision_relation": self.revision_relation, "diagnostics": list(self.diagnostics)}
    @property
    def fingerprint(self): return semantic_fingerprint({"assessment_id": self.assessment_id, **self.identity_payload()})
    def to_dict(self): return {"record_type": "EQUIVALENCE_ASSESSMENT", "assessment_id": self.assessment_id, **self.identity_payload(), "fingerprint": self.fingerprint}
    @classmethod
    def from_dict(cls, v): return _roundtrip(cls, v, ("diagnostics",))

def _validate(defn, result):
    if result.projection_id != defn.projection_id: raise ValueError("semantic projection result projection_id does not match definition")
    if result.projection_fingerprint != defn.fingerprint: raise ValueError("semantic projection result projection fingerprint does not match definition")
    if result.subject.semantic_type_id not in defn.source_type_ids: raise ValueError("semantic projection subject type is not admitted by projection definition")
def _rev(a, b):
    if not a.revision_bound and not b.revision_bound: return "UNBOUND"
    if a.revision_bound != b.revision_bound: return "DIFFERENT"
    return "SAME" if (a.revision_id, a.revision_fingerprint) == (b.revision_id, b.revision_fingerprint) else "DIFFERENT"
def assess_semantic_equivalence(definition, left, right):
    _validate(definition, left); _validate(definition, right)
    left, right = sorted((left, right), key=lambda x: (x.subject.semantic_type_id, x.subject.object_id, x.subject.fingerprint, x.subject.revision_id, x.subject.revision_fingerprint, x.result_id))
    rr, d = _rev(left.subject, right.subject), []
    if left.subject.identity_payload() == right.subject.identity_payload(): relation = "EXACT_IDENTITY"; d.append("same semantic type, object identity, fingerprint, and revision binding")
    elif "UNSUPPORTED" in {left.status, right.status}: relation = "UNSUPPORTED"; d.append("at least one projection result is explicitly unsupported")
    elif "INDETERMINATE" in {left.status, right.status}: relation = "INDETERMINATE"; d.append("at least one projection result is indeterminate")
    elif definition.revision_policy == "EXACT_MATCH_REQUIRED" and rr == "DIFFERENT": relation = "INDETERMINATE"; d.append("projection contract requires exact source revision match")
    elif left.projected_fingerprint == right.projected_fingerprint:
        relation = "PROJECTION_EQUIVALENT"; d.append("projected fingerprints match under the exact explicit projection")
        if definition.fidelity == "LOSSY": d.append("projection is lossy; equivalence is limited to preserved semantics")
    else: relation = "NON_EQUIVALENT"; d.append("projected fingerprints differ under the exact explicit projection")
    return SemanticEquivalenceAssessment(definition.projection_id, definition.fingerprint, left.result_id, left.fingerprint, right.result_id, right.fingerprint, left.subject, right.subject, relation, definition.fidelity, rr, tuple(d))
