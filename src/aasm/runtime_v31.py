from __future__ import annotations

from .runtime_v30 import AASMEngine as V30Engine, default_profile_registry
from ._runtime_v31_admin import ScopeAdminMixin
from ._runtime_v31_records import ScopeRecordMixin
from ._runtime_v31_activation import ScopeActivationMixin
from ._runtime_v31_recovery import ScopeRecoveryMixin
from ._runtime_v31_search import ScopeSearchMixin
from ._runtime_v31_inspect import ScopeInspectionMixin


class AASMEngine(
    ScopeAdminMixin,
    ScopeRecordMixin,
    ScopeActivationMixin,
    ScopeRecoveryMixin,
    ScopeSearchMixin,
    ScopeInspectionMixin,
    V30Engine,
):
    """v0.31 runtime: hierarchical reasoning inside one authoritative machine."""


__all__ = ["AASMEngine", "default_profile_registry"]
