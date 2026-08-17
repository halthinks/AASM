from __future__ import annotations

from copy import deepcopy
import json
from typing import Any, Mapping

from .artifact_lineage_runtime import project_artifact_lineage_evidence
from .entity_evolution import (
    ENTITY_EVOLUTION_CONTRACT_ID,
    EntityEvolution,
    entity_evolution_contract,
)
from .evidence import EvidenceRecord
from .scoped_authority import AuthorityRequest
from .semantic_result import canonical_semantic_json, semantic_fingerprint


ENTITY_EVOLUTION_RUNTIME_CONTRACT_ID = "aasm.entity-evolution.runtime.v1"
ENTITY_EVOLUTION_RUNTIME_CONTRACT_VERSION = "0.1.0"
ENTITY_EVOLUTION_RUNTIME_STABILITY = "FOUNDATION_EXPERIMENTAL"
ENTITY_EVOLUTION_CAPABILITIES = {"evolution_record": "entity.evolution.record"}

_ENTITY_EVOLUTION_RECORD_TYPE = "aasm_entity_evolution_record_type"
_ENTITY_EVOLUTION_DOCUMENT = "document"
_ENTITY_EVOLUTION_RECORD = "ENTITY_EVOLUTION"
_FIREWALL_METADATA = {
    "artifact_authority": "NONE",
    "physical_state_authority": "NONE",
    "external_state_authority": "NONE",
    "fact_authority_creation": "NONE",
    "source_trust_creation": "NONE",
    "effect_authorization": "NONE",
    "effect_dispatch": "NONE",
    "state_claim_creation": "NONE",
    "current_entity_state_pointer": "NONE",
}


def entity_evolution_runtime_contract() -> dict[str, Any]:
    return {
        "contract_id": ENTITY_EVOLUTION_RUNTIME_CONTRACT_ID,
        "contract_version": ENTITY_EVOLUTION_RUNTIME_CONTRACT_VERSION,
        "stability": ENTITY_EVOLUTION_RUNTIME_STABILITY,
        "model_contract": entity_evolution_contract(),
        "durability": "EXISTING_AASM_EVIDENCE_EVENT_REPLAY",
        "recording_authority": "EXISTING_AASM_SCOPED_AUTHORITY_ONLY",
        "capabilities": deepcopy(ENTITY_EVOLUTION_CAPABILITIES),
        "artifact_revision_source": "EXISTING_ARTIFACT_LINEAGE_PROJECTION_ONLY",
        "artifact_revision_binding": "EXACT_ID_AND_FINGERPRINT_REQUIRED",
        "scope_binding": "WORKSPACE_AND_SCOPE_BOUND_TO_DURABLE_EVOLUTION_RECORD",
        "artifact_lineage_relation": "SUCCESSOR_REPRESENTATIONS_REQUIRE_DESCENDANT_ARTIFACT_REVISION_WHEN_PREDECESSORS_EXIST",
        "ambiguity": "RECORDED_EXPLICITLY_AND_FAIL_CLOSED_FOR_HARD_AUTOMATIC_REUSE",
        "history": "APPEND_ONLY_EVIDENCE_PROJECTION",
        "heads": "QUERY_PROJECTION_ONLY_NEVER_CURRENT_STATE_OR_AUTHORITY",
        "artifact_authority": "NONE",
        "physical_state_authority": "NONE",
        "external_state_authority": "NONE",
        "fact_authority_creation": "NONE",
        "source_trust_creation": "NONE",
        "effect_authorization": "NONE",
        "effect_dispatch": "NONE",
        "state_claim_creation": "NONE",
        "current_entity_state_pointer": "NONE",
        "parallel_entity_registry": "NONE_EVIDENCE_PROJECTION_ONLY",
        "parallel_current_state_store": "NONE",
        "hidden_wall_clock": "NONE",
        "runtime_admission": "ACTIVE_ENGINE_CANDIDATE",
    }


def _document(row: Mapping[str, Any]) -> dict[str, Any]:
    metadata = dict(row.get("metadata") or {})
    value = metadata.get(_ENTITY_EVOLUTION_DOCUMENT)
    if isinstance(value, Mapping):
        return deepcopy(dict(value))
    statement = row.get("statement")
    if isinstance(statement, str) and statement:
        parsed = json.loads(statement)
        if isinstance(parsed, Mapping):
            return deepcopy(dict(parsed))
    raise ValueError("entity-evolution Evidence is missing canonical document")


