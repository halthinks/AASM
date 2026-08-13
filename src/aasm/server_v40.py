from __future__ import annotations

from . import server_v39 as _v39
from .runtime_v40 import AASMEngine

_v39.AASMEngine = AASMEngine
_v39._v32.AASMEngine = AASMEngine
_v39._v32._v31.AASMEngine = AASMEngine
_v39._v32._v31._v19.AASMEngine = AASMEngine
_v39._v32._v31._v25.AASMEngine = AASMEngine
_v39._v32._v31._v29.AASMEngine = AASMEngine
_v39._v32._v31._v30.AASMEngine = AASMEngine

CSP = _v39.CSP
LOOPBACK_HOSTS = _v39.LOOPBACK_HOSTS
MAX_ARTIFACT_PREVIEW_CHARS = _v39.MAX_ARTIFACT_PREVIEW_CHARS
MAX_BODY_BYTES = _v39.MAX_BODY_BYTES
make_handler = _v39.make_handler
serve = _v39.serve
main = _v39.main

__all__ = ["CSP", "LOOPBACK_HOSTS", "MAX_ARTIFACT_PREVIEW_CHARS", "MAX_BODY_BYTES", "make_handler", "serve", "main"]

if __name__ == "__main__": main()
