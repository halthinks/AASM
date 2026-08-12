from __future__ import annotations

from . import server_v19 as _v19, server_v25 as _v25, server_v27 as _v27
from .control_center_v29 import html_document
from .runtime_v29 import AASMEngine

# Preserve the proven handlers and only replace their injected runtime and HTML
# projection. LangGraph checkpoints never become AASM storage or authority.
_v19.AASMEngine = AASMEngine
_v25.AASMEngine = AASMEngine
_v19.html_document = html_document

CSP = _v27.CSP
LOOPBACK_HOSTS = _v27.LOOPBACK_HOSTS
MAX_ARTIFACT_PREVIEW_CHARS = _v27.MAX_ARTIFACT_PREVIEW_CHARS
MAX_BODY_BYTES = _v27.MAX_BODY_BYTES
make_handler = _v27.make_handler
serve = _v27.serve
main = _v27.main

__all__ = [
    "CSP",
    "LOOPBACK_HOSTS",
    "MAX_ARTIFACT_PREVIEW_CHARS",
    "MAX_BODY_BYTES",
    "make_handler",
    "serve",
    "main",
]