def _expected_evidence_id(object_id: str, document: Mapping[str, Any]) -> str:
    identity = {
        "record_type": _ENTITY_EVOLUTION_RECORD,
        "object_id": str(object_id),
        "document": deepcopy(dict(document)),
    }
    return f"entity-evolution-evidence-{semantic_fingerprint(identity)[:24]}"


def _require_evidence_envelope(
    row: Mapping[str, Any], *, object_id: str, object_fingerprint: str, document: Mapping[str, Any]
) -> None:
    metadata = dict(row.get("metadata") or {})
    if str(row.get("kind") or "") != "entity_evolution":
        raise ValueError("entity-evolution Evidence kind mismatch")
    if str(row.get("source") or "") != ENTITY_EVOLUTION_CONTRACT_ID:
        raise ValueError("entity-evolution Evidence source contract mismatch")
    if metadata.get(_ENTITY_EVOLUTION_RECORD_TYPE) != _ENTITY_EVOLUTION_RECORD:
        raise ValueError("entity-evolution Evidence record type mismatch")
    if metadata.get("object_id") != object_id:
        raise ValueError(f"entity-evolution metadata object_id mismatch: {object_id}")
    if metadata.get("object_fingerprint") != object_fingerprint:
        raise ValueError(f"entity-evolution metadata fingerprint mismatch: {object_id}")
    for key, expected in _FIREWALL_METADATA.items():
        if metadata.get(key) != expected:
            raise ValueError(f"entity-evolution source firewall metadata mismatch: {key}")
    if str(row.get("evidence_id") or "") != _expected_evidence_id(object_id, document):
        raise ValueError(f"entity-evolution deterministic Evidence ID mismatch: {object_id}")
    if str(row.get("statement") or "") != canonical_semantic_json(dict(document)):
        raise ValueError(f"entity-evolution canonical statement mismatch: {object_id}")


def _is_ancestor(artifact_rows: Mapping[str, Any], ancestor_id: str, descendant_id: str) -> bool:
    if ancestor_id == descendant_id:
        return False
    stack = [descendant_id]
    seen: set[str] = set()
    while stack:
        current = stack.pop()
        if current in seen:
            continue
        seen.add(current)
        row = artifact_rows.get(current)
        if row is None:
            continue
        parents = list((row.get("revision") or {}).get("parent_revision_ids") or ())
        if ancestor_id in parents:
            return True
        stack.extend(str(parent) for parent in parents)
    return False


def _representation_key(row: Mapping[str, Any]) -> str:
    return str(row.get("fingerprint") or "")


