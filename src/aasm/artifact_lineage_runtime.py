from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

from .artifact_backends import ArtifactBackend
from .artifact_lineage import (
    ARTIFACT_REVISION_CONTRACT_ID,
    ArtifactRevision,
    artifact_lineage_contract,
    validate_artifact_revision_transition,
)
from .evidence import EvidenceRecord
from .scoped_authority import AuthorityRequest
from .semantic_result import canonical_semantic_json, semantic_fingerprint


ARTIFACT_LINEAGE_RUNTIME_CONTRACT_ID = "aasm.artifact-lineage.runtime.v1"
ARTIFACT_LINEAGE_RUNTIME_CONTRACT_VERSION = "0.1.0"
ARTIFACT_LINEAGE_RUNTIME_STABILITY = "FOUNDATION_EXPERIMENTAL"
ARTIFACT_LINEAGE_CAPABILITIES = {
    "revision_record": "artifact.revision.record",
}

_ARTIFACT_LINEAGE_RECORD_TYPE = "aasm_artifact_lineage_record_type"
_ARTIFACT_LINEAGE_DOCUMENT = "document"
_ARTIFACT_REVISION_RECORD = "ARTIFACT_REVISION"
_ARTIFACT_STORAGE_BINDING_RECORD = "ARTIFACT_STORAGE_BINDING"


def artifact_lineage_runtime_contract() -> dict[str, Any]:
    return {
        "contract_id": ARTIFACT_LINEAGE_RUNTIME_CONTRACT_ID,
        "contract_version": ARTIFACT_LINEAGE_RUNTIME_CONTRACT_VERSION,
        "stability": ARTIFACT_LINEAGE_RUNTIME_STABILITY,
        "model_contract": artifact_lineage_contract(),
        "durability": "EXISTING_AASM_EVIDENCE_EVENT_REPLAY",
        "recording_authority": "EXISTING_AASM_SCOPED_AUTHORITY_ONLY",
        "capabilities": deepcopy(ARTIFACT_LINEAGE_CAPABILITIES),
        "content_verification": "SHA256_OVER_EXPLICIT_BYTES_OR_EXISTING_ARTIFACT_BACKEND_TEXT",
        "semantic_projection_verification": "SHA256_OVER_EXPLICIT_CANONICAL_PROJECTION_BYTES",
        "source_problem_revision": "EXACT_DURABLE_ID_AND_FINGERPRINT_REQUIRED_WHEN_REFERENCED",
        "parent_revision": "EXACT_DURABLE_ID_AND_FINGERPRINT_REQUIRED",
        "storage_rebinding": "APPEND_ONLY_EVIDENCE_BINDING_NOT_REVISION_MUTATION",
        "branching": "EXPLICIT_AND_LEGAL",
        "heads": "QUERY_PROJECTION_ONLY_NOT_ACCEPTANCE_OR_AUTHORITY",
        "newest_revision_authority": "NONE",
        "artifact_acceptance": "NONE_DEFINED_BY_RUNTIME",
        "fact_authority_creation": "NONE",
        "source_trust_creation": "NONE",
        "effect_authorization": "NONE",
        "effect_dispatch": "NONE",
        "state_claim_creation": "NONE",
        "current_artifact_pointer": "NONE",
        "parallel_artifact_registry": "NONE_EVIDENCE_PROJECTION_ONLY",
        "parallel_current_state_store": "NONE",
        "hidden_wall_clock": "NONE",
        "runtime_admission": "PRE_ADMISSION_ONLY",
    }


def _document(row: Mapping[str, Any]) -> dict[str, Any]:
    metadata = dict(row.get("metadata") or {})
    value = metadata.get(_ARTIFACT_LINEAGE_DOCUMENT)
    if isinstance(value, Mapping):
        return deepcopy(dict(value))
    statement = row.get("statement")
    if isinstance(statement, str) and statement:
        parsed = json.loads(statement)
        if isinstance(parsed, Mapping):
            return deepcopy(dict(parsed))
    raise ValueError("artifact-lineage Evidence is missing canonical document")


