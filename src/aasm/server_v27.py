from __future__ import annotations

import argparse
import json
import os
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote, urlparse

from . import __version__, server_v19 as _v19, server_v25 as _v25
from .control_center_v27 import html_document

# server_v25 deliberately reuses the established v0.19 HTTP surface. Replace
# only the HTML renderer used by that surface; authority, routing, stores, and
# machine mutation remain in the existing handlers and runtime.
_v19.html_document = html_document

CSP = _v25.CSP
LOOPBACK_HOSTS = _v25.LOOPBACK_HOSTS
MAX_ARTIFACT_PREVIEW_CHARS = _v25.MAX_ARTIFACT_PREVIEW_CHARS
MAX_BODY_BYTES = _v25.MAX_BODY_BYTES


def _read_demo_state(path: str | None) -> dict:
    if not path:
        return {"enabled": False, "reason": "demo state path is not configured"}
    target = Path(path)
    if not target.exists():
        return {
            "enabled": True,
            "ready": False,
            "state_path": str(target),
            "reason": "demo stack bootstrap has not written state yet",
        }
    value = json.loads(target.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("demo stack state must be a JSON object")
    return {"enabled": True, "ready": True, **value}


def make_handler(
    store_target: str,
    token: str | None = None,
    provisioners=None,
    artifacts=None,
    demo_state_path: str | None = None,
):
    base_handler = _v25.make_handler(store_target, token, provisioners, artifacts)

    class Handler(base_handler):
        server_version = f"AASM/{__version__}"

        def _redirect(self, location: str):
            self.send_response(302)
            self.send_header("Location", location)
            self._security_headers(html=True)
            self.send_header("Content-Length", "0")
            self.end_headers()

        def do_GET(self):
            parsed = urlparse(self.path)
            if parsed.path == "/":
                location = "/ui"
                if demo_state_path and token:
                    location += "?token=" + quote(token, safe="")
                return self._redirect(location)
            if parsed.path == "/demo-stack":
                if not self._auth():
                    return self._json(401, {"error": "unauthorized"})
                try:
                    payload = _read_demo_state(demo_state_path)
                except Exception as exc:
                    return self._error(exc)
                payload["runtime_version"] = __version__
                payload["control_center_path"] = "/ui"
                payload["health_path"] = "/health"
                return self._json(200, payload)
            return super().do_GET()

    return Handler


def serve(
    store_target: str,
    host: str = "127.0.0.1",
    port: int = 8787,
    token: str | None = None,
    provisioners=None,
    artifacts=None,
    demo_state_path: str | None = None,
):
    token = token or os.getenv("AASM_SERVER_TOKEN")
    demo_state_path = demo_state_path or os.getenv("AASM_DEMO_STATE")
    if host not in LOOPBACK_HOSTS and not token:
        raise ValueError(
            "AASM refuses non-loopback binding without --token or AASM_SERVER_TOKEN"
        )
    handler = make_handler(
        store_target,
        token,
        provisioners,
        artifacts,
        demo_state_path,
    )
    ThreadingHTTPServer((host, int(port)), handler).serve_forever()


def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--store", required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--token")
    parser.add_argument("--demo-state")
    args = parser.parse_args(argv)
    serve(
        args.store,
        args.host,
        args.port,
        args.token,
        demo_state_path=args.demo_state,
    )


if __name__ == "__main__":
    main()
