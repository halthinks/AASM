from __future__ import annotations

from . import server_v32 as _v32
from .runtime_v39 import AASMEngine

# Existing HTTP endpoints resume/use the current v0.39 engine even though v0.39
# adds no new HTTP authority path.
_v32.AASMEngine = AASMEngine
_v32._v31.AASMEngine = AASMEngine
_v32._v31._v19.AASMEngine = AASMEngine
_v32._v31._v25.AASMEngine = AASMEngine
_v32._v31._v29.AASMEngine = AASMEngine
_v32._v31._v30.AASMEngine = AASMEngine

CSP = _v32.CSP
LOOPBACK_HOSTS = _v32.LOOPBACK_HOSTS
MAX_ARTIFACT_PREVIEW_CHARS = _v32.MAX_ARTIFACT_PREVIEW_CHARS
MAX_BODY_BYTES = _v32.MAX_BODY_BYTES
make_handler = _v32.make_handler
serve = _v32.serve
main = _v32.main

__all__ = ["CSP", "LOOPBACK_HOSTS", "MAX_ARTIFACT_PREVIEW_CHARS", "MAX_BODY_BYTES", "make_handler", "serve", "main"]

if __name__ == "__main__":
    main()