def _storage_binding_document(item: ArtifactRevision) -> dict[str, Any]:
    return {
        "revision_id": item.revision_id,
        "revision_fingerprint": item.fingerprint,
        "content_sha256": item.content_sha256,
        "artifact_ref": item.artifact_ref,
        "storage_binding_fingerprint": item.storage_binding_fingerprint,
    }


def _validate_storage_binding_document(
    document: Mapping[str, Any],
    revision: ArtifactRevision,
) -> dict[str, Any]:
    payload = deepcopy(dict(document))
    required = {
        "revision_id",
        "revision_fingerprint",
        "content_sha256",
        "artifact_ref",
        "storage_binding_fingerprint",
    }
    if set(payload) != required:
        raise ValueError("artifact storage binding has unexpected or missing fields")
    if str(payload["revision_id"]) != revision.revision_id:
        raise ValueError("artifact storage binding revision_id mismatch")
    if str(payload["revision_fingerprint"]) != revision.fingerprint:
        raise ValueError("artifact storage binding revision fingerprint mismatch")
    if str(payload["content_sha256"]) != revision.content_sha256:
        raise ValueError("artifact storage binding content hash mismatch")
    expected = semantic_fingerprint(
        {
            "contract_id": revision.contract_id,
            "contract_version": revision.contract_version,
            "revision_id": revision.revision_id,
            "content_sha256": revision.content_sha256,
            "artifact_ref": str(payload["artifact_ref"]),
        }
    )
    if str(payload["storage_binding_fingerprint"]) != expected:
        raise ValueError("artifact storage binding fingerprint mismatch")
    return payload


