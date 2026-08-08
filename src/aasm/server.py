from __future__ import annotations
import argparse, html, json
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse
from .model import ProblemSpec
from .model_routing import ModelRouteRequest
from .persistence.factory import open_store
from .resources import TaskDemand
from .runtime_v08 import AASMEngine
from .workers import WorkerRecord


def make_handler(store_target:str,token:str|None=None):
    class Handler(BaseHTTPRequestHandler):
        server_version="AASM/0.8"
        def log_message(self,fmt,*args): pass
        def _auth(self): return True if not token else self.headers.get("Authorization")==f"Bearer {token}"
        def _json(self,status,payload):
            raw=json.dumps(payload,sort_keys=True,default=str).encode(); self.send_response(status); self.send_header("Content-Type","application/json"); self.send_header("Content-Length",str(len(raw))); self.end_headers(); self.wfile.write(raw)
        def _read(self):
            n=int(self.headers.get("Content-Length","0")); return json.loads(self.rfile.read(n) or b"{}")
        def _machine(self,mid):
            store=open_store(store_target)
            try: engine=AASMEngine.resume(mid,store)
            except Exception: store.close(); raise
            return store,engine
        def _error(self,exc): self._json(400,{"error":type(exc).__name__,"message":str(exc)})

        def do_GET(self):
            if self.path=="/health": return self._json(200,{"ok":True,"protocol":"aasm.remote.v1"})
            if not self._auth(): return self._json(401,{"error":"unauthorized"})
            parsed=urlparse(self.path); parts=[p for p in parsed.path.split('/') if p]
            try:
                if parsed.path=="/ui":
                    mid=parse_qs(parsed.query).get("machine_id",[""])[0]
                    body="<h1>AASM Control Plane</h1><form><input name='machine_id' placeholder='machine id' value='%s'><button>Inspect</button></form>"%html.escape(mid)
                    if mid:
                        store,engine=self._machine(mid)
                        body += "<h2>State</h2><pre>%s</pre>"%html.escape(json.dumps({"state":engine.state_value,"workers":engine.list_workers(),"leases":engine.list_leases(),"models":engine.list_model_profiles()},indent=2,default=str)); store.close()
                    raw=("<!doctype html><meta name='viewport' content='width=device-width'><title>AASM</title><style>body{font-family:system-ui;max-width:1100px;margin:2rem auto;padding:0 1rem}pre{white-space:pre-wrap;background:#111;color:#eee;padding:1rem;border-radius:8px}input{width:60%;padding:.6rem}button{padding:.6rem}</style>"+body).encode(); self.send_response(200); self.send_header("Content-Type","text/html; charset=utf-8"); self.send_header("Content-Length",str(len(raw))); self.end_headers(); return self.wfile.write(raw)
                if len(parts)==4 and parts[:2]==["v1","machines"] and parts[3]=="state":
                    store,engine=self._machine(parts[2]); payload={"snapshot":asdict(engine.snapshot),"workers":engine.list_workers(),"leases":engine.list_leases(),"models":engine.list_model_profiles(),"last_model_route":engine.last_model_route()}; store.close(); return self._json(200,payload)
                return self._json(404,{"error":"not_found"})
            except Exception as exc: return self._error(exc)

        def do_POST(self):
            if not self._auth(): return self._json(401,{"error":"unauthorized"})
            parts=[p for p in urlparse(self.path).path.split('/') if p]
            try:
                payload=self._read()
                if parts==["v1","machines"]:
                    store=open_store(store_target); engine=AASMEngine(ProblemSpec(**payload["problem"]),store=store); out={"machine_id":engine.snapshot.machine_id,"state":engine.state_value}; store.close(); return self._json(201,out)
                if len(parts)<3 or parts[:2] != ["v1","machines"]: return self._json(404,{"error":"not_found"})
                mid=parts[2]; store,engine=self._machine(mid)
                try:
                    if parts[3:]==["workers","register"]: out=engine.register_worker(WorkerRecord(**payload["worker"]))
                    elif len(parts)==6 and parts[3]=="workers" and parts[5]=="heartbeat": out=engine.worker_heartbeat(parts[4])
                    elif parts[3:]==["claim"]: out=engine.claim_task(TaskDemand(**payload["task"]),payload["worker_id"],lease_seconds=float(payload.get("lease_seconds",60)))
                    elif parts[3:]==["claim-next"]:
                        out=engine.claim_next_task(payload["worker_id"],lease_seconds=float(payload.get("lease_seconds",60)))
                        if out is None: store.close(); return self._json(200,{"lease":None})
                    elif len(parts)==6 and parts[3]=="leases" and parts[5]=="heartbeat": out=engine.lease_heartbeat(parts[4],extend_seconds=float(payload.get("extend_seconds",60)))
                    elif len(parts)==6 and parts[3]=="leases" and parts[5]=="complete": out=engine.complete_lease(parts[4],result=payload.get("result"))
                    elif len(parts)==6 and parts[3]=="leases" and parts[5]=="fail": out=engine.fail_lease(parts[4],error=payload.get("error"))
                    elif parts[3:]==["model-route"]: out=engine.route_model(ModelRouteRequest(**payload["request"])).to_dict()
                    else: store.close(); return self._json(404,{"error":"not_found"})
                    store.close(); return self._json(200,out if isinstance(out,dict) else asdict(out))
                except Exception: store.close(); raise
            except Exception as exc: return self._error(exc)
    return Handler


def serve(store_target:str,host="127.0.0.1",port=8787,token:str|None=None):
    server=ThreadingHTTPServer((host,int(port)),make_handler(store_target,token)); server.serve_forever()


def main():
    p=argparse.ArgumentParser(); p.add_argument("--store",required=True,help="SQLite path/sqlite:///... or postgres://..."); p.add_argument("--host",default="127.0.0.1"); p.add_argument("--port",type=int,default=8787); p.add_argument("--token"); a=p.parse_args(); serve(a.store,a.host,a.port,a.token)
