from __future__ import annotations

import argparse
from dataclasses import asdict
import hmac
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from .adaptive_routing import ModelOutcomeRecord
from .change_impact import ChangeSignal
from .checkpoint_triggers import CheckpointTriggerPolicy
from .collaboration import CollaborationPolicy
from .control_center_v19 import html_document
from .economics import ModelUsageRecord
from .execution_controls import WorkerControlRecord
from .execution_telemetry import ExecutionTelemetryRecord, TelemetryPolicy
from .fleet_control import FleetControlPolicy
from .governance import GovernanceBudgetPolicy, GovernanceContext
from .mission_control import ForkRequest, MissionControlAction, MissionControlRecord, MissionPauseMode
from .model import ProblemSpec
from .model_routing import ModelRouteRequest
from .persistence.factory import open_store
from .provisioning import ProvisioningRequest
from .resources import TaskDemand
from .runtime_v19 import AASMEngine
from .team_protocol import BuilderOutput, PlannerDecision, TeamMember, VerifierReport
from .workers import WorkerRecord


MAX_BODY_BYTES = 1_000_000
MAX_ARTIFACT_PREVIEW_CHARS = 200_000
LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}
CSP = "default-src 'self'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'; img-src 'self' data:; object-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"


def make_handler(store_target: str, token: str | None = None, provisioners=None, artifacts=None):
    class Handler(BaseHTTPRequestHandler):
        server_version = "AASM/0.19"

        def log_message(self, fmt, *args):
            pass

        def _auth(self):
            if not token:
                return True
            return hmac.compare_digest(self.headers.get("Authorization", ""), f"Bearer {token}")

        def _security_headers(self, *, html=False):
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
            if html:
                self.send_header("Content-Security-Policy", CSP)

        def _json(self, status, payload):
            raw = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self._security_headers()
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def _read(self):
            length = int(self.headers.get("Content-Length", "0") or 0)
            if length < 0 or length > MAX_BODY_BYTES:
                raise ValueError(f"request body exceeds {MAX_BODY_BYTES} bytes")
            value = json.loads(self.rfile.read(length) if length else b"{}")
            if not isinstance(value, dict):
                raise ValueError("JSON request body must be an object")
            return value

        def _machine(self, machine_id):
            store = open_store(store_target)
            try:
                engine = AASMEngine.resume(machine_id, store, load_history=False)
            except Exception:
                store.close()
                raise
            return store, engine

        def _error(self, exc):
            status = 403 if isinstance(exc, PermissionError) else 400
            self._json(status, {"error": type(exc).__name__, "message": str(exc)})

        @staticmethod
        def _q(query, key, default=None):
            values = query.get(key)
            return default if not values else values[-1]

        def do_GET(self):
            parsed = urlparse(self.path)
            if parsed.path == "/health":
                return self._json(200, {"ok": True, "protocol": "aasm.remote.v1", "version": "0.19.0"})
            if parsed.path == "/ui":
                raw = html_document().encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self._security_headers(html=True)
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                return self.wfile.write(raw)
            if not self._auth():
                return self._json(401, {"error": "unauthorized"})

            parts = [part for part in parsed.path.split("/") if part]
            query = parse_qs(parsed.query, keep_blank_values=False)
            try:
                if len(parts) < 4 or parts[:2] != ["v1", "machines"]:
                    return self._json(404, {"error": "not_found"})
                machine_id = parts[2]
                resource = parts[3:]
                store, engine = self._machine(machine_id)
                try:
                    if resource == ["dashboard"]:
                        payload = engine.dashboard()
                    elif resource == ["state"]:
                        payload = {
                            "snapshot": asdict(engine.snapshot),
                            "event_sequence": engine.current_sequence(),
                            "workers": engine.list_workers(),
                            "leases": engine.list_leases(),
                            "models": engine.list_model_profiles(),
                            "last_model_route": engine.last_model_route(),
                            "model_performance": engine.model_performance(),
                            "governance": engine.governance_report(),
                            "team_protocol": engine.team_report(),
                            "collaboration": engine.last_collaboration_analysis(),
                            "change_control": {"paused_tasks": engine.paused_tasks(), "last_impact": engine.last_impact()},
                            "checkpoint_triggers": {"policy": asdict(engine.checkpoint_trigger_policy()), "last": engine.last_checkpoint_trigger()},
                            "fleet_control": engine.fleet_control_report(),
                            "execution_telemetry": engine.telemetry_report(),
                            "provisioning": engine.provisioning_report(),
                            "execution_controls": engine.execution_control_report(),
                            "external_artifacts": engine.external_artifacts(limit=100),
                            "mission_control": engine.mission_control_report(),
                            "effect_queue": engine.effect_queue_report(),
                            "forks": engine.fork_report(),
                        }
                    elif resource == ["team"]:
                        payload = engine.team_report()
                    elif resource == ["collaboration"]:
                        payload = engine.last_collaboration_analysis() or {}
                    elif resource == ["change-control"]:
                        payload = {"paused_tasks": engine.paused_tasks(), "last_impact": engine.last_impact(), "impacts": engine.impact_history()}
                    elif resource == ["checkpoint-triggers"]:
                        payload = {"policy": asdict(engine.checkpoint_trigger_policy()), "last": engine.last_checkpoint_trigger(), "history": engine.checkpoint_trigger_history()}
                    elif resource == ["fleet-control"]:
                        payload = engine.fleet_control_report()
                    elif resource == ["telemetry"]:
                        payload = engine.telemetry_report()
                    elif resource == ["telemetry", "page"]:
                        payload = engine.telemetry_page(
                            cursor=self._q(query, "cursor"),
                            limit=int(self._q(query, "limit", 100)),
                            task_id=self._q(query, "task_id"),
                            worker_id=self._q(query, "worker_id"),
                            kind=self._q(query, "kind"),
                        )
                    elif resource == ["provisioning"]:
                        payload = engine.provisioning_report()
                    elif resource == ["execution-controls"]:
                        payload = engine.execution_control_report()
                    elif resource == ["artifacts"]:
                        payload = {"artifacts": engine.external_artifacts(limit=200)}
                    elif resource == ["artifacts", "page"]:
                        payload = engine.artifact_page(
                            cursor=self._q(query, "cursor"),
                            limit=int(self._q(query, "limit", 100)),
                            task_id=self._q(query, "task_id"),
                            worker_id=self._q(query, "worker_id"),
                        )
                    elif resource == ["artifacts", "content"]:
                        if artifacts is None:
                            raise ValueError("No artifact backend registry is configured on this control plane")
                        backend_name = self._q(query, "backend")
                        ref = self._q(query, "ref")
                        if not backend_name or not ref:
                            raise ValueError("backend and ref query parameters are required")
                        known = any(
                            row.get("backend") == backend_name and row.get("ref") == ref
                            for row in engine.external_artifacts(limit=1000)
                        )
                        if not known:
                            raise PermissionError("artifact reference is not registered to this machine")
                        text = artifacts.get(backend_name).get_text(ref)
                        payload = {
                            "backend": backend_name,
                            "ref": ref,
                            "text": text[:MAX_ARTIFACT_PREVIEW_CHARS],
                            "truncated": len(text) > MAX_ARTIFACT_PREVIEW_CHARS,
                            "characters": len(text),
                        }
                    elif resource == ["mission-control"]:
                        payload = engine.mission_control_report()
                    elif resource == ["effects"]:
                        payload = engine.effect_queue_report()
                    elif resource == ["forks"]:
                        payload = engine.fork_report()
                    else:
                        return self._json(404, {"error": "not_found"})
                finally:
                    store.close()
                return self._json(200, payload)
            except Exception as exc:
                return self._error(exc)

        def do_POST(self):
            if not self._auth():
                return self._json(401, {"error": "unauthorized"})
            parts = [part for part in urlparse(self.path).path.split("/") if part]
            try:
                payload = self._read()
                if parts == ["v1", "machines"]:
                    store = open_store(store_target)
                    try:
                        engine = AASMEngine(ProblemSpec(**payload["problem"]), store=store)
                        out = {"machine_id": engine.snapshot.machine_id, "state": engine.state_value}
                    finally:
                        store.close()
                    return self._json(201, out)
                if len(parts) < 3 or parts[:2] != ["v1", "machines"]:
                    return self._json(404, {"error": "not_found"})

                machine_id = parts[2]
                resource = parts[3:]
                store, engine = self._machine(machine_id)
                try:
                    if resource == ["workers", "register"]:
                        out = engine.register_worker(WorkerRecord(**payload["worker"]))
                    elif len(resource) == 3 and resource[0] == "workers" and resource[2] == "heartbeat":
                        out = engine.worker_heartbeat(resource[1])
                    elif len(resource) == 3 and resource[0] == "workers" and resource[2] == "control":
                        out = engine.control_worker(WorkerControlRecord(worker_id=resource[1], **payload["control"]))
                    elif resource == ["claim"]:
                        out = engine.claim_task(TaskDemand(**payload["task"]), payload["worker_id"], lease_seconds=float(payload.get("lease_seconds", 60)))
                    elif resource == ["claim-next"]:
                        out = engine.claim_next_task(payload["worker_id"], lease_seconds=float(payload.get("lease_seconds", 60)))
                        if out is None:
                            return self._json(200, {"lease": None})
                    elif len(resource) == 3 and resource[0] == "leases" and resource[2] == "heartbeat":
                        out = engine.lease_heartbeat(resource[1], extend_seconds=float(payload.get("extend_seconds", 60)))
                    elif len(resource) == 3 and resource[0] == "leases" and resource[2] == "complete":
                        out = engine.complete_lease(resource[1], result=payload.get("result"))
                    elif len(resource) == 3 and resource[0] == "leases" and resource[2] == "fail":
                        out = engine.fail_lease(resource[1], error=payload.get("error"))
                    elif resource == ["model-route"]:
                        out = engine.route_model(ModelRouteRequest(**payload["request"])).to_dict()
                    elif resource == ["model-usage"]:
                        out = engine.record_model_usage(ModelUsageRecord(**payload["record"]))
                    elif resource == ["model-outcome"]:
                        out = engine.record_model_outcome(ModelOutcomeRecord(**payload["record"]))
                    elif resource == ["governance-budget"]:
                        out = engine.configure_governance_budget(GovernanceBudgetPolicy(**payload["policy"]))
                    elif resource == ["governance-decision"]:
                        out = engine.governance_decide(GovernanceContext(**payload["context"]))
                    elif len(resource) == 3 and resource[0] == "governance-review" and resource[2] == "complete":
                        out = engine.complete_governance_review(resource[1], evidence=payload.get("evidence"))
                    elif resource == ["team", "initialize"]:
                        out = engine.initialize_team([TeamMember(**row) for row in payload["members"]])
                    elif resource == ["team", "builder-output"]:
                        out = engine.submit_builder_output(BuilderOutput(**payload["output"]))
                    elif resource == ["team", "verifier-report"]:
                        out = engine.submit_verifier_report(VerifierReport(**payload["report"]))
                    elif resource == ["team", "planner-decision"]:
                        out = engine.planner_decide(PlannerDecision(**payload["decision"]))
                    elif resource == ["collaboration", "analyze"]:
                        rows = payload.get("tasks")
                        tasks = None if rows is None else [TaskDemand(**row) for row in rows]
                        out = engine.analyze_collaboration(tasks, CollaborationPolicy(**payload.get("policy", {})))
                    elif resource == ["change-control", "analyze"]:
                        out = engine.analyze_change(ChangeSignal(**payload["signal"]), pause_affected=bool(payload.get("pause_affected", True)))
                    elif len(resource) == 3 and resource[0] == "change-control" and resource[2] == "resolve":
                        out = engine.resolve_change_impact(payload["planner_id"], resource[1], resume_nodes=payload.get("resume_nodes"), retire_nodes=payload.get("retire_nodes"), plan_decision_id=payload.get("plan_decision_id"))
                    elif resource == ["checkpoint-triggers", "configure"]:
                        out = engine.configure_checkpoint_triggers(CheckpointTriggerPolicy(**payload.get("policy", {})))
                    elif resource == ["fleet-control", "configure"]:
                        out = engine.configure_fleet_control(FleetControlPolicy(**payload.get("policy", {})), refresh=bool(payload.get("refresh", True)))
                    elif resource == ["fleet-control", "refresh"]:
                        out = engine.refresh_fleet_control(collaboration_policy=CollaborationPolicy(**payload.get("collaboration_policy", {})))
                    elif resource == ["telemetry"]:
                        out = engine.record_execution_telemetry(ExecutionTelemetryRecord(**payload["record"]))
                    elif resource == ["telemetry", "configure"]:
                        out = engine.configure_telemetry(TelemetryPolicy(**payload.get("policy", {})))
                    elif resource == ["provisioning", "plan"]:
                        out = engine.plan_fleet_provisioning(payload["provider"], payload["resource_id"], desired_workers=payload.get("desired_workers"))
                    elif resource == ["provisioning", "propose"]:
                        out = engine.propose_provisioning(ProvisioningRequest(**payload["request"]))
                    elif len(resource) == 3 and resource[0] == "provisioning" and resource[2] == "authorize":
                        out = engine.authorize_pending_effect(resource[1], payload.get("authority", "controller"), payload.get("reason", "provisioning approved"))
                    elif len(resource) == 3 and resource[0] == "provisioning" and resource[2] == "execute":
                        if provisioners is None:
                            raise ValueError("No provisioning registry is configured on this control plane")
                        effect = engine.store.load_effect(machine_id, resource[1])
                        provider = (effect.spec.payload or {}).get("provider")
                        out = engine.execute_provisioning(resource[1], provisioners.get(provider))
                    elif resource == ["artifacts", "text"]:
                        if artifacts is None:
                            raise ValueError("No artifact backend registry is configured on this control plane")
                        backend_name = payload["backend"]
                        out = engine.store_text_artifact(
                            artifacts.get(backend_name),
                            backend_name=backend_name,
                            namespace=payload.get("namespace", machine_id),
                            name=payload["name"],
                            text=payload["text"],
                            worker_id=payload.get("worker_id"),
                            task_id=payload.get("task_id"),
                            lease_id=payload.get("lease_id"),
                            metadata=payload.get("metadata"),
                        )
                    elif resource == ["mission-control", "pause"]:
                        out = engine.pause_mission(MissionControlRecord(
                            MissionControlAction.PAUSE,
                            payload["actor"],
                            payload["reason"],
                            payload.get("mode", MissionPauseMode.QUIESCE),
                            metadata=payload.get("metadata", {}),
                        ))
                    elif resource == ["mission-control", "resume"]:
                        out = engine.resume_mission(MissionControlRecord(
                            MissionControlAction.RESUME,
                            payload["actor"],
                            payload["reason"],
                            metadata=payload.get("metadata", {}),
                        ))
                    elif len(resource) == 3 and resource[0] == "effects" and resource[2] == "authorize":
                        out = engine.authorize_pending_effect(resource[1], payload["actor"], payload["reason"])
                    elif resource == ["forks", "propose"]:
                        out = engine.propose_fork(ForkRequest(**payload["request"]))
                    elif len(resource) == 3 and resource[0] == "forks" and resource[2] == "execute":
                        out = engine.execute_fork(resource[1])
                    elif resource == ["review-gate"]:
                        out = engine.review_gate(payload["action_class"], **payload.get("signals", {}))
                    elif resource == ["interrupt"]:
                        out = engine.user_interrupt(payload["note"], metadata=payload.get("metadata"))
                    else:
                        return self._json(404, {"error": "not_found"})
                    return self._json(200, out if isinstance(out, dict) else asdict(out))
                finally:
                    store.close()
            except Exception as exc:
                return self._error(exc)

    return Handler


def serve(store_target: str, host="127.0.0.1", port=8787, token: str | None = None, provisioners=None, artifacts=None):
    token = token or os.getenv("AASM_SERVER_TOKEN")
    if host not in LOOPBACK_HOSTS and not token:
        raise ValueError("AASM refuses non-loopback binding without --token or AASM_SERVER_TOKEN")
    ThreadingHTTPServer((host, int(port)), make_handler(store_target, token, provisioners, artifacts)).serve_forever()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--store", required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--token")
    args = parser.parse_args()
    serve(args.store, args.host, args.port, args.token)