def project_entity_evolution_evidence(records) -> dict[str, Any]:
    rows = [deepcopy(dict(row)) for row in records]
    evidence_by_id = {
        str(row.get("evidence_id")): row
        for row in rows
        if row.get("evidence_id")
    }
    artifact_projection = project_artifact_lineage_evidence(rows)
    artifact_rows = artifact_projection.get("revisions", {})
    issues: list[dict[str, Any]] = []
    events: dict[str, dict[str, Any]] = {}

    if not artifact_projection.get("valid", False):
        issues.append({
            "index": -1,
            "evidence_id": "",
            "record_type": "ARTIFACT_LINEAGE",
            "error": "ValueError: artifact lineage projection is invalid",
        })

    for index, row in enumerate(rows):
        metadata = dict(row.get("metadata") or {})
        if metadata.get(_ENTITY_EVOLUTION_RECORD_TYPE) != _ENTITY_EVOLUTION_RECORD:
            continue
        evidence_id = str(row.get("evidence_id") or "")
        try:
            document = _document(row)
            item = EntityEvolution.from_dict(document)
            _require_evidence_envelope(
                row,
                object_id=item.evolution_id,
                object_fingerprint=item.fingerprint,
                document=document,
            )
            workspace_id = str(metadata.get("workspace_id") or "")
            scope_id = str(metadata.get("scope_id") or "")
            actor_principal_id = str(metadata.get("actor_principal_id") or "")
            if not workspace_id or not scope_id or not actor_principal_id:
                raise ValueError("entity evolution Evidence requires workspace_id, scope_id, and actor_principal_id")
            prior = events.get(item.evolution_id)
            if prior is not None:
                if prior["evolution"]["fingerprint"] != item.fingerprint:
                    raise ValueError(f"entity evolution identity collision: {item.evolution_id}")
                raise ValueError(f"duplicate entity evolution record: {item.evolution_id}")
            events[item.evolution_id] = {
                "evolution": item.to_dict(),
                "evidence_id": evidence_id,
                "evidence_status": str(row.get("status") or "active"),
                "workspace_id": workspace_id,
                "scope_id": scope_id,
                "actor_principal_id": actor_principal_id,
                "derived_from": tuple(map(str, row.get("derived_from") or ())),
            }
        except Exception as exc:
            issues.append({
                "index": index,
                "evidence_id": evidence_id,
                "record_type": _ENTITY_EVOLUTION_RECORD,
                "error": f"{type(exc).__name__}: {exc}",
            })

    entity_history: dict[str, list[str]] = {}
    ambiguous_entities: set[str] = set()
    representation_edges: dict[str, set[str]] = {}
    successor_representations: dict[str, dict[str, Any]] = {}
    predecessor_representations: set[str] = set()

    for evolution_id, row in events.items():
        try:
            item = EntityEvolution.from_dict(row["evolution"])
            derived_from = set(row["derived_from"])
            if row["evidence_status"] != "active":
                raise ValueError(f"entity evolution Evidence is not active: {evolution_id}")

            if not item.evidence_ids:
                raise ValueError("entity evolution requires at least one source Evidence ID")
            for source_evidence_id in item.evidence_ids:
                source_row = evidence_by_id.get(source_evidence_id)
                if source_row is None:
                    raise KeyError(f"unknown entity evolution source Evidence: {source_evidence_id}")
                if str(source_row.get("status") or "active") != "active":
                    raise ValueError(f"entity evolution source Evidence is not active: {source_evidence_id}")
                if source_evidence_id not in derived_from:
                    raise ValueError(f"entity evolution Evidence missing source Evidence lineage: {source_evidence_id}")

            logical_artifact_ids: set[str] = set()
            predecessor_revision_ids: set[str] = set()
            successor_revision_ids: set[str] = set()
            for role, refs in (("predecessor", item.predecessors), ("successor", item.successors)):
                for ref in refs:
                    artifact_row = artifact_rows.get(ref.artifact_revision_id)
                    if artifact_row is None:
                        raise KeyError(f"unknown artifact revision for entity {role}: {ref.artifact_revision_id}")
                    if artifact_row["workspace_id"] != row["workspace_id"] or artifact_row["scope_id"] != row["scope_id"]:
                        raise PermissionError(f"entity {role} artifact revision is outside requested workspace/scope: {ref.artifact_revision_id}")
                    if artifact_row["evidence_status"] != "active":
                        raise ValueError(f"entity {role} artifact revision Evidence is not active: {ref.artifact_revision_id}")
                    revision = artifact_row["revision"]
                    if str(revision.get("fingerprint") or "") != ref.artifact_revision_fingerprint:
                        raise ValueError(f"entity {role} artifact revision fingerprint mismatch: {ref.artifact_revision_id}")
                    artifact_evidence_id = str(artifact_row["evidence_id"])
                    if artifact_evidence_id not in derived_from:
                        raise ValueError(f"entity evolution Evidence missing artifact revision lineage: {ref.artifact_revision_id}")
                    logical_artifact_ids.add(str(revision.get("logical_artifact_id") or ""))
                    if role == "predecessor":
                        predecessor_revision_ids.add(ref.artifact_revision_id)
                    else:
                        successor_revision_ids.add(ref.artifact_revision_id)

            if len(logical_artifact_ids) > 1:
                raise ValueError("entity evolution references unrelated logical artifact lineages")
            if predecessor_revision_ids and successor_revision_ids:
                for successor_id in successor_revision_ids:
                    if not any(_is_ancestor(artifact_rows, predecessor_id, successor_id) for predecessor_id in predecessor_revision_ids):
                        raise ValueError(
                            f"entity successor artifact revision is not descended from any predecessor revision: {successor_id}"
                        )

            for ref in (*item.predecessors, *item.successors):
                entity_history.setdefault(ref.entity_id, []).append(evolution_id)
            if item.is_ambiguous:
                ambiguous_entities.update(ref.entity_id for ref in (*item.predecessors, *item.successors))

            for predecessor in item.predecessors:
                pred_key = predecessor.fingerprint
                predecessor_representations.add(pred_key)
                representation_edges.setdefault(pred_key, set())
                for successor in item.successors:
                    succ_key = successor.fingerprint
                    if pred_key == succ_key:
                        raise ValueError("entity evolution representation cannot be its own successor")
                    representation_edges[pred_key].add(succ_key)
                    successor_representations[succ_key] = successor.to_dict()
            if not item.predecessors:
                for successor in item.successors:
                    successor_representations[successor.fingerprint] = successor.to_dict()
        except Exception as exc:
            issues.append({
                "index": -1,
                "evidence_id": row["evidence_id"],
                "record_type": _ENTITY_EVOLUTION_RECORD,
                "error": f"{type(exc).__name__}: {exc}",
            })

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> None:
        if node in visiting:
            raise ValueError(f"entity evolution representation cycle: {node}")
        if node in visited:
            return
        visiting.add(node)
        for child in sorted(representation_edges.get(node, ())):
            visit(child)
        visiting.remove(node)
        visited.add(node)

    try:
        for node in sorted(representation_edges):
            visit(node)
    except Exception as exc:
        issues.append({
            "index": -1,
            "evidence_id": "",
            "record_type": "ENTITY_EVOLUTION_GRAPH",
            "error": f"{type(exc).__name__}: {exc}",
        })

    heads_by_entity: dict[str, list[dict[str, Any]]] = {}
    for representation_fingerprint, representation in successor_representations.items():
        if representation_fingerprint in predecessor_representations:
            continue
        heads_by_entity.setdefault(str(representation["entity_id"]), []).append(deepcopy(representation))
    for entity_id in list(heads_by_entity):
        heads_by_entity[entity_id] = sorted(
            heads_by_entity[entity_id],
            key=lambda value: (value["artifact_revision_id"], value["representation_id"], value["fingerprint"]),
        )
    for entity_id in list(entity_history):
        entity_history[entity_id] = sorted(set(entity_history[entity_id]))

    return {
        "valid": not issues,
        "issues": issues,
        "events": dict(sorted(events.items())),
        "entity_history": dict(sorted(entity_history.items())),
        "heads_by_entity": dict(sorted(heads_by_entity.items())),
        "ambiguous_entities": sorted(ambiguous_entities),
        "hard_reuse_blocked_entities": sorted(ambiguous_entities),
        "head_semantics": "QUERY_PROJECTION_ONLY_NEVER_CURRENT_STATE_OR_AUTHORITY",
        "current_entity_state_selected": False,
        "fact_authority_created": False,
        "source_trust_created": False,
        "effect_authorized": False,
        "effect_dispatched": False,
    }


