from .reuse_model import CanonicalRef
from .semantic_result import semantic_fingerprint

class ReuseReferenceRuntimeMixin:
    def canonical_reuse_ref(self,ref_type,ref_id,*,privacy_level="PUBLIC",privacy_principal_id=""):
        if ref_type=="EVIDENCE":
            row=next((r for r in self.snapshot.evidence.get("records",[]) if str(r.get("evidence_id"))==ref_id),None)
            if row is None: raise KeyError(ref_id)
            scope=str((row.get("metadata") or {}).get("scope_id") or "root")
            return CanonicalRef(ref_type,ref_id,semantic_fingerprint(row),scope,privacy_level,privacy_principal_id)
        if ref_type=="REASONING_ARTIFACT":
            entry=self.reasoning_report().get("artifacts",{}).get(ref_id)
            if entry is None: raise KeyError(ref_id)
            artifact=entry["artifact"]; scope=str((artifact.get("scope") or {}).get("scope_id") or "root")
            return CanonicalRef(ref_type,ref_id,str(artifact["fingerprint"]),scope,privacy_level,privacy_principal_id)
        if ref_type=="MEMORY":
            entry=self.hierarchical_memory_report().get("memories",{}).get(ref_id)
            if entry is None: raise KeyError(ref_id)
            memory=entry["memory"]; meta=memory.get("metadata") or {}; level=str(memory.get("privacy_level") or privacy_level); principal=str(meta.get("privacy_principal_id") or privacy_principal_id)
            return CanonicalRef(ref_type,ref_id,str(memory["fingerprint"]),str(memory.get("scope_id") or "root"),level,principal)
        raise ValueError(f"unsupported canonical reuse source type: {ref_type}")
