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
    def __init__(self,base_url:str,token:str|None=None,timeout:float=30.0):
        self.base_url=base_url.rstrip('/'); self.token=token; self.timeout=timeout
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
    def health(self): return self._request("GET","/health")
    def create_machine(self,problem:dict): return self._request("POST","/v1/machines",{"problem":problem})
    def state(self,machine_id): return self._request("GET",f"/v1/machines/{machine_id}/state")
    def register_worker(self,machine_id,worker:WorkerRecord): return self._request("POST",f"/v1/machines/{machine_id}/workers/register",{"worker":asdict(worker)})
    def heartbeat(self,machine_id,worker_id): return self._request("POST",f"/v1/machines/{machine_id}/workers/{worker_id}/heartbeat",{})
    def claim(self,machine_id,worker_id,task:TaskDemand,lease_seconds=60.0): return self._request("POST",f"/v1/machines/{machine_id}/claim",{"worker_id":worker_id,"task":asdict(task),"lease_seconds":lease_seconds})
    def claim_next(self,machine_id,worker_id,lease_seconds=60.0): return self._request("POST",f"/v1/machines/{machine_id}/claim-next",{"worker_id":worker_id,"lease_seconds":lease_seconds})
    def lease_heartbeat(self,machine_id,lease_id,extend_seconds=60.0): return self._request("POST",f"/v1/machines/{machine_id}/leases/{lease_id}/heartbeat",{"extend_seconds":extend_seconds})
    def complete(self,machine_id,lease_id,result=None): return self._request("POST",f"/v1/machines/{machine_id}/leases/{lease_id}/complete",{"result":result or {}})
    def fail(self,machine_id,lease_id,error): return self._request("POST",f"/v1/machines/{machine_id}/leases/{lease_id}/fail",{"error":error})
    def route_model(self,machine_id,request:ModelRouteRequest): return self._request("POST",f"/v1/machines/{machine_id}/model-route",{"request":asdict(request)})
    def model_usage(self,machine_id,record):
        payload=asdict(record) if hasattr(record,"__dataclass_fields__") else dict(record)
        return self._request("POST",f"/v1/machines/{machine_id}/model-usage",{"record":payload})