class EntityEvolutionRuntimeMixin:
    """Evidence-backed entity evolution over the existing artifact lineage."""

    def entity_evolution_runtime_contract_report(self) -> dict[str, Any]:
        return entity_evolution_runtime_contract()

    def _entity_evolution_projection(self) -> dict[str, Any]:
        records = self.snapshot.evidence.get("records", []) if isinstance(self.snapshot.evidence, dict) else []
        return project_entity_evolution_evidence(records)

    def _require_valid_entity_evolution_projection(self) -> dict[str, Any]:
        report = self._entity_evolution_projection()
        if not report["valid"]:
            raise ValueError(f"entity evolution projection is invalid: {report['issues']}")
        return report

    def _entity_evidence_row(self, evidence_id: str) -> dict[str, Any]:
        for row in self.snapshot.evidence.get("records", []):
            if str(row.get("evidence_id") or "") == str(evidence_id):
                return deepcopy(row)
        raise KeyError(evidence_id)

    def _authorize_entity_evolution_record(
        self,
        *,
        actor_principal_id: str,
        workspace_id: str,
        scope_id: str,
        at_time: float,
    ) -> dict[str, Any]:
        if not str(actor_principal_id).strip():
            raise PermissionError("entity-evolution mutation requires actor_principal_id")
        result = self.authorize_scoped_request(
            AuthorityRequest(
                actor_principal_id,
                workspace_id,
                scope_id,
                ENTITY_EVOLUTION_CAPABILITIES["evolution_record"],
                at_time=float(at_time),
            ),
            reason="entity evolution recording authority evaluated",
        )
        if not result["decision"]["allowed"]:
            raise PermissionError(f"entity evolution recording denied: {result['decision']['reason']}")
        return result

    def _validate_entity_evolution_inputs(
        self,
        item: EntityEvolution,
        *,
        workspace_id: str,
        scope_id: str,
    ) -> tuple[list[str], list[str]]:
        artifact_projection = self._require_valid_artifact_lineage_projection()
        artifact_rows = artifact_projection["revisions"]
        if not item.evidence_ids:
            raise ValueError("entity evolution requires at least one source Evidence ID")
        source_evidence_ids: list[str] = []
        for evidence_id in item.evidence_ids:
            row = self._entity_evidence_row(evidence_id)
            if str(row.get("status") or "active") != "active":
                raise ValueError(f"entity evolution source Evidence is not active: {evidence_id}")
            source_evidence_ids.append(evidence_id)

        artifact_evidence_ids: list[str] = []
        logical_artifact_ids: set[str] = set()
        predecessor_revision_ids = {ref.artifact_revision_id for ref in item.predecessors}
        successor_revision_ids = {ref.artifact_revision_id for ref in item.successors}
        for role, refs in (("predecessor", item.predecessors), ("successor", item.successors)):
            for ref in refs:
                try:
                    row = artifact_rows[ref.artifact_revision_id]
                except KeyError:
                    raise KeyError(f"unknown artifact revision for entity {role}: {ref.artifact_revision_id}") from None
                if row["workspace_id"] != workspace_id or row["scope_id"] != scope_id:
                    raise PermissionError(f"entity {role} artifact revision is outside requested workspace/scope: {ref.artifact_revision_id}")
                if row["evidence_status"] != "active":
                    raise ValueError(f"entity {role} artifact revision Evidence is not active: {ref.artifact_revision_id}")
                revision = row["revision"]
                if str(revision.get("fingerprint") or "") != ref.artifact_revision_fingerprint:
                    raise ValueError(f"entity {role} artifact revision fingerprint mismatch: {ref.artifact_revision_id}")
                logical_artifact_ids.add(str(revision.get("logical_artifact_id") or ""))
                artifact_evidence_ids.append(str(row["evidence_id"]))
        if len(logical_artifact_ids) > 1:
            raise ValueError("entity evolution references unrelated logical artifact lineages")
        if predecessor_revision_ids and successor_revision_ids:
            for successor_id in successor_revision_ids:
                if not any(_is_ancestor(artifact_rows, predecessor_id, successor_id) for predecessor_id in predecessor_revision_ids):
                    raise ValueError(
                        f"entity successor artifact revision is not descended from any predecessor revision: {successor_id}"
                    )
        return sorted(set(source_evidence_ids)), sorted(set(artifact_evidence_ids))

    def record_entity_evolution(
        self,
        evolution: EntityEvolution | Mapping[str, Any],
        *,
        workspace_id: str,
        scope_id: str,
        actor_principal_id: str,
        at_time: float = 0.0,
        reason: str = "entity evolution recorded",
    ) -> dict[str, Any]:
        item = evolution if isinstance(evolution, EntityEvolution) else EntityEvolution.from_dict(evolution)
        projection = self._require_valid_entity_evolution_projection()
        existing = projection["events"].get(item.evolution_id)
        if existing is not None:
            if existing["evolution"]["fingerprint"] != item.fingerprint:
                raise ValueError(f"entity evolution identity collision: {item.evolution_id}")
            return {
                **deepcopy(existing),
                "already_recorded": True,
                "hard_reuse_allowed": not any(
                    ref.entity_id in projection["hard_reuse_blocked_entities"]
                    for ref in (*item.predecessors, *item.successors)
                ),
                "fact_authority_created": False,
                "effect_authorized": False,
                "effect_dispatched": False,
            }

        source_evidence_ids, artifact_evidence_ids = self._validate_entity_evolution_inputs(
            item,
            workspace_id=workspace_id,
            scope_id=scope_id,
        )
        authorized = self._authorize_entity_evolution_record(
            actor_principal_id=actor_principal_id,
            workspace_id=workspace_id,
            scope_id=scope_id,
            at_time=at_time,
        )
        document = item.to_dict()
        evidence_id = _expected_evidence_id(item.evolution_id, document)
        lineage = sorted(set(source_evidence_ids + artifact_evidence_ids + [str(authorized["evidence_id"])]))
        metadata = {
            _ENTITY_EVOLUTION_RECORD_TYPE: _ENTITY_EVOLUTION_RECORD,
            _ENTITY_EVOLUTION_DOCUMENT: deepcopy(document),
            "object_id": item.evolution_id,
            "object_fingerprint": item.fingerprint,
            "workspace_id": str(workspace_id),
            "scope_id": str(scope_id),
            "actor_principal_id": str(actor_principal_id),
            **_FIREWALL_METADATA,
        }
        candidate = {
            "kind": "entity_evolution",
            "statement": canonical_semantic_json(document),
            "source": ENTITY_EVOLUTION_CONTRACT_ID,
            "confidence": None,
            "supports": [],
            "contradicts": [],
            "derived_from": lineage,
            "metadata": deepcopy(metadata),
            "status": "active",
            "evidence_id": evidence_id,
            "created_at": 0.0,
            "invalidated_at": None,
            "invalidated_reason": None,
        }
        records = list(self.snapshot.evidence.get("records", []))
        preflight = project_entity_evolution_evidence([*records, candidate])
        if not preflight["valid"]:
            raise ValueError(f"entity evolution preflight rejected: {preflight['issues']}")

        record = EvidenceRecord(
            kind="entity_evolution",
            statement=canonical_semantic_json(document),
            source=ENTITY_EVOLUTION_CONTRACT_ID,
            derived_from=lineage,
            metadata=metadata,
            evidence_id=evidence_id,
        )
        self.add_evidence_guarded(record, expected_machine_version=self.snapshot.version, reason=reason)
        final_projection = self._require_valid_entity_evolution_projection()
        stored = final_projection["events"][item.evolution_id]
        hard_reuse_allowed = not any(
            ref.entity_id in final_projection["hard_reuse_blocked_entities"]
            for ref in (*item.predecessors, *item.successors)
        )
        return {
            **deepcopy(stored),
            "already_recorded": False,
            "hard_reuse_allowed": hard_reuse_allowed,
            "artifact_authority_created": False,
            "physical_state_authority_created": False,
            "external_state_authority_created": False,
            "fact_authority_created": False,
            "source_trust_created": False,
            "effect_authorized": False,
            "effect_dispatched": False,
            "current_entity_state_selected": False,
        }

    def entity_evolution_event_report(self, evolution_id: str) -> dict[str, Any]:
        projection = self._require_valid_entity_evolution_projection()
        try:
            row = projection["events"][evolution_id]
        except KeyError:
            raise KeyError(evolution_id) from None
        item = EntityEvolution.from_dict(row["evolution"])
        return {
            **deepcopy(row),
            "hard_reuse_allowed": not any(
                ref.entity_id in projection["hard_reuse_blocked_entities"]
                for ref in (*item.predecessors, *item.successors)
            ),
            "authoritative": False,
            "current_entity_state_selected": False,
        }

    def entity_evolution_report(
        self,
        entity_id: str,
        *,
        workspace_id: str,
        scope_id: str,
    ) -> dict[str, Any]:
        projection = self._require_valid_entity_evolution_projection()
        event_ids = projection["entity_history"].get(str(entity_id), [])
        events = []
        for evolution_id in event_ids:
            row = projection["events"][evolution_id]
            if row["workspace_id"] == workspace_id and row["scope_id"] == scope_id:
                events.append(deepcopy(row))
        ambiguous = str(entity_id) in projection["ambiguous_entities"]
        return {
            "contract": entity_evolution_contract(),
            "runtime_contract": entity_evolution_runtime_contract(),
            "entity_id": str(entity_id),
            "workspace_id": str(workspace_id),
            "scope_id": str(scope_id),
            "events": events,
            "heads": deepcopy(projection["heads_by_entity"].get(str(entity_id), [])),
            "ambiguous": ambiguous,
            "hard_reuse_allowed": not ambiguous,
            "head_semantics": projection["head_semantics"],
            "authoritative": False,
            "current_entity_state_selected": False,
        }

    def entity_evolutions_report(self) -> dict[str, Any]:
        projection = self._require_valid_entity_evolution_projection()
        return {
            "contract": entity_evolution_contract(),
            "runtime_contract": entity_evolution_runtime_contract(),
            **deepcopy(projection),
        }


__all__ = [
    "ENTITY_EVOLUTION_RUNTIME_CONTRACT_ID",
    "ENTITY_EVOLUTION_RUNTIME_CONTRACT_VERSION",
    "ENTITY_EVOLUTION_RUNTIME_STABILITY",
    "ENTITY_EVOLUTION_CAPABILITIES",
    "EntityEvolutionRuntimeMixin",
    "entity_evolution_runtime_contract",
    "project_entity_evolution_evidence",
]
