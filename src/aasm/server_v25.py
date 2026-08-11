from __future__ import annotations

import argparse
import os
from http.server import ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from . import server_v19 as _base
from .decision_backends import BackendBudget
from .runtime_v25 import AASMEngine

_base.AASMEngine = AASMEngine

CSP = _base.CSP
LOOPBACK_HOSTS = _base.LOOPBACK_HOSTS
MAX_ARTIFACT_PREVIEW_CHARS = _base.MAX_ARTIFACT_PREVIEW_CHARS
MAX_BODY_BYTES = _base.MAX_BODY_BYTES


def make_handler(store_target: str, token: str | None = None, provisioners=None, artifacts=None):
    base_handler = _base.make_handler(store_target, token, provisioners, artifacts)

    class Handler(base_handler):
        server_version = "AASM/0.25"

        def _v25_machine_resource(self):
            parsed = urlparse(self.path)
            parts = [part for part in parsed.path.split("/") if part]
            if len(parts) < 4 or parts[:2] != ["v1", "machines"]:
                return None
            return parts[2], parts[3:], parse_qs(parsed.query, keep_blank_values=False)

        def do_GET(self):
            if self.path == "/health":
                return self._json(
                    200,
                    {
                        "ok": True,
                        "protocol": "aasm.remote.v1",
                        "version": "0.19.0",
                        "runtime_version": "0.25.0",
                    },
                )
            parsed = self._v25_machine_resource()
            if parsed is None:
                return super().do_GET()
            if not self._auth():
                return self._json(401, {"error": "unauthorized"})
            machine_id, resource, query = parsed
            if not resource or resource[0] not in {"inspect", "candidates", "backends", "assurance", "history-check"}:
                return super().do_GET()
            store, engine = self._machine(machine_id)
            try:
                if resource[0] == "inspect":
                    surface = resource[1] if len(resource) > 1 else self._q(query, "surface", "summary")
                    payload = engine.inspect_machine(surface)
                elif resource == ["candidates"]:
                    payload = {"candidates": engine.candidate_records(status=self._q(query, "status"))}
                elif resource == ["backends"]:
                    payload = engine.backend_report()
                elif resource == ["assurance"]:
                    payload = engine.assurance_report()
                elif resource == ["history-check"]:
                    payload = engine.check_durable_history(persist=False)
                else:
                    return self._json(404, {"error": "not_found"})
            except Exception as exc:
                return self._error(exc)
            finally:
                store.close()
            return self._json(200, payload)

        def do_POST(self):
            parsed = self._v25_machine_resource()
            if parsed is None:
                return super().do_POST()
            if not self._auth():
                return self._json(401, {"error": "unauthorized"})
            machine_id, resource, _ = parsed
            if not resource or resource[0] not in {"candidates", "history-check"}:
                return super().do_POST()
            try:
                payload = self._read()
                store, engine = self._machine(machine_id)
                try:
                    if resource == ["candidates", "generate"]:
                        budget = BackendBudget(
                            max_candidates=int(payload.get("max_candidates", 32)),
                            max_combinations=int(payload.get("max_combinations", 100000)),
                            max_cost=payload.get("max_cost"),
                            max_latency_ms=payload.get("max_latency_ms"),
                        )
                        out = engine.generate_candidate_batch(
                            payload.get("backend_id", "aasm.finite-domain"),
                            budget=budget,
                            continuation=payload.get("continuation"),
                        )
                    elif len(resource) == 3 and resource[0] == "candidates" and resource[2] == "select":
                        out = engine.select_candidate(resource[1])
                    elif len(resource) == 3 and resource[0] == "candidates" and resource[2] == "activate":
                        out = engine.activate_candidate(resource[1])
                    elif resource == ["history-check"]:
                        out = engine.check_durable_history(persist=bool(payload.get("persist", True)))
                    else:
                        return self._json(404, {"error": "not_found"})
                finally:
                    store.close()
                return self._json(200, out)
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


if __name__ == "__main__":
    main()
