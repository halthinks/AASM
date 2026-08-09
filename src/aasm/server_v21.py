from __future__ import annotations

import argparse
import os
from http.server import ThreadingHTTPServer

from . import server_v19 as _base
from .runtime_v21 import AASMEngine

# server_v19 resolves this module global when handling each request. Replacing
# it here upgrades existing endpoints without copying the entire HTTP surface.
_base.AASMEngine = AASMEngine

CSP = _base.CSP
LOOPBACK_HOSTS = _base.LOOPBACK_HOSTS
MAX_ARTIFACT_PREVIEW_CHARS = _base.MAX_ARTIFACT_PREVIEW_CHARS
MAX_BODY_BYTES = _base.MAX_BODY_BYTES


def make_handler(store_target: str, token: str | None = None, provisioners=None, artifacts=None):
    handler = _base.make_handler(store_target, token, provisioners, artifacts)
    handler.server_version = "AASM/0.21"
    return handler


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
