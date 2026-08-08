from __future__ import annotations
import json
from dataclasses import asdict
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from .resources import TaskDemand
from .workers import WorkerRecord
from .model_routing import ModelRouteRequest

class RemoteProtocolError(RuntimeError): pass

class AASMRemoteClient:
    """Dependency-free JSON/HTTP client for remote AASM control planes."""
    def __init__(self,base_url:str,token:str|None=None,timeout:float=30.0): self.base_url=base_url.rstrip('/'); self.token=token; self.timeout=timeout
    def _request(self,method,path,payload=None):
        data=None if payload is None else json.dumps(payload).encode(); headers={"Content-Type":"application/json","Accept":"application/json"}
        if self.token: headers["Authorization"]=f"Bearer {self.token}"
        req=Request(self.base_url+path,data=data,headers=headers,method=method)
        try:
            with urlopen(req,timeout=self.timeout) as resp:
                raw=resp.read().decode(); return json.loads(raw) if raw else {}
        except HTTPError as exc:
            if exc.code==204: return {}
            body=exc.read().decode(errors='replace'); raise RemoteProtocolError(f"HTTP {exc.code}: {body}") from exc
    @staticmethod
    def _payload(value): return asdict(value) if hasattr(value,"__dataclass_fields__") else dict(value)
    def health(self): return self._request("GET","/health")
    def create_machine(self,problem:dict): return self._request("POST","/v1/machines",{"problem":problem})
    def state(self,machine_id): return self._request("GET",f"/v1/machines/{machine_id}/state")
    def team(self,machine_id): return self._request("GET",f"/v1/machines/{machine_id}/team")
    def collaboration(self,machine_id): return self._request("GET",f"/v1/machines/{machine_id}/collaboration")
    def change_control(self,machine_id): return self._request("GET",f"/v1/machines/{machine_id}/change-control")
    def checkpoint_triggers(self,machine_id): return self._request("GET",f"/v1/machines/{machine_id}/checkpoint-triggers")
    def fleet_control(self,machine_id): return self._request("GET",f"/v1/machines/{machine_id}/fleet-control")
    def telemetry_report(self,machine_id): return self._request("GET",f"/v1/machines/{machine_id}/telemetry")
    def provisioning(self,machine_id): return self._request("GET",f"/v1/machines/{machine_id}/provisioning")
    def register_worker(self,machine_id,worker:WorkerRecord): return self._request("POST",f"/v1/machines/{machine_id}/workers/register",{"worker":asdict(worker)})
    def heartbeat(self,machine_id,worker_id): return self._request("POST",f"/v1/machines/{machine_id}/workers/{worker_id}/heartbeat",{})
    def claim(self,machine_id,worker_id,task:TaskDemand,lease_seconds=60.0): return self._request("POST",f"/v1/machines/{machine_id}/claim",{"worker_id":worker_id,"task":asdict(task),"lease_seconds":lease_seconds})
    def claim_next(self,machine_id,worker_id,lease_seconds=60.0): return self._request("POST",f"/v1/machines/{machine_id}/claim-next",{"worker_id":worker_id,"lease_seconds":lease_seconds})
    def lease_heartbeat(self,machine_id,lease_id,extend_seconds=60.0): return self._request("POST",f"/v1/machines/{machine_id}/leases/{lease_id}/heartbeat",{"extend_seconds":extend_seconds})
    def complete(self,machine_id,lease_id,result=None): return self._request("POST",f"/v1/machines/{machine_id}/leases/{lease_id}/complete",{"result":result or {}})
    def fail(self,machine_id,lease_id,error): return self._request("POST",f"/v1/machines/{machine_id}/leases/{lease_id}/fail",{"error":error})
    def route_model(self,machine_id,request:ModelRouteRequest): return self._request("POST",f"/v1/machines/{machine_id}/model-route",{"request":asdict(request)})
    def model_usage(self,machine_id,record): return self._request("POST",f"/v1/machines/{machine_id}/model-usage",{"record":self._payload(record)})
    def model_outcome(self,machine_id,record): return self._request("POST",f"/v1/machines/{machine_id}/model-outcome",{"record":self._payload(record)})
    def configure_governance_budget(self,machine_id,policy): return self._request("POST",f"/v1/machines/{machine_id}/governance-budget",{"policy":self._payload(policy)})
    def governance_decide(self,machine_id,context): return self._request("POST",f"/v1/machines/{machine_id}/governance-decision",{"context":self._payload(context)})
    def complete_governance_review(self,machine_id,decision_id,evidence=None): return self._request("POST",f"/v1/machines/{machine_id}/governance-review/{decision_id}/complete",{"evidence":list(evidence or [])})
    def initialize_team(self,machine_id,members): return self._request("POST",f"/v1/machines/{machine_id}/team/initialize",{"members":[self._payload(x) for x in members]})
    def builder_output(self,machine_id,output): return self._request("POST",f"/v1/machines/{machine_id}/team/builder-output",{"output":self._payload(output)})
    def verifier_report(self,machine_id,report): return self._request("POST",f"/v1/machines/{machine_id}/team/verifier-report",{"report":self._payload(report)})
    def planner_decision(self,machine_id,decision): return self._request("POST",f"/v1/machines/{machine_id}/team/planner-decision",{"decision":self._payload(decision)})
    def analyze_collaboration(self,machine_id,policy=None,tasks=None):
        body={"policy":self._payload(policy) if policy is not None else {}}
        if tasks is not None: body["tasks"]=[self._payload(x) for x in tasks]
        return self._request("POST",f"/v1/machines/{machine_id}/collaboration/analyze",body)
    def analyze_change(self,machine_id,signal,pause_affected=True): return self._request("POST",f"/v1/machines/{machine_id}/change-control/analyze",{"signal":self._payload(signal),"pause_affected":bool(pause_affected)})
    def resolve_change_impact(self,machine_id,impact_id,planner_id,*,resume_nodes=None,retire_nodes=None,plan_decision_id=None):
        return self._request("POST",f"/v1/machines/{machine_id}/change-control/{impact_id}/resolve",{"planner_id":planner_id,"resume_nodes":list(resume_nodes or []),"retire_nodes":list(retire_nodes or []),"plan_decision_id":plan_decision_id})
    def configure_checkpoint_triggers(self,machine_id,policy): return self._request("POST",f"/v1/machines/{machine_id}/checkpoint-triggers/configure",{"policy":self._payload(policy)})
    def configure_fleet_control(self,machine_id,policy,refresh=True): return self._request("POST",f"/v1/machines/{machine_id}/fleet-control/configure",{"policy":self._payload(policy),"refresh":bool(refresh)})
    def refresh_fleet_control(self,machine_id,collaboration_policy=None): return self._request("POST",f"/v1/machines/{machine_id}/fleet-control/refresh",{"collaboration_policy":self._payload(collaboration_policy) if collaboration_policy is not None else {}})
    def telemetry(self,machine_id,record): return self._request("POST",f"/v1/machines/{machine_id}/telemetry",{"record":self._payload(record)})
    def configure_telemetry(self,machine_id,policy): return self._request("POST",f"/v1/machines/{machine_id}/telemetry/configure",{"policy":self._payload(policy)})
    def plan_provisioning(self,machine_id,provider,resource_id,desired_workers=None): return self._request("POST",f"/v1/machines/{machine_id}/provisioning/plan",{"provider":provider,"resource_id":resource_id,"desired_workers":desired_workers})
    def propose_provisioning(self,machine_id,request): return self._request("POST",f"/v1/machines/{machine_id}/provisioning/propose",{"request":self._payload(request)})
    def authorize_provisioning(self,machine_id,effect_id,authority="controller"): return self._request("POST",f"/v1/machines/{machine_id}/provisioning/{effect_id}/authorize",{"authority":authority})
    def execute_provisioning(self,machine_id,effect_id): return self._request("POST",f"/v1/machines/{machine_id}/provisioning/{effect_id}/execute",{})
