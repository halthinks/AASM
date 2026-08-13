from __future__ import annotations

import argparse
import os
from http.server import ThreadingHTTPServer
from urllib.parse import urlparse

from . import server_v19 as _v19, server_v25 as _v25, server_v29 as _v29, server_v30 as _v30
from .control_center_v31 import html_document
from .runtime_v31 import AASMEngine

# Reuse the established authenticated server/store implementation. Only the
# current runtime and generic scope projection are injected.
_v19.AASMEngine = AASMEngine
_v25.AASMEngine = AASMEngine
_v29.AASMEngine = AASMEngine
_v30.AASMEngine = AASMEngine
_v19.html_document = html_document

CSP = _v30.CSP
LOOPBACK_HOSTS = _v30.LOOPBACK_HOSTS
MAX_ARTIFACT_PREVIEW_CHARS = _v30.MAX_ARTIFACT_PREVIEW_CHARS
MAX_BODY_BYTES = _v30.MAX_BODY_BYTES


def make_handler(
    store_target: str,
    token: str | None = None,
    provisioners=None,
    artifacts=None,
    demo_state_path: str | None = None,
):
    base_handler = _v30.make_handler(
        store_target,
        token,
        provisioners,
        artifacts,
        demo_state_path,
    )

    class Handler(base_handler):
        def do_GET(self):
            parsed = urlparse(self.path)
            parts = [part for part in parsed.path.split("/") if part]
            if (
                len(parts) == 4
                and parts[:2] == ["v1", "machines"]
                and parts[3] == "scopes"
            ):
                if not self._auth():
                    return self._json(401, {"error": "unauthorized"})
                store, engine = self._machine(parts[2])
                try:
                    payload = engine.scope_report()
                except Exception as exc:
                    return self._error(exc)
                finally:
                    store.close()
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


__all__ = [
    "CSP",
    "LOOPBACK_HOSTS",
    "MAX_ARTIFACT_PREVIEW_CHARS",
    "MAX_BODY_BYTES",
    "make_handler",
    "serve",
    "main",
]
