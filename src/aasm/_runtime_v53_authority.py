from __future__ import annotations

from copy import deepcopy
from typing import Any, Iterable, Mapping

from .evidence import EvidenceRecord
from .scoped_authority import (
    SCOPED_AUTHORITY_CONTRACT_ID,
    SCOPED_IDENTITY_CONTRACT_ID,
    AuthorityDecision,
    AuthorityRequest,
    Principal,
    ScopedAuthorityGrant,
    Workspace,
    evaluate_scoped_authority,
    scoped_authority_contract,
    validate_grant_admission,
)
from .semantic_result import canonical_semantic_json, semantic_fingerprint


SCOPED_AUTHORITY_RUNTIME_CONTRACT_ID = "aasm.authority.scoped.runtime.v1"
SCOPED_AUTHORITY_RUNTIME_CONTRACT_VERSION = "0.1.0"
SCOPED_AUTHORITY_RUNTIME_STABILITY = "FOUNDATION_EXPERIMENTAL"

_AUTHORITY_RECORD_TYPE = "aasm_scoped_authority_record_type"
_AUTHORITY_DOCUMENT = "document"


def scoped_authority_runtime_contract() -> dict[str, Any]:
    return {
        "contract_id": SCOPED_AUTHORITY_RUNTIME_CONTRACT_ID,
        "contract_version": SCOPED_AUTHORITY_RUNTIME_CONTRACT_VERSION,
        "stability": SCOPED_AUTHORITY_RUNTIME_STABILITY,
        "authority_contract_id": SCOPED_AUTHORITY_CONTRACT_ID,
        "identity_contract_id": SCOPED_IDENTITY_CONTRACT_ID,
        "durability": "EXISTING_AASM_EVIDENCE_EVENT_REPLAY",
        "workspace_bootstrap": "EXPLICIT_TRUST_ANCHOR_EVIDENCE_REQUIRED",
        "principal_registration": "SCOPED_IDENTITY_REGISTER_AUTHORIZATION_REQUIRED",
        "grant_admission": "SCOPED_GRANT_VALIDATION_REQUIRED",
        "decision_recording": "ALLOW_AND_DENY_DURABLE",
        "resource_state_grants_authority": False,
        "cross_run_authority_transfer": "NEVER",
    }


def _authority_records(snapshot, record_type: str | None = None):
    rows = []
    for row in snapshot.evidence.get("records", []):
        if row.get("status", "active") != "active":
            continue
        metadata = row.get("metadata") or {}
        value = metadata.get(_AUTHORITY_RECORD_TYPE)
        if not value:
            continue
        if record_type is not None and value != record_type:
            continue
        rows.append(row)
    return rows


def _authority_document(row: Mapping[str, Any]) -> dict[str, Any]:
    metadata = row.get("metadata") or {}
    value = metadata.get(_AUTHORITY_DOCUMENT)
    if not isinstance(value, dict):
        raise ValueError("scoped authority Evidence is missing its canonical document")
    return deepcopy(value)


