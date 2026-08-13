from . import server_v40 as _v40
from .runtime_v41 import AASMEngine

_v40.AASMEngine=AASMEngine
CSP=_v40.CSP
LOOPBACK_HOSTS=_v40.LOOPBACK_HOSTS
MAX_ARTIFACT_PREVIEW_CHARS=_v40.MAX_ARTIFACT_PREVIEW_CHARS
MAX_BODY_BYTES=_v40.MAX_BODY_BYTES
make_handler=_v40.make_handler
serve=_v40.serve
main=_v40.main

__all__=["CSP","LOOPBACK_HOSTS","MAX_ARTIFACT_PREVIEW_CHARS","MAX_BODY_BYTES","make_handler","serve","main"]
