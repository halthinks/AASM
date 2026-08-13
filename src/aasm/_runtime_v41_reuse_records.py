from __future__ import annotations
from copy import deepcopy
import json
from .evidence import EvidenceRecord
from .reuse_index import HotReuseIndex
from .reuse_model import CanonicalRef,ReuseCandidate,REUSE_CONTRACT_ID,reuse_contract
from .semantic_result import canonical_semantic_json,semantic_fingerprint

class ReuseRecordRuntimeMixin:
    def _reuse_hot_index(self):
        index=getattr(self,"__aasm_reuse_hot_index",None)
        if index is None: index=HotReuseIndex(); setattr(self,"__aasm_reuse_hot_index",index)
        return index
    def reuse_contract_report(self): return reuse_contract()
    def _reuse_records(self):
        return [deepcopy(row) for row in self.snapshot.evidence.get("records",[]) if (row.get("metadata") or {}).get("reuse_record_type") in {"CANDIDATE","CERTIFICATE","METRICS"}]
    def _canonical_ref_valid(self,source):
        current=self.canonical_reuse_ref(source.ref_type,source.ref_id,privacy_level=source.privacy_level,privacy_principal_id=source.privacy_principal_id)
        if current.fingerprint!=source.fingerprint or current.scope_id!=source.scope_id: raise ValueError("reuse source does not match canonical object")
    def _candidate_from_statement(self,statement):
        raw=json.loads(statement); source=CanonicalRef(**raw.pop("source")); raw.pop("fingerprint",None); return ReuseCandidate(source=source,**raw)
    def register_reuse_candidate(self,candidate,*,authority_id,authority_class,reason="reuse candidate indexed"):
        if authority_class not in {"POLICY","CONTROLLER"}: raise PermissionError("reuse candidate admission requires POLICY or CONTROLLER authority")
        if not isinstance(candidate,ReuseCandidate):
            raw=deepcopy(dict(candidate)); source=raw.pop("source"); source=source if isinstance(source,CanonicalRef) else CanonicalRef(**source); raw.pop("fingerprint",None); candidate=ReuseCandidate(source=source,**raw)
        self._canonical_ref_valid(candidate.source)
        for row in self._reuse_records():
            if (row.get("metadata") or {}).get("candidate_fingerprint")==candidate.fingerprint:
                self._reuse_hot_index().add(candidate); return {"contract":reuse_contract(),"candidate":candidate.to_dict(),"evidence_id":row.get("evidence_id"),"already_registered":True}
        stored=self.add_evidence(EvidenceRecord(kind="reuse_candidate",statement=canonical_semantic_json(candidate.to_dict()),source=REUSE_CONTRACT_ID,metadata={"reuse_record_type":"CANDIDATE","reuse_contract_id":REUSE_CONTRACT_ID,"candidate_fingerprint":candidate.fingerprint,"source_ref_id":candidate.source.ref_id,"authority_id":authority_id,"authority_class":authority_class,"scope_id":candidate.source.scope_id}),reason=reason)
        self._reuse_hot_index().add(candidate)
        return {"contract":reuse_contract(),"candidate":candidate.to_dict(),"evidence_id":stored.evidence_id,"already_registered":False}
    def _durable_reuse_candidates(self,kind):
        out=[]
        for row in self._reuse_records():
            if (row.get("metadata") or {}).get("reuse_record_type")!="CANDIDATE": continue
            try: candidate=self._candidate_from_statement(str(row.get("statement") or "{}"))
            except Exception: continue
            if candidate.kind==kind: out.append(candidate); self._reuse_hot_index().add(candidate)
        return sorted(out,key=lambda row:row.fingerprint)
    def _candidate_registration_evidence_id(self,fingerprint):
        for row in self._reuse_records():
            if (row.get("metadata") or {}).get("candidate_fingerprint")==fingerprint: return str(row.get("evidence_id") or "")
        return ""
