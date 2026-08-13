from copy import deepcopy
from .reuse_model import ReuseRequest,reuse_contract
from .reuse_validation import validate_reuse_candidate

class ReuseLookupRuntimeMixin:
    def _invalid_reuse_source_ids(self):
        invalid=set()
        for aid,entry in self.reasoning_report().get("artifacts",{}).items():
            if entry.get("state") in {"STALE","REFUTED","REJECTED"}: invalid.add(str(aid))
        for mid,entry in self.hierarchical_memory_report().get("memories",{}).items():
            if entry.get("status") in {"STALE","REFUTED","REJECTED","REVOKED","EXPIRED"}: invalid.add(str(mid))
        return invalid
    def lookup_reuse(self,request,*,subsumption_validator=None):
        request=request if isinstance(request,ReuseRequest) else ReuseRequest(**deepcopy(dict(request)))
        candidates=self._reuse_hot_index().candidates(request) or self._durable_reuse_candidates(request.kind)
        rejected=[]
        for candidate in candidates:
            if not self._candidate_registration_evidence_id(candidate.fingerprint): continue
            validation=validate_reuse_candidate(request,candidate,scope_state=self._begin_calculus()["scope_state"],invalid_source_ids=self._invalid_reuse_source_ids(),subsumption_validator=subsumption_validator)
            if validation.usable: return {"contract":reuse_contract(),"hit":True,"request":request.to_dict(),"candidate":candidate.to_dict(),"validation":validation.to_dict(),"certificate":None,"rejections":rejected}
            rejected.append({"candidate_fingerprint":candidate.fingerprint,"reasons":list(validation.reasons)})
        return {"contract":reuse_contract(),"hit":False,"request":request.to_dict(),"candidate":None,"validation":None,"certificate":None,"rejections":rejected}
