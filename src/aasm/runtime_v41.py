from .runtime_v40 import AASMEngine as V40Engine
from ._runtime_v41_reuse_records import ReuseRecordRuntimeMixin
from ._runtime_v41_reuse_refs import ReuseReferenceRuntimeMixin
from ._runtime_v41_reuse_lookup import ReuseLookupRuntimeMixin
from ._runtime_v41_reuse_certify import ReuseCertificationRuntimeMixin
from ._runtime_v41_reuse_commit import ReuseCommitRuntimeMixin
from ._runtime_v41_solver import SolverLoopRuntimeMixin
from .evidence import EvidenceRecord
from .reuse_metrics import ReuseMetrics
from .reuse_model import REUSE_CONTRACT_ID
from .semantic_result import canonical_semantic_json, semantic_fingerprint


class AASMEngine(
    SolverLoopRuntimeMixin,
    ReuseCommitRuntimeMixin,
    ReuseCertificationRuntimeMixin,
    ReuseLookupRuntimeMixin,
    ReuseReferenceRuntimeMixin,
    ReuseRecordRuntimeMixin,
    V40Engine,
):
    def record_reuse_metrics(self, metrics, *, actor_id):
        metrics = metrics if isinstance(metrics, ReuseMetrics) else ReuseMetrics(**dict(metrics))
        stored = self.add_evidence(
            EvidenceRecord(
                kind="reuse_metrics",
                statement=canonical_semantic_json(metrics.to_dict()),
                source=REUSE_CONTRACT_ID,
                metadata={
                    "reuse_record_type": "METRICS",
                    "reuse_contract_id": REUSE_CONTRACT_ID,
                    "actor_id": actor_id,
                    "metrics_fingerprint": semantic_fingerprint(metrics.to_dict()),
                },
            ),
            reason="reuse metrics recorded",
        )
        return {"metrics": metrics.to_dict(), "evidence_id": stored.evidence_id}
