from .runtime_v40 import AASMEngine as V40Engine
from ._runtime_v41_metrics import ReuseMetricsRuntimeMixin
from ._runtime_v41_reuse_records import ReuseRecordRuntimeMixin
from ._runtime_v41_reuse_refs import ReuseReferenceRuntimeMixin
from ._runtime_v41_reuse_lookup import ReuseLookupRuntimeMixin
from ._runtime_v41_reuse_certify import ReuseCertificationRuntimeMixin
from ._runtime_v41_reuse_commit import ReuseCommitRuntimeMixin
from ._runtime_v41_solver import SolverLoopRuntimeMixin


class AASMEngine(
    SolverLoopRuntimeMixin,
    ReuseMetricsRuntimeMixin,
    ReuseCommitRuntimeMixin,
    ReuseCertificationRuntimeMixin,
    ReuseLookupRuntimeMixin,
    ReuseReferenceRuntimeMixin,
    ReuseRecordRuntimeMixin,
    V40Engine,
):
    """AASM v0.41 runtime: v0.40 authority plus validated reuse and solver loop."""

    pass
