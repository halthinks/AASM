from __future__ import annotations

from . import server_v31 as _v31
from .runtime_v32 import AASMEngine

_v31.AASMEngine = AASMEngine
_v31._v19.AASMEngine = AASMEngine
_v31._v25.AASMEngine = AASMEngine
_v31._v29.AASMEngine = AASMEngine
_v31._v30.AASMEngine = AASMEngine

CSP = _v31.CSP
LOOPBACK_HOSTS = _v31.LOOPBACK_HOSTS
MAX_ARTIFACT_PREVIEW_CHARS = _v31.MAX_ARTIFACT_PREVIEW_CHARS
MAX_BODY_BYTES = _v31.MAX_BODY_BYTES
make_handler = _v31.make_handler
serve = _v31.serve
main = _v31.main

__all__ = ["CSP", "LOOPBACK_HOSTS", "MAX_ARTIFACT_PREVIEW_CHARS", "MAX_BODY_BYTES", "make_handler", "serve", "main"]

if __name__ == "__main__":
    main()