def project_artifact_lineage_evidence(records) -> dict[str, Any]:
    revisions: dict[str, dict[str, Any]] = {}
    pending_bindings: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []

    for index, raw in enumerate(records):
        row = deepcopy(dict(raw))
        metadata = dict(row.get("metadata") or {})
        record_type = metadata.get(_ARTIFACT_LINEAGE_RECORD_TYPE)
        if record_type not in {_ARTIFACT_REVISION_RECORD, _ARTIFACT_STORAGE_BINDING_RECORD}:
            continue
        evidence_id = str(row.get("evidence_id") or "")
        evidence_status = str(row.get("status") or "active")
        try:
            document = _document(row)
            if record_type == _ARTIFACT_REVISION_RECORD:
                item = ArtifactRevision.from_dict(document)
                candidate = {
                    "revision": item.to_dict(),
                    "evidence_id": evidence_id,
                    "evidence_status": evidence_status,
                    "workspace_id": str(metadata.get("workspace_id") or ""),
                    "scope_id": str(metadata.get("scope_id") or ""),
                    "actor_principal_id": str(metadata.get("actor_principal_id") or ""),
                }
                prior = revisions.get(item.revision_id)
                if prior is not None:
                    if prior["revision"]["fingerprint"] != item.fingerprint:
                        raise ValueError(f"artifact revision identity collision: {item.revision_id}")
                    raise ValueError(
                        f"duplicate artifact revision record; use storage binding for rebinding: {item.revision_id}"
                    )
                if metadata.get("object_id") != item.revision_id:
                    raise ValueError(f"artifact-lineage metadata object_id mismatch: {item.revision_id}")
                if metadata.get("object_fingerprint") != item.fingerprint:
                    raise ValueError(f"artifact-lineage metadata fingerprint mismatch: {item.revision_id}")
                revisions[item.revision_id] = candidate
            else:
                pending_bindings.append(
                    {
                        "index": index,
                        "evidence_id": evidence_id,
                        "evidence_status": evidence_status,
                        "document": document,
                    }
                )
        except Exception as exc:
            issues.append(
                {
                    "index": index,
                    "evidence_id": evidence_id,
                    "record_type": record_type,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )

    storage_bindings_by_revision: dict[str, list[dict[str, Any]]] = {
        revision_id: [] for revision_id in revisions
    }
    for revision_id, row in revisions.items():
        item = ArtifactRevision.from_dict(row["revision"])
        if item.artifact_ref:
            storage_bindings_by_revision[revision_id].append(
                {
                    "binding": _storage_binding_document(item),
                    "evidence_id": row["evidence_id"],
                    "evidence_status": row["evidence_status"],
                    "embedded_in_revision_record": True,
                }
            )

    for raw in pending_bindings:
        try:
            revision_id = str(raw["document"].get("revision_id") or "")
            if revision_id not in revisions:
                raise ValueError(f"artifact storage binding references unknown revision: {revision_id}")
            revision = ArtifactRevision.from_dict(revisions[revision_id]["revision"])
            document = _validate_storage_binding_document(raw["document"], revision)
            fingerprint = str(document["storage_binding_fingerprint"])
            prior = next(
                (
                    row
                    for row in storage_bindings_by_revision[revision_id]
                    if row["binding"]["storage_binding_fingerprint"] == fingerprint
                ),
                None,
            )
            if prior is not None and prior["binding"] != document:
                raise ValueError(f"artifact storage binding identity collision: {fingerprint}")
            if prior is None:
                storage_bindings_by_revision[revision_id].append(
                    {
                        "binding": document,
                        "evidence_id": raw["evidence_id"],
                        "evidence_status": raw["evidence_status"],
                        "embedded_in_revision_record": False,
                    }
                )
        except Exception as exc:
            issues.append(
                {
                    "index": raw["index"],
                    "evidence_id": raw["evidence_id"],
                    "record_type": _ARTIFACT_STORAGE_BINDING_RECORD,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )

    graph: dict[str, list[str]] = {}
    children: dict[str, set[str]] = {revision_id: set() for revision_id in revisions}
    roots_by_artifact: dict[str, list[str]] = {}
    for revision_id, row in revisions.items():
        try:
            item = ArtifactRevision.from_dict(row["revision"])
            graph[revision_id] = list(item.parent_revision_ids)
            if not item.parent_revision_ids:
                roots_by_artifact.setdefault(item.logical_artifact_id, []).append(revision_id)
            parent_rows = []
            for parent_id in item.parent_revision_ids:
                parent_row = revisions.get(parent_id)
                if parent_row is None:
                    raise ValueError(f"unknown artifact parent revision: {parent_id}")
                parent = ArtifactRevision.from_dict(parent_row["revision"])
                if item.parent_revision_fingerprints.get(parent_id) != parent.fingerprint:
                    raise ValueError(f"artifact parent fingerprint mismatch: {parent_id}")
                children[parent_id].add(revision_id)
                parent_rows.append(parent)
            if parent_rows:
                validation = validate_artifact_revision_transition(parent_rows, item)
                if not validation["valid"]:
                    raise ValueError(f"invalid artifact revision transition: {validation['errors']}")
        except Exception as exc:
            issues.append(
                {
                    "index": -1,
                    "evidence_id": row["evidence_id"],
                    "record_type": _ARTIFACT_REVISION_RECORD,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )

    for logical_artifact_id, roots in sorted(roots_by_artifact.items()):
        if len(roots) > 1:
            issues.append(
                {
                    "index": -1,
                    "evidence_id": "",
                    "record_type": "LINEAGE",
                    "error": f"ValueError: multiple CREATED roots for logical artifact {logical_artifact_id}: {sorted(roots)}",
                }
            )

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> None:
        if node in visiting:
            raise ValueError(f"artifact revision lineage cycle: {node}")
        if node in visited:
            return
        visiting.add(node)
        for parent in graph.get(node, []):
            if parent in graph:
                visit(parent)
        visiting.remove(node)
        visited.add(node)

    try:
        for node in sorted(graph):
            visit(node)
    except Exception as exc:
        issues.append(
            {
                "index": -1,
                "evidence_id": "",
                "record_type": "LINEAGE",
                "error": f"{type(exc).__name__}: {exc}",
            }
        )

    heads_by_artifact: dict[str, list[str]] = {}
    for revision_id, row in revisions.items():
        item = ArtifactRevision.from_dict(row["revision"])
        if not children.get(revision_id):
            heads_by_artifact.setdefault(item.logical_artifact_id, []).append(revision_id)
    for logical_artifact_id in list(heads_by_artifact):
        heads_by_artifact[logical_artifact_id] = sorted(heads_by_artifact[logical_artifact_id])
    for revision_id in list(storage_bindings_by_revision):
        storage_bindings_by_revision[revision_id] = sorted(
            storage_bindings_by_revision[revision_id],
            key=lambda row: row["binding"]["storage_binding_fingerprint"],
        )

    return {
        "runtime_contract": artifact_lineage_runtime_contract(),
        "valid": not issues,
        "issues": issues,
        "revisions": revisions,
        "storage_bindings_by_revision": storage_bindings_by_revision,
        "heads_by_artifact": heads_by_artifact,
        "head_semantics": "QUERY_PROJECTION_ONLY_NOT_ACCEPTANCE_OR_AUTHORITY",
    }


def _payload_bytes(value: str | bytes, *, label: str) -> bytes:
    if isinstance(value, bytes):
        return value
    if isinstance(value, str):
        return value.encode("utf-8")
    raise TypeError(f"{label} must be str or bytes")


class ArtifactLineageRuntimeMixin:
    """Pre-admission artifact revision runtime over existing Evidence/event replay."""

    def artifact_lineage_runtime_contract_report(self) -> dict[str, Any]:
        return artifact_lineage_runtime_contract()

    def _artifact_lineage_projection(self) -> dict[str, Any]:
        records = self.snapshot.evidence.get("records", []) if isinstance(self.snapshot.evidence, dict) else []
        return project_artifact_lineage_evidence(records)

    def _require_valid_artifact_lineage_projection(self) -> dict[str, Any]:
        report = self._artifact_lineage_projection()
        if not report["valid"]:
            raise RuntimeError(f"invalid durable artifact-lineage projection: {report['issues']}")
        return report

    def _artifact_evidence_row(self, evidence_id: str) -> dict[str, Any]:
        for row in self.snapshot.evidence.get("records", []):
            if str(row.get("evidence_id")) == str(evidence_id):
                return deepcopy(dict(row))
        raise KeyError(evidence_id)

    def _require_active_artifact_evidence_ids(self, evidence_ids: Sequence[str]) -> tuple[str, ...]:
        lineage = self._require_evidence_ids(tuple(sorted(set(map(str, evidence_ids)))))
        inactive = [
            evidence_id
            for evidence_id in lineage
            if str(self._artifact_evidence_row(evidence_id).get("status") or "active") != "active"
        ]
        if inactive:
            raise ValueError(f"artifact revision source Evidence is not active: {inactive}")
        return lineage

    def _authorize_artifact_lineage_record(
        self,
        *,
        actor_principal_id: str,
        workspace_id: str,
        scope_id: str,
        at_time: float,
        derived_from: Sequence[str],
        revision_id: str,
    ) -> dict[str, Any]:
        if not str(actor_principal_id).strip():
            raise PermissionError("artifact-lineage mutation requires actor_principal_id")
        result = self.authorize_scoped_request(
            AuthorityRequest(
                actor_principal_id,
                workspace_id,
                scope_id,
                ARTIFACT_LINEAGE_CAPABILITIES["revision_record"],
                at_time=float(at_time),
                machine_id=self.snapshot.machine_id,
                metadata={"revision_id": revision_id},
            ),
            derived_from=tuple(derived_from),
            reason="artifact-lineage scoped recording authority evaluated",
        )
        if not result["decision"]["allowed"]:
            raise PermissionError(f"artifact-lineage recording denied: {result['decision']['reason']}")
        return result

    def _record_artifact_lineage_document(
        self,
        *,
        record_type: str,
        object_id: str,
        object_fingerprint: str,
        document: Mapping[str, Any],
        workspace_id: str,
        scope_id: str,
        actor_principal_id: str,
        derived_from: Sequence[str],
        reason: str,
    ) -> str:
        payload = deepcopy(dict(document))
        identity = {"record_type": record_type, "object_id": object_id, "document": payload}
        evidence_id = f"artifact-lineage-evidence-{semantic_fingerprint(identity)[:24]}"
        lineage = self._require_evidence_ids(tuple(derived_from))
        for row in self.snapshot.evidence.get("records", []):
            if row.get("evidence_id") != evidence_id:
                continue
            metadata = row.get("metadata") or {}
            if (
                metadata.get(_ARTIFACT_LINEAGE_RECORD_TYPE) != record_type
                or metadata.get(_ARTIFACT_LINEAGE_DOCUMENT) != payload
                or metadata.get("object_id") != object_id
                or metadata.get("object_fingerprint") != object_fingerprint
            ):
                raise ValueError(f"artifact-lineage Evidence collision: {evidence_id}")
            return evidence_id
        record = EvidenceRecord(
            kind="artifact_lineage",
            statement=canonical_semantic_json(payload),
            source=ARTIFACT_REVISION_CONTRACT_ID,
            derived_from=list(lineage),
            metadata={
                _ARTIFACT_LINEAGE_RECORD_TYPE: record_type,
                _ARTIFACT_LINEAGE_DOCUMENT: payload,
                "object_id": object_id,
                "object_fingerprint": object_fingerprint,
                "workspace_id": str(workspace_id),
                "scope_id": str(scope_id),
                "actor_principal_id": str(actor_principal_id),
                "fact_authority_creation": "NONE",
                "source_trust_creation": "NONE",
                "effect_authorization": "NONE",
                "effect_dispatch": "NONE",
                "state_claim_creation": "NONE",
                "artifact_acceptance": "NONE",
                "current_artifact_pointer": "NONE",
            },
            evidence_id=evidence_id,
        )
        self.add_evidence_guarded(
            record,
            expected_machine_version=self.snapshot.version,
            reason=reason,
        )
        return evidence_id

    def _verify_artifact_payloads(
        self,
        item: ArtifactRevision,
        *,
        artifact_backend: ArtifactBackend | None,
        artifact_content: str | bytes | None,
        semantic_projection: str | bytes | None,
    ) -> dict[str, Any]:
        if artifact_backend is not None:
            if not item.artifact_ref:
                raise ValueError("artifact backend verification requires artifact_ref")
            content = artifact_backend.get_text(item.artifact_ref).encode("utf-8")
            content_source = "EXISTING_AASM_ARTIFACT_BACKEND"
        elif artifact_content is not None:
            content = _payload_bytes(artifact_content, label="artifact_content")
            content_source = "EXPLICIT_CALLER_BYTES"
        else:
            raise ValueError("artifact revision recording requires verified artifact content bytes or backend")
        content_digest = sha256(content).hexdigest()
        if content_digest != item.content_sha256:
            raise ValueError("artifact content SHA-256 mismatch")

        if semantic_projection is None:
            raise ValueError("artifact revision recording requires explicit semantic projection bytes")
        projection_bytes = _payload_bytes(semantic_projection, label="semantic_projection")
        projection_digest = sha256(projection_bytes).hexdigest()
        if projection_digest != item.semantic_projection_sha256:
            raise ValueError("artifact semantic projection SHA-256 mismatch")
        return {
            "content_sha256": content_digest,
            "semantic_projection_sha256": projection_digest,
            "content_source": content_source,
        }

    def _artifact_source_problem_revision(self, item: ArtifactRevision) -> dict[str, Any] | None:
        if not item.source_problem_revision_id:
            return None
        report = self.semantic_evolution_report()
        if not report.get("valid", False):
            raise RuntimeError(f"invalid durable semantic-evolution projection: {report.get('issues')}")
        try:
            row = report["revisions"][item.source_problem_revision_id]
        except KeyError:
            raise KeyError(f"unknown durable source problem revision: {item.source_problem_revision_id}") from None
        revision = row["revision"]
        if revision.get("fingerprint") != item.source_problem_revision_fingerprint:
            raise ValueError("artifact source problem revision fingerprint mismatch")
        return deepcopy(row)

    def _artifact_environment_evidence(self, item: ArtifactRevision) -> str | None:
        if not item.environment_id:
            return None
        row = self.execution_environment_report(item.environment_id)
        environment = row["environment"]
        if environment.get("fingerprint") != item.environment_fingerprint:
            raise ValueError("artifact execution environment fingerprint mismatch")
        return str(row["evidence_id"])

    def _record_artifact_storage_binding(
        self,
        item: ArtifactRevision,
        *,
        workspace_id: str,
        scope_id: str,
        actor_principal_id: str,
        derived_from: Sequence[str],
        reason: str,
    ) -> str | None:
        if not item.artifact_ref:
            return None
        projection = self._require_valid_artifact_lineage_projection()
        existing = projection["storage_bindings_by_revision"].get(item.revision_id, [])
        for row in existing:
            if row["binding"]["storage_binding_fingerprint"] == item.storage_binding_fingerprint:
                if row["binding"] != _storage_binding_document(item):
                    raise ValueError("artifact storage binding identity collision")
                return str(row["evidence_id"])
        document = _storage_binding_document(item)
        return self._record_artifact_lineage_document(
            record_type=_ARTIFACT_STORAGE_BINDING_RECORD,
            object_id=f"{item.revision_id}:{item.storage_binding_fingerprint}",
            object_fingerprint=item.storage_binding_fingerprint,
            document=document,
            workspace_id=workspace_id,
            scope_id=scope_id,
            actor_principal_id=actor_principal_id,
            derived_from=derived_from,
            reason=reason,
        )

    def record_artifact_revision(
        self,
        revision: ArtifactRevision | Mapping[str, Any],
        *,
        workspace_id: str,
        scope_id: str,
        actor_principal_id: str,
        artifact_backend: ArtifactBackend | None = None,
        artifact_content: str | bytes | None = None,
        semantic_projection: str | bytes | None = None,
        at_time: float = 0.0,
        evidence_ids: Sequence[str] = (),
        reason: str = "artifact revision recorded",
    ) -> dict[str, Any]:
        item = revision if isinstance(revision, ArtifactRevision) else ArtifactRevision.from_dict(revision)
        verification = self._verify_artifact_payloads(
            item,
            artifact_backend=artifact_backend,
            artifact_content=artifact_content,
            semantic_projection=semantic_projection,
        )
        projection = self._require_valid_artifact_lineage_projection()

        prior = projection["revisions"].get(item.revision_id)
        if prior is not None:
            if prior["revision"]["fingerprint"] != item.fingerprint:
                raise ValueError(f"artifact revision identity collision: {item.revision_id}")
            lineage = self._require_active_artifact_evidence_ids(
                tuple(sorted(set((*map(str, evidence_ids), *item.evidence_ids, str(prior["evidence_id"])))))
            )
            authorization = self._authorize_artifact_lineage_record(
                actor_principal_id=actor_principal_id,
                workspace_id=workspace_id,
                scope_id=scope_id,
                at_time=at_time,
                derived_from=lineage,
                revision_id=item.revision_id,
            )
            full_lineage = tuple(sorted(set((*lineage, str(authorization["evidence_id"])))))
            binding_evidence_id = self._record_artifact_storage_binding(
                item,
                workspace_id=workspace_id,
                scope_id=scope_id,
                actor_principal_id=actor_principal_id,
                derived_from=full_lineage,
                reason=f"artifact storage binding recorded: {item.revision_id}",
            )
            return {
                "revision": deepcopy(prior["revision"]),
                "evidence_id": prior["evidence_id"],
                "storage_binding_evidence_id": binding_evidence_id,
                "authority_decision_evidence_id": authorization["evidence_id"],
                "verification": verification,
                "already_recorded": True,
                "fact_authority_created": False,
                "source_trust_created": False,
                "artifact_accepted": False,
                "current_artifact_selected": False,
                "effect_authorized": False,
                "effect_dispatched": False,
            }

        parents: list[ArtifactRevision] = []
        parent_evidence_ids: list[str] = []
        for parent_id in item.parent_revision_ids:
            try:
                row = projection["revisions"][parent_id]
            except KeyError:
                raise KeyError(f"unknown durable artifact parent revision: {parent_id}") from None
            if row["evidence_status"] != "active":
                raise ValueError(f"artifact parent revision Evidence is not active: {parent_id}")
            parent = ArtifactRevision.from_dict(row["revision"])
            expected_fingerprint = item.parent_revision_fingerprints.get(parent_id)
            if expected_fingerprint != parent.fingerprint:
                raise ValueError(f"artifact parent revision fingerprint mismatch: {parent_id}")
            parents.append(parent)
            parent_evidence_ids.append(str(row["evidence_id"]))

        if parents:
            validation = validate_artifact_revision_transition(parents, item)
            if not validation["valid"]:
                raise ValueError(f"invalid artifact revision transition: {validation['errors']}")
        else:
            existing_roots = [
                revision_id
                for revision_id, row in projection["revisions"].items()
                if row["revision"]["logical_artifact_id"] == item.logical_artifact_id
                and not row["revision"]["parent_revision_ids"]
            ]
            if existing_roots:
                raise ValueError(
                    f"logical artifact already has a durable CREATED root: {item.logical_artifact_id}; roots={sorted(existing_roots)}"
                )

        source_problem = self._artifact_source_problem_revision(item)
        environment_evidence_id = self._artifact_environment_evidence(item)
        lineage_ids = set(map(str, evidence_ids)) | set(map(str, item.evidence_ids)) | set(parent_evidence_ids)
        if source_problem is not None:
            lineage_ids.add(str(source_problem["evidence_id"]))
        if environment_evidence_id:
            lineage_ids.add(environment_evidence_id)
        lineage = self._require_active_artifact_evidence_ids(tuple(sorted(lineage_ids)))

        authorization = self._authorize_artifact_lineage_record(
            actor_principal_id=actor_principal_id,
            workspace_id=workspace_id,
            scope_id=scope_id,
            at_time=at_time,
            derived_from=lineage,
            revision_id=item.revision_id,
        )
        full_lineage = tuple(sorted(set((*lineage, str(authorization["evidence_id"])))))
        evidence_id = self._record_artifact_lineage_document(
            record_type=_ARTIFACT_REVISION_RECORD,
            object_id=item.revision_id,
            object_fingerprint=item.fingerprint,
            document=item.to_dict(),
            workspace_id=workspace_id,
            scope_id=scope_id,
            actor_principal_id=actor_principal_id,
            derived_from=full_lineage,
            reason=reason,
        )
        return {
            "revision": item.to_dict(),
            "evidence_id": evidence_id,
            "storage_binding_evidence_id": evidence_id if item.artifact_ref else None,
            "authority_decision_evidence_id": authorization["evidence_id"],
            "verification": verification,
            "already_recorded": False,
            "fact_authority_created": False,
            "source_trust_created": False,
            "artifact_accepted": False,
            "current_artifact_selected": False,
            "effect_authorized": False,
            "effect_dispatched": False,
        }

    def artifact_revision_report(self, revision_id: str) -> dict[str, Any]:
        projection = self._require_valid_artifact_lineage_projection()
        try:
            row = projection["revisions"][revision_id]
        except KeyError:
            raise KeyError(revision_id) from None
        return {
            **deepcopy(row),
            "storage_bindings": deepcopy(projection["storage_bindings_by_revision"].get(revision_id, [])),
            "head_semantics": projection["head_semantics"],
            "artifact_accepted": False,
            "authoritative": False,
        }

    def artifact_lineage_report(self, logical_artifact_id: str | None = None) -> dict[str, Any]:
        projection = self._artifact_lineage_projection()
        if logical_artifact_id is None:
            return projection
        revisions = {
            revision_id: deepcopy(row)
            for revision_id, row in projection["revisions"].items()
            if row["revision"]["logical_artifact_id"] == logical_artifact_id
        }
        return {
            "runtime_contract": artifact_lineage_runtime_contract(),
            "valid": projection["valid"],
            "issues": deepcopy(projection["issues"]),
            "logical_artifact_id": logical_artifact_id,
            "revisions": revisions,
            "storage_bindings_by_revision": {
                revision_id: deepcopy(projection["storage_bindings_by_revision"].get(revision_id, []))
                for revision_id in revisions
            },
            "heads": deepcopy(projection["heads_by_artifact"].get(logical_artifact_id, [])),
            "head_semantics": projection["head_semantics"],
            "newest_revision_authority": "NONE",
            "artifact_acceptance": "NONE",
        }


__all__ = [
    "ARTIFACT_LINEAGE_RUNTIME_CONTRACT_ID",
    "ARTIFACT_LINEAGE_RUNTIME_CONTRACT_VERSION",
    "ARTIFACT_LINEAGE_RUNTIME_STABILITY",
    "ARTIFACT_LINEAGE_CAPABILITIES",
    "ArtifactLineageRuntimeMixin",
    "artifact_lineage_runtime_contract",
    "project_artifact_lineage_evidence",
]
