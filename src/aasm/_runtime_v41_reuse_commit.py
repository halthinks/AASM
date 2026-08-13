from copy import deepcopy
from .evidence import EvidenceRecord
from .reuse_model import REUSE_CERTIFICATE_CONTRACT_ID,REUSE_CONTRACT_ID
from .semantic_result import canonical_semantic_json

class ReuseCommitRuntimeMixin:
    def commit_reuse_certificate(self,lookup,*,actor_id,authority_class="CONTROLLER"):
        if authority_class not in {"POLICY","CONTROLLER"}: raise PermissionError("reuse certificate commit requires POLICY or CONTROLLER authority")
        if not lookup.get("hit") or not lookup.get("certificate"): raise ValueError("cannot commit reuse certificate for a miss")
        doc=deepcopy(lookup["certificate"]); source=doc["source"]
        current=self.canonical_reuse_ref(source["ref_type"],source["ref_id"],privacy_level=source.get("privacy_level","PUBLIC"),privacy_principal_id=source.get("privacy_principal_id",""))
        if current.fingerprint!=source["fingerprint"]: raise ValueError("reuse source changed before certificate commit")
        if source["ref_id"] in self._invalid_reuse_source_ids(): raise ValueError("reuse source became invalid before certificate commit")
        self._require_evidence_ids(doc.get("evidence_ids") or ())
        for row in self._reuse_records():
            if (row.get("metadata") or {}).get("certificate_id")==doc["certificate_id"]: return {"certificate":doc,"evidence_id":row.get("evidence_id"),"already_committed":True}
        stored=self.add_evidence(EvidenceRecord(kind="reuse_certificate",statement=canonical_semantic_json(doc),source=REUSE_CERTIFICATE_CONTRACT_ID,derived_from=list(doc.get("evidence_ids") or ()),metadata={"reuse_record_type":"CERTIFICATE","reuse_contract_id":REUSE_CONTRACT_ID,"certificate_id":doc["certificate_id"],"certificate_fingerprint":doc["fingerprint"],"source_ref_id":source["ref_id"],"actor_id":actor_id,"authority_class":authority_class,"scope_id":doc["scope_id"]}),reason="validated reuse committed")
        return {"certificate":doc,"evidence_id":stored.evidence_id,"already_committed":False}
