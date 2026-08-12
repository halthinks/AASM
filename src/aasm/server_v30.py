from __future__ import annotations

import argparse
import os
from http.server import ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from . import server_v19 as _v19, server_v25 as _v25, server_v29 as _v29
from .control_center_v30 import html_document
from .integrations.conformance import CONFORMANCE_SCENARIOS, conformance_contract
from .integrations.conformance_registry import (
    list_conformance_drivers,
    run_adapter_conformance,
)
from .runtime_v30 import AASMEngine

# Reuse the established authenticated HTTP/store implementation and inject only
# the current runtime and HTML projection.
_v19.AASMEngine = AASMEngine
_v25.AASMEngine = AASMEngine
_v19.html_document = html_document

CSP = _v29.CSP
LOOPBACK_HOSTS = _v29.LOOPBACK_HOSTS
MAX_ARTIFACT_PREVIEW_CHARS = _v29.MAX_ARTIFACT_PREVIEW_CHARS
MAX_BODY_BYTES = _v29.MAX_BODY_BYTES


def make_handler(
    store_target: str,
    token: str | None = None,
    provisioners=None,
    artifacts=None,
    demo_state_path: str | None = None,
):
    base_handler = _v29.make_handler(
        store_target,
        token,
        provisioners,
        artifacts,
        demo_state_path,
    )

    class Handler(base_handler):
        def do_GET(self):
            parsed = urlparse(self.path)
            if parsed.path == "/adapter-conformance":
                if not self._auth():
                    return self._json(401, {"error": "unauthorized"})
                return self._json(
                    200,
                    {
                        **conformance_contract(),
                        "drivers": list_conformance_drivers(),
                    },
                )
            prefix = "/v1/conformance/adapters/"
            if parsed.path.startswith(prefix):
                if not self._auth():
                    return self._json(401, {"error": "unauthorized"})
                adapter_id = parsed.path[len(prefix) :].strip("/")
                query = parse_qs(parsed.query)
                scenarios = query.get("scenario") or None
                if scenarios:
                    unknown = sorted(set(scenarios) - set(CONFORMANCE_SCENARIOS))
                    if unknown:
                        return self._json(
                            400,
                            {"error": f"unknown conformance scenarios: {unknown}"},
                        )
                try:
                    report = run_adapter_conformance(
                        adapter_id,
                        scenarios=scenarios,
                        engine_class=AASMEngine,
                    ).to_dict()
                except KeyError as exc:
                    return self._json(404, {"error": str(exc)})
                except Exception as exc:
                    return self._error(exc)
                return self._json(200, report)
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


__all__ = [
    "CSP",
    "LOOPBACK_HOSTS",
    "MAX_ARTIFACT_PREVIEW_CHARS",
    "MAX_BODY_BYTES",
    "make_handler",
    "serve",
    "main",
]
