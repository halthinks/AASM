from dataclasses import asdict
from .reuse_model import ReuseRequest
from .semantic_result import semantic_fingerprint
from .solver_loop import solver_loop_contract
from .solver_types import SolverStepRequest,SolverStepResult

class SolverLoopRuntimeMixin:
    def solver_loop_contract_report(self): return solver_loop_contract()
    def solver_step(self,request,*,reuse_request=None):
        request=request if isinstance(request,SolverStepRequest) else SolverStepRequest(**dict(request)); request_fp=semantic_fingerprint(asdict(request))
        if request.obligation_id:
            obligation=self._begin_calculus()["obligations"].get(request.obligation_id)
            if obligation is None: raise KeyError(request.obligation_id)
            if obligation.get("status") in {"COMMITTED","REJECTED","SUPERSEDED","IMPOSSIBLE"}: return asdict(SolverStepResult(request_fp,"CHECK_COMPLETION","NO_WORK","TERMINAL_OBLIGATION",request.obligation_id,"",{"status":obligation.get("status")}))
        if reuse_request is not None:
            lookup=self.lookup_reuse(reuse_request if isinstance(reuse_request,ReuseRequest) else ReuseRequest(**dict(reuse_request)))
            if lookup["hit"]:
                committed=self.commit_reuse_certificate(lookup,actor_id="solver-loop",authority_class="CONTROLLER")
                return asdict(SolverStepResult(request_fp,"REUSE","REUSED","SKIP_EXECUTION",request.obligation_id,committed["certificate"]["certificate_id"],{"certificate_evidence_id":committed["evidence_id"]}))
        if request.obligation_id:
            status=self._begin_calculus()["obligations"][request.obligation_id].get("status")
            action="ENABLE_OBLIGATION" if status=="AVAILABLE" else "ROUTE_CAPABILITY"; phase="OBLIGATION" if status=="AVAILABLE" else "CAPABILITY_ROUTE"
            return asdict(SolverStepResult(request_fp,phase,"READY" if status=="AVAILABLE" else "EXECUTION_REQUIRED",action,request.obligation_id,"",{"status":status,"capability_id":request.capability_id}))
        frontier=self.reasoning_frontier({"scope_id":request.scope_id}); rows=frontier.get("obligations",[])
        if rows:
            selected=sorted(rows,key=lambda row:str(row.get("obligation_id")))[0]
            return asdict(SolverStepResult(request_fp,"FRONTIER","WORK_AVAILABLE","SELECT_OBLIGATION",str(selected.get("obligation_id"))))
        return asdict(SolverStepResult(request_fp,"CHECK_COMPLETION","QUIESCENT","NO_OPEN_OBLIGATION"))
