from __future__ import annotations
import argparse, hmac, json, os
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
from .adaptive_routing import ModelOutcomeRecord
from .change_impact import ChangeSignal
from .checkpoint_triggers import CheckpointTriggerPolicy
from .collaboration import CollaborationPolicy
from .control_center import html_document
from .economics import ModelUsageRecord
from .execution_controls import WorkerControlRecord
from .execution_telemetry import ExecutionTelemetryRecord, TelemetryPolicy
from .fleet_control import FleetControlPolicy
from .governance import GovernanceBudgetPolicy, GovernanceContext
from .model import ProblemSpec
from .model_routing import ModelRouteRequest
from .persistence.factory import open_store
from .provisioning import ProvisioningRequest
from .resources import TaskDemand
from .runtime_v18 import AASMEngine
from .team_protocol import BuilderOutput, PlannerDecision, TeamMember, VerifierReport
from .workers import WorkerRecord

MAX_BODY_BYTES=1_000_000
LOOPBACK_HOSTS={"127.0.0.1","localhost","::1"}
CSP="default-src 'self'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'; img-src 'self' data:; object-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"

def make_handler(store_target:str,token:str|None=None,provisioners=None,artifacts=None):
    class Handler(BaseHTTPRequestHandler):
        server_version="AASM/0.18"
        def log_message(self,fmt,*args): pass
        def _auth(self):
            if not token: return True
            return hmac.compare_digest(self.headers.get("Authorization",""),f"Bearer {token}")
        def _security_headers(self,*,html=False):
            self.send_header("Cache-Control","no-store"); self.send_header("X-Content-Type-Options","nosniff"); self.send_header("Referrer-Policy","no-referrer"); self.send_header("X-Frame-Options","DENY"); self.send_header("Permissions-Policy","camera=(), microphone=(), geolocation=()")
            if html: self.send_header("Content-Security-Policy",CSP)
        def _json(self,status,payload):
            raw=json.dumps(payload,sort_keys=True,default=str).encode(); self.send_response(status); self.send_header("Content-Type","application/json; charset=utf-8"); self._security_headers(); self.send_header("Content-Length",str(len(raw))); self.end_headers(); self.wfile.write(raw)
        def _read(self):
            n=int(self.headers.get("Content-Length","0") or 0)
            if n<0 or n>MAX_BODY_BYTES: raise ValueError(f"request body exceeds {MAX_BODY_BYTES} bytes")
            value=json.loads(self.rfile.read(n) if n else b"{}")
            if not isinstance(value,dict): raise ValueError("JSON request body must be an object")
            return value
        def _machine(self,mid):
            store=open_store(store_target)
            try: engine=AASMEngine.resume(mid,store,load_history=False)
            except Exception: store.close(); raise
            return store,engine
        def _error(self,exc): self._json(400,{"error":type(exc).__name__,"message":str(exc)})
        def do_GET(self):
            parsed=urlparse(self.path)
            if parsed.path=="/health": return self._json(200,{"ok":True,"protocol":"aasm.remote.v1","version":"0.18.0"})
            if parsed.path=="/ui":
                raw=html_document().encode(); self.send_response(200); self.send_header("Content-Type","text/html; charset=utf-8"); self._security_headers(html=True); self.send_header("Content-Length",str(len(raw))); self.end_headers(); return self.wfile.write(raw)
            if not self._auth(): return self._json(401,{"error":"unauthorized"})
            parts=[p for p in parsed.path.split('/') if p]
            try:
                supported={"state","dashboard","team","collaboration","change-control","checkpoint-triggers","fleet-control","telemetry","provisioning","execution-controls","artifacts"}
                if len(parts)==4 and parts[:2]==["v1","machines"] and parts[3] in supported:
                    store,engine=self._machine(parts[2])
                    try:
                        if parts[3]=="dashboard": payload=engine.dashboard()
                        elif parts[3]=="team": payload=engine.team_report()
                        elif parts[3]=="collaboration": payload=engine.last_collaboration_analysis() or {}
                        elif parts[3]=="change-control": payload={"paused_tasks":engine.paused_tasks(),"last_impact":engine.last_impact(),"impacts":engine.impact_history()}
                        elif parts[3]=="checkpoint-triggers": payload={"policy":asdict(engine.checkpoint_trigger_policy()),"last":engine.last_checkpoint_trigger(),"history":engine.checkpoint_trigger_history()}
                        elif parts[3]=="fleet-control": payload=engine.fleet_control_report()
                        elif parts[3]=="telemetry": payload=engine.telemetry_report()
                        elif parts[3]=="provisioning": payload=engine.provisioning_report()
                        elif parts[3]=="execution-controls": payload=engine.execution_control_report()
                        elif parts[3]=="artifacts": payload={"artifacts":engine.external_artifacts(limit=200)}
                        else: payload={"snapshot":asdict(engine.snapshot),"workers":engine.list_workers(),"leases":engine.list_leases(),"models":engine.list_model_profiles(),"last_model_route":engine.last_model_route(),"model_performance":engine.model_performance(),"governance":engine.governance_report(),"team_protocol":engine.team_report(),"collaboration":engine.last_collaboration_analysis(),"change_control":{"paused_tasks":engine.paused_tasks(),"last_impact":engine.last_impact()},"checkpoint_triggers":{"policy":asdict(engine.checkpoint_trigger_policy()),"last":engine.last_checkpoint_trigger()},"fleet_control":engine.fleet_control_report(),"execution_telemetry":engine.telemetry_report(),"provisioning":engine.provisioning_report(),"execution_controls":engine.execution_control_report(),"external_artifacts":engine.external_artifacts(limit=100)}
                    finally: store.close()
                    return self._json(200,payload)
                return self._json(404,{"error":"not_found"})
            except Exception as exc: return self._error(exc)
        def do_POST(self):
            if not self._auth(): return self._json(401,{"error":"unauthorized"})
            parts=[p for p in urlparse(self.path).path.split('/') if p]
            try:
                payload=self._read()
                if parts==["v1","machines"]:
                    store=open_store(store_target)
                    try: engine=AASMEngine(ProblemSpec(**payload["problem"]),store=store); out={"machine_id":engine.snapshot.machine_id,"state":engine.state_value}
                    finally: store.close()
                    return self._json(201,out)
                if len(parts)<3 or parts[:2] != ["v1","machines"]: return self._json(404,{"error":"not_found"})
                mid=parts[2]; store,engine=self._machine(mid)
                try:
                    if parts[3:]==["workers","register"]: out=engine.register_worker(WorkerRecord(**payload["worker"]))
                    elif len(parts)==6 and parts[3]=="workers" and parts[5]=="heartbeat": out=engine.worker_heartbeat(parts[4])
                    elif len(parts)==6 and parts[3]=="workers" and parts[5]=="control": out=engine.control_worker(WorkerControlRecord(worker_id=parts[4],**payload["control"]))
                    elif parts[3:]==["claim"]: out=engine.claim_task(TaskDemand(**payload["task"]),payload["worker_id"],lease_seconds=float(payload.get("lease_seconds",60)))
                    elif parts[3:]==["claim-next"]:
                        out=engine.claim_next_task(payload["worker_id"],lease_seconds=float(payload.get("lease_seconds",60)))
                        if out is None: return self._json(200,{"lease":None})
                    elif len(parts)==6 and parts[3]=="leases" and parts[5]=="heartbeat": out=engine.lease_heartbeat(parts[4],extend_seconds=float(payload.get("extend_seconds",60)))
                    elif len(parts)==6 and parts[3]=="leases" and parts[5]=="complete": out=engine.complete_lease(parts[4],result=payload.get("result"))
                    elif len(parts)==6 and parts[3]=="leases" and parts[5]=="fail": out=engine.fail_lease(parts[4],error=payload.get("error"))
                    elif parts[3:]==["model-route"]: out=engine.route_model(ModelRouteRequest(**payload["request"])).to_dict()
                    elif parts[3:]==["model-usage"]: out=engine.record_model_usage(ModelUsageRecord(**payload["record"]))
                    elif parts[3:]==["model-outcome"]: out=engine.record_model_outcome(ModelOutcomeRecord(**payload["record"]))
                    elif parts[3:]==["governance-budget"]: out=engine.configure_governance_budget(GovernanceBudgetPolicy(**payload["policy"]))
                    elif parts[3:]==["governance-decision"]: out=engine.governance_decide(GovernanceContext(**payload["context"]))
                    elif len(parts)==6 and parts[3]=="governance-review" and parts[5]=="complete": out=engine.complete_governance_review(parts[4],evidence=payload.get("evidence"))
                    elif parts[3:]==["team","initialize"]: out=engine.initialize_team([TeamMember(**x) for x in payload["members"]])
                    elif parts[3:]==["team","builder-output"]: out=engine.submit_builder_output(BuilderOutput(**payload["output"]))
                    elif parts[3:]==["team","verifier-report"]: out=engine.submit_verifier_report(VerifierReport(**payload["report"]))
                    elif parts[3:]==["team","planner-decision"]: out=engine.planner_decide(PlannerDecision(**payload["decision"]))
                    elif parts[3:]==["collaboration","analyze"]:
                        task_rows=payload.get("tasks"); tasks=None if task_rows is None else [TaskDemand(**x) for x in task_rows]
                        out=engine.analyze_collaboration(tasks,CollaborationPolicy(**payload.get("policy",{})))
                    elif parts[3:]==["change-control","analyze"]: out=engine.analyze_change(ChangeSignal(**payload["signal"]),pause_affected=bool(payload.get("pause_affected",True)))
                    elif len(parts)==6 and parts[3]=="change-control" and parts[5]=="resolve": out=engine.resolve_change_impact(payload["planner_id"],parts[4],resume_nodes=payload.get("resume_nodes"),retire_nodes=payload.get("retire_nodes"),plan_decision_id=payload.get("plan_decision_id"))
                    elif parts[3:]==["checkpoint-triggers","configure"]: out=engine.configure_checkpoint_triggers(CheckpointTriggerPolicy(**payload.get("policy",{})))
                    elif parts[3:]==["fleet-control","configure"]: out=engine.configure_fleet_control(FleetControlPolicy(**payload.get("policy",{})),refresh=bool(payload.get("refresh",True)))
                    elif parts[3:]==["fleet-control","refresh"]: out=engine.refresh_fleet_control(collaboration_policy=CollaborationPolicy(**payload.get("collaboration_policy",{})))
                    elif parts[3:]==["telemetry"]: out=engine.record_execution_telemetry(ExecutionTelemetryRecord(**payload["record"]))
                    elif parts[3:]==["telemetry","configure"]: out=engine.configure_telemetry(TelemetryPolicy(**payload.get("policy",{})))
                    elif parts[3:]==["provisioning","plan"]: out=engine.plan_fleet_provisioning(payload["provider"],payload["resource_id"],desired_workers=payload.get("desired_workers"))
                    elif parts[3:]==["provisioning","propose"]: out=engine.propose_provisioning(ProvisioningRequest(**payload["request"]))
                    elif len(parts)==6 and parts[3]=="provisioning" and parts[5]=="authorize": out=engine.authorize_effect(parts[4],authority=payload.get("authority","controller"))
                    elif len(parts)==6 and parts[3]=="provisioning" and parts[5]=="execute":
                        if provisioners is None: raise ValueError("No provisioning registry is configured on this control plane")
                        effect=engine.store.load_effect(mid,parts[4]); provider=(effect.spec.payload or {}).get("provider"); adapter=provisioners.get(provider); out=engine.execute_provisioning(parts[4],adapter)
                    elif parts[3:]==["artifacts","text"]:
                        if artifacts is None: raise ValueError("No artifact backend registry is configured on this control plane")
                        backend_name=payload["backend"]; backend=artifacts.get(backend_name); out=engine.store_text_artifact(backend,backend_name=backend_name,namespace=payload.get("namespace",mid),name=payload["name"],text=payload["text"],worker_id=payload.get("worker_id"),task_id=payload.get("task_id"),lease_id=payload.get("lease_id"),metadata=payload.get("metadata"))
                    elif parts[3:]==["review-gate"]: out=engine.review_gate(payload["action_class"],**payload.get("signals",{}))
                    elif parts[3:]==["interrupt"]: out=engine.user_interrupt(payload["note"],metadata=payload.get("metadata"))
                    else: return self._json(404,{"error":"not_found"})
                    return self._json(200,out if isinstance(out,dict) else asdict(out))
                finally: store.close()
            except Exception as exc: return self._error(exc)
    return Handler

def serve(store_target:str,host="127.0.0.1",port=8787,token:str|None=None,provisioners=None,artifacts=None):
    token=token or os.getenv("AASM_SERVER_TOKEN")
    if host not in LOOPBACK_HOSTS and not token: raise ValueError("AASM refuses non-loopback binding without --token or AASM_SERVER_TOKEN")
    ThreadingHTTPServer((host,int(port)),make_handler(store_target,token,provisioners,artifacts)).serve_forever()

def main():
    p=argparse.ArgumentParser(); p.add_argument("--store",required=True); p.add_argument("--host",default="127.0.0.1"); p.add_argument("--port",type=int,default=8787); p.add_argument("--token"); a=p.parse_args(); serve(a.store,a.host,a.port,a.token)
