from __future__ import annotations

from ._runtime_v53_authority import ScopedAuthorityRuntimeMixin
from .runtime_v52 import AASMEngine as V52Engine


class AASMEngine(ScopedAuthorityRuntimeMixin, V52Engine):
    """Experimental v0.53 runtime: scoped identity and authority over v0.52."""


__all__ = ["AASMEngine"]
