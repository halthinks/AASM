from __future__ import annotations

from typing import Any, Sequence

from .runtime_v31 import AASMEngine as V31Engine, default_profile_registry
from .trace_conformance import (
    project_trace, semantic_trace_check, build_trace_corpus,
    export_provenance, verify_provenance_export, create_selective_provenance_export,
)


class AASMEngine(V31Engine):
    """v0.33 runtime: trace conformance plus signed portable provenance exports."""

    def trace_projection(self) -> dict[str, Any]:
        return project_trace(self.events)

    def semantic_trace_report(self) -> dict[str, Any]:
        return semantic_trace_check(self.events)

    def provenance_export(self, destination: str, *, key: bytes | str, signer_id: str = "local") -> dict[str, Any]:
        return export_provenance(self, destination, key=key, signer_id=signer_id)

    def provenance_verify(self, source: str, *, key: bytes | str, signer_id: str | None = None) -> dict[str, Any]:
        return verify_provenance_export(source, key=key, signer_id=signer_id)

    def provenance_select(self, source: str, destination: str, names: Sequence[str], *, key: bytes | str, signer_id: str = "local") -> dict[str, Any]:
        return create_selective_provenance_export(source, destination, names, key=key, signer_id=signer_id)

    def inspect_machine(self, surface: str = "summary") -> Any:
        if surface == "trace": return self.trace_projection()
        if surface == "trace-semantic": return self.semantic_trace_report()
        if surface == "provenance":
            return {"contract": "aasm.provenance.v1", "exportable": True, "source_trace_sha256": self.trace_projection()["source_trace_sha256"]}
        return super().inspect_machine(surface)


__all__ = ["AASMEngine", "default_profile_registry", "build_trace_corpus"]