class ScopedAuthorityRuntimeMixin:
    def scoped_authority_runtime_contract_report(self) -> dict[str, Any]:
        return scoped_authority_runtime_contract()

    def _scope_state_for_authority(self) -> dict[str, Any]:
        return deepcopy(self._begin_calculus()["scope_state"])

    def _authority_evidence_ids(self) -> set[str]:
        return {
            str(row.get("evidence_id"))
            for row in self.snapshot.evidence.get("records", [])
            if row.get("evidence_id")
        }

    def _record_authority_document(
        self,
        *,
        record_type: str,
        object_id: str,
        document: Mapping[str, Any],
        source: str,
        derived_from=(),
        reason: str,
    ) -> str:
        payload = deepcopy(dict(document))
        identity = {
            "record_type": record_type,
            "object_id": str(object_id),
            "document": payload,
        }
        evidence_id = f"scoped-authority-evidence-{semantic_fingerprint(identity)[:24]}"
        for row in _authority_records(self.snapshot):
            if row.get("evidence_id") != evidence_id:
                continue
            metadata = row.get("metadata") or {}
            if metadata.get(_AUTHORITY_RECORD_TYPE) != record_type or metadata.get(_AUTHORITY_DOCUMENT) != payload:
                raise ValueError(f"scoped authority Evidence collision: {evidence_id}")
            return evidence_id
        stored = self.add_evidence(
            EvidenceRecord(
                kind="scoped_authority",
                statement=canonical_semantic_json(payload),
                source=source,
                derived_from=list(sorted(set(map(str, derived_from)))),
                metadata={
                    _AUTHORITY_RECORD_TYPE: record_type,
                    "object_id": str(object_id),
                    _AUTHORITY_DOCUMENT: payload,
                    "authority": "GOVERNANCE_EVIDENCE_ONLY",
                },
                evidence_id=evidence_id,
            ),
            reason=reason,
        )
        return stored.evidence_id

    def _authority_projection(self) -> dict[str, Any]:
        workspaces: dict[str, dict[str, Any]] = {}
        principals_by_workspace: dict[str, dict[str, dict[str, Any]]] = {}
        grants: dict[str, dict[str, Any]] = {}
        decisions: dict[str, dict[str, Any]] = {}

        for row in _authority_records(self.snapshot):
            record_type = (row.get("metadata") or {}).get(_AUTHORITY_RECORD_TYPE)
            document = _authority_document(row)
            if record_type == "workspace_bootstrap":
                workspace = Workspace(**{
                    key: value for key, value in document["workspace"].items() if key != "fingerprint"
                })
                principal = Principal(**{
                    key: value for key, value in document["root_principal"].items() if key != "fingerprint"
                })
                workspaces[workspace.workspace_id] = {
                    "workspace": workspace.to_dict(),
                    "root_principal": principal.to_dict(),
                    "evidence_id": row["evidence_id"],
                    "trust_anchor_evidence_id": document["trust_anchor_evidence_id"],
                }
                principals_by_workspace.setdefault(workspace.workspace_id, {})[principal.principal_id] = {
                    "principal": principal.to_dict(),
                    "evidence_id": row["evidence_id"],
                }
            elif record_type == "principal":
                workspace_id = str(document["workspace_id"])
                principal = Principal(**{
                    key: value for key, value in document["principal"].items() if key != "fingerprint"
                })
                principals_by_workspace.setdefault(workspace_id, {})[principal.principal_id] = {
                    "principal": principal.to_dict(),
                    "evidence_id": row["evidence_id"],
                    "authorized_by_decision_evidence_id": document["authorized_by_decision_evidence_id"],
                }
            elif record_type == "grant":
                grant = ScopedAuthorityGrant.from_dict(document["grant"])
                grants[grant.grant_id] = {
                    "grant": grant.to_dict(),
                    "evidence_id": row["evidence_id"],
                    "admission": deepcopy(document["admission"]),
                }
            elif record_type == "decision":
                request = deepcopy(document["request"])
                decision = deepcopy(document["decision"])
                decisions[str(row["evidence_id"])] = {
                    "request": request,
                    "decision": decision,
                    "evidence_id": row["evidence_id"],
                }

        return {
            "workspaces": workspaces,
            "principals_by_workspace": principals_by_workspace,
            "grants": grants,
            "decisions": decisions,
        }

    def bootstrap_scoped_workspace(
        self,
        root_principal: Principal | Mapping[str, Any],
        workspace: Workspace | Mapping[str, Any],
        *,
        trust_anchor_evidence_id: str,
        reason: str = "scoped workspace trust root bootstrapped",
    ) -> dict[str, Any]:
        principal = root_principal if isinstance(root_principal, Principal) else Principal(**dict(root_principal))
        item = workspace if isinstance(workspace, Workspace) else Workspace(**dict(workspace))
        if item.root_principal_id != principal.principal_id:
            raise ValueError("workspace root_principal_id must match the bootstrapped root principal")
        if item.owner_principal_id != principal.principal_id:
            raise ValueError("initial workspace owner must be the bootstrapped root principal")
        if trust_anchor_evidence_id not in self._authority_evidence_ids():
            raise KeyError(f"unknown trust anchor Evidence: {trust_anchor_evidence_id}")
        projection = self._authority_projection()
        if item.workspace_id in projection["workspaces"]:
            prior = projection["workspaces"][item.workspace_id]
            if prior["workspace"]["fingerprint"] != item.fingerprint or prior["root_principal"]["fingerprint"] != principal.fingerprint:
                raise ValueError(f"workspace identity collision: {item.workspace_id}")
            return {**deepcopy(prior), "already_bootstrapped": True}
        document = {
            "workspace": item.to_dict(),
            "root_principal": principal.to_dict(),
            "trust_anchor_evidence_id": trust_anchor_evidence_id,
        }
        evidence_id = self._record_authority_document(
            record_type="workspace_bootstrap",
            object_id=item.workspace_id,
            document=document,
            source=SCOPED_IDENTITY_CONTRACT_ID,
            derived_from=[trust_anchor_evidence_id],
            reason=reason,
        )
        return {"workspace": item.to_dict(), "root_principal": principal.to_dict(), "evidence_id": evidence_id, "already_bootstrapped": False}

    def _workspace_authority_inputs(self, workspace_id: str) -> tuple[list[Principal], Workspace, list[ScopedAuthorityGrant]]:
        projection = self._authority_projection()
        try:
            workspace_row = projection["workspaces"][workspace_id]
        except KeyError:
            raise KeyError(f"unknown scoped workspace: {workspace_id}") from None
        workspace = Workspace(**{key: value for key, value in workspace_row["workspace"].items() if key != "fingerprint"})
        principal_rows = projection["principals_by_workspace"].get(workspace_id, {})
        principals = [
            Principal(**{key: value for key, value in row["principal"].items() if key != "fingerprint"})
            for row in principal_rows.values()
        ]
        grants = [
            ScopedAuthorityGrant.from_dict(row["grant"])
            for row in projection["grants"].values()
            if row["grant"]["workspace_id"] == workspace_id
        ]
        return principals, workspace, grants

    def evaluate_scoped_request(self, request: AuthorityRequest | Mapping[str, Any]) -> AuthorityDecision:
        item = request if isinstance(request, AuthorityRequest) else AuthorityRequest(**dict(request))
        try:
            principals, workspace, grants = self._workspace_authority_inputs(item.workspace_id)
        except KeyError:
            return AuthorityDecision(item.fingerprint, False, "UNKNOWN_WORKSPACE")
        return evaluate_scoped_authority(
            item,
            principals=principals,
            workspaces=[workspace],
            grants=grants,
            scope_state=self._scope_state_for_authority(),
        )

    def authorize_scoped_request(
        self,
        request: AuthorityRequest | Mapping[str, Any],
        *,
        derived_from=(),
        reason: str = "scoped authority decision recorded",
    ) -> dict[str, Any]:
        item = request if isinstance(request, AuthorityRequest) else AuthorityRequest(**dict(request))
        decision = self.evaluate_scoped_request(item)
        projection = self._authority_projection()
        lineage = list(map(str, derived_from))
        for grant_id in (*decision.allow_grant_ids, *decision.deny_grant_ids):
            row = projection["grants"].get(grant_id)
            if row:
                lineage.append(str(row["evidence_id"]))
        document = {
            "request": item.to_dict(),
            "decision": decision.to_dict(),
        }
        evidence_id = self._record_authority_document(
            record_type="decision",
            object_id=decision.fingerprint,
            document=document,
            source=SCOPED_AUTHORITY_CONTRACT_ID,
            derived_from=lineage,
            reason=reason,
        )
        return {"request": item.to_dict(), "decision": decision.to_dict(), "evidence_id": evidence_id}

    def register_scoped_principal(
        self,
        principal: Principal | Mapping[str, Any],
        *,
        workspace_id: str,
        actor_principal_id: str,
        scope_id: str = "root",
        at_time: float = 0.0,
        reason: str = "scoped principal registered",
    ) -> dict[str, Any]:
        item = principal if isinstance(principal, Principal) else Principal(**dict(principal))
        projection = self._authority_projection()
        existing = projection["principals_by_workspace"].get(workspace_id, {}).get(item.principal_id)
        if existing:
            if existing["principal"]["fingerprint"] != item.fingerprint:
                raise ValueError(f"principal identity collision: {item.principal_id}")
            return {**deepcopy(existing), "already_registered": True}
        authorized = self.authorize_scoped_request(
            AuthorityRequest(actor_principal_id, workspace_id, scope_id, "identity.register", at_time=at_time),
            reason="principal registration authority evaluated",
        )
        if not authorized["decision"]["allowed"]:
            raise PermissionError(f"principal registration denied: {authorized['decision']['reason']}")
        document = {
            "workspace_id": workspace_id,
            "principal": item.to_dict(),
            "authorized_by_decision_evidence_id": authorized["evidence_id"],
        }
        evidence_id = self._record_authority_document(
            record_type="principal",
            object_id=f"{workspace_id}:{item.principal_id}",
            document=document,
            source=SCOPED_IDENTITY_CONTRACT_ID,
            derived_from=[authorized["evidence_id"]],
            reason=reason,
        )
        return {"workspace_id": workspace_id, "principal": item.to_dict(), "evidence_id": evidence_id, "already_registered": False}

    def admit_scoped_authority_grant(
        self,
        grant: ScopedAuthorityGrant | Mapping[str, Any],
        *,
        at_time: float = 0.0,
        reason: str = "scoped authority grant admitted",
    ) -> dict[str, Any]:
        item = grant if isinstance(grant, ScopedAuthorityGrant) else ScopedAuthorityGrant.from_dict(grant)
        projection = self._authority_projection()
        existing = projection["grants"].get(item.grant_id)
        if existing:
            if existing["grant"]["fingerprint"] != item.fingerprint:
                raise ValueError(f"authority grant collision: {item.grant_id}")
            return {**deepcopy(existing), "already_admitted": True}
        principals, workspace, grants = self._workspace_authority_inputs(item.workspace_id)
        admission = validate_grant_admission(
            item,
            principals=principals,
            workspaces=[workspace],
            existing_grants=grants,
            scope_state=self._scope_state_for_authority(),
            at_time=at_time,
        )
        if not admission["valid"]:
            raise PermissionError(f"scoped authority grant rejected: {admission['errors']}")
        lineage = []
        if item.parent_grant_id:
            lineage.append(str(projection["grants"][item.parent_grant_id]["evidence_id"]))
        else:
            lineage.append(str(projection["workspaces"][item.workspace_id]["evidence_id"]))
        document = {"grant": item.to_dict(), "admission": deepcopy(admission)}
        evidence_id = self._record_authority_document(
            record_type="grant",
            object_id=item.grant_id,
            document=document,
            source=SCOPED_AUTHORITY_CONTRACT_ID,
            derived_from=lineage,
            reason=reason,
        )
        return {"grant": item.to_dict(), "admission": admission, "evidence_id": evidence_id, "already_admitted": False}

    def scoped_authority_report(
        self,
        *,
        workspace_id: str,
        scope_id: str | None = None,
    ) -> dict[str, Any]:
        projection = self._authority_projection()
        if workspace_id not in projection["workspaces"]:
            return {
                "contract": scoped_authority_contract(),
                "runtime_contract": scoped_authority_runtime_contract(),
                "workspace_id": workspace_id,
                "scope_id": scope_id,
                "workspace": None,
                "principals": {},
                "grants": {},
                "decisions": {},
            }
        scope_state = self._scope_state_for_authority()
        if scope_id is not None:
            try:
                allowed_scope = lambda grant_scope: __import__("aasm._scopes_graph", fromlist=["scope_flow_allowed"]).scope_flow_allowed(scope_state, grant_scope, scope_id)
            except Exception:
                allowed_scope = lambda grant_scope: False
        else:
            allowed_scope = lambda grant_scope: True
        grants = {
            grant_id: deepcopy(row)
            for grant_id, row in projection["grants"].items()
            if row["grant"]["workspace_id"] == workspace_id and allowed_scope(row["grant"]["scope_id"])
        }
        decisions = {
            evidence_id: deepcopy(row)
            for evidence_id, row in projection["decisions"].items()
            if row["request"]["workspace_id"] == workspace_id
            and (scope_id is None or row["request"]["scope_id"] == scope_id)
        }
        return {
            "contract": scoped_authority_contract(),
            "runtime_contract": scoped_authority_runtime_contract(),
            "workspace_id": workspace_id,
            "scope_id": scope_id,
            "workspace": deepcopy(projection["workspaces"][workspace_id]),
            "principals": deepcopy(projection["principals_by_workspace"].get(workspace_id, {})),
            "grants": grants,
            "decisions": decisions,
        }


__all__ = [
    "SCOPED_AUTHORITY_RUNTIME_CONTRACT_ID",
    "SCOPED_AUTHORITY_RUNTIME_CONTRACT_VERSION",
    "SCOPED_AUTHORITY_RUNTIME_STABILITY",
    "scoped_authority_runtime_contract",
    "ScopedAuthorityRuntimeMixin",
]
