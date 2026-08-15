from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping


_AUTHORITY_RECORD_TYPE = "aasm_scoped_authority_record_type"
_AUTHORITY_DOCUMENT = "document"
_RESOURCE_RECORD_TYPE = "aasm_resource_record_type"
_RESOURCE_DOCUMENT = "document"


def _resource_context(record_type: str, document: Mapping[str, Any]) -> tuple[str | None, str | None]:
    if record_type == "routing_transaction":
        context = document.get("access_context") or {}
        return context.get("workspace_id"), context.get("scope_id")
    return document.get("workspace_id"), document.get("scope_id")


class PrincipalAwareResourceHistoryMixin:
    """Derive v0.53 resource actor history from canonical authority Evidence lineage."""

    def resource_governance_report(self, *, workspace_id=None, scope_id=None):
        report = super().resource_governance_report(workspace_id=workspace_id, scope_id=scope_id)
        decisions: dict[str, dict[str, Any]] = {}
        bindings: dict[str, dict[str, Any]] = {}
        evidence_rows = self.snapshot.evidence.get("records", [])

        for row in evidence_rows:
            if row.get("status", "active") != "active":
                continue
            metadata = row.get("metadata") or {}
            if metadata.get(_AUTHORITY_RECORD_TYPE) != "decision":
                continue
            document = metadata.get(_AUTHORITY_DOCUMENT)
            if isinstance(document, dict):
                decisions[str(row.get("evidence_id"))] = deepcopy(document)

        for row in evidence_rows:
            if row.get("status", "active") != "active":
                continue
            metadata = row.get("metadata") or {}
            if metadata.get(_AUTHORITY_RECORD_TYPE) != "resource_enforcement":
                continue
            document = metadata.get(_AUTHORITY_DOCUMENT)
            if not isinstance(document, dict):
                continue
            if document.get("workspace_id") != workspace_id or document.get("scope_id") != scope_id:
                continue
            for evidence_id in document.get("result_evidence_ids") or []:
                bindings[str(evidence_id)] = {
                    "actor_principal_id": str(document.get("actor_principal_id") or ""),
                    "authority_decision_evidence_id": str(document.get("authority_decision_evidence_id") or ""),
                    "action": str(document.get("action") or ""),
                }

        history: list[dict[str, Any]] = []
        for row in evidence_rows:
            if row.get("status", "active") != "active":
                continue
            metadata = row.get("metadata") or {}
            record_type = metadata.get(_RESOURCE_RECORD_TYPE)
            document = metadata.get(_RESOURCE_DOCUMENT)
            if not record_type or not isinstance(document, dict):
                continue
            row_workspace, row_scope = _resource_context(str(record_type), document)
            if row_workspace != workspace_id or row_scope != scope_id:
                continue
            evidence_id = str(row.get("evidence_id") or "")
            actor = bindings.get(evidence_id)
            if actor is None:
                for parent_id in row.get("derived_from") or []:
                    decision = decisions.get(str(parent_id))
                    if decision is None:
                        continue
                    request = decision.get("request") or {}
                    if request.get("workspace_id") != workspace_id or request.get("scope_id") != scope_id:
                        continue
                    actor = {
                        "actor_principal_id": str(request.get("principal_id") or ""),
                        "authority_decision_evidence_id": str(parent_id),
                        "action": str(request.get("capability") or ""),
                    }
                    break
            if actor is None:
                continue
            history.append({
                "record_type": str(record_type),
                "object_id": str(metadata.get("object_id") or ""),
                "evidence_id": evidence_id,
                "actor_principal_id": actor["actor_principal_id"],
                "authority_decision_evidence_id": actor["authority_decision_evidence_id"],
                "authority_action": actor["action"],
                "derived_from": list(row.get("derived_from") or []),
            })

        report["principal_history"] = history
        report["contract"] = {
            **report["contract"],
            "principal_history": "DERIVED_FROM_SCOPED_AUTHORITY_EVIDENCE",
            "concurrent_commit_guard": "V53_OPTIMISTIC_MACHINE_VERSION_FAIL_CLOSED",
        }
        return report


__all__ = ["PrincipalAwareResourceHistoryMixin"]
