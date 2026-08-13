from __future__ import annotations
from typing import Callable, Mapping
from .reuse_certificate import ReuseValidation
from .reuse_model import ReuseCandidate, ReuseRequest
from .scopes import scope_flow_allowed

SubsumptionValidator = Callable[[ReuseRequest, ReuseCandidate], bool | tuple[bool, str]]

def validate_reuse_candidate(request: ReuseRequest, candidate: ReuseCandidate, *, scope_state: Mapping, invalid_source_ids: set[str] | None = None, subsumption_validator: SubsumptionValidator | None = None) -> ReuseValidation:
    reasons=[]
    invalid_source_ids=invalid_source_ids or set()
    if candidate.kind != request.kind: reasons.append("kind_mismatch")
    if candidate.source.ref_id in invalid_source_ids: reasons.append("stale_or_invalid_source")
    if not scope_flow_allowed(scope_state,candidate.source.scope_id,request.scope_id): reasons.append("scope_visibility_denied")
    if candidate.source.privacy_level in {"AGENT","USER"} and candidate.source.privacy_principal_id != request.privacy_principal_id: reasons.append("privacy_principal_mismatch")
    if request.environment_fingerprint and request.environment_fingerprint != candidate.environment_fingerprint: reasons.append("environment_mismatch")
    if request.dependency_fingerprints and not set(request.dependency_fingerprints).issubset(set(candidate.dependency_fingerprints)): reasons.append("dependency_fingerprint_mismatch")
    if request.freshness_seconds is not None:
        if request.as_of is None or candidate.created_at is None or request.as_of < candidate.created_at or request.as_of-candidate.created_at > request.freshness_seconds: reasons.append("freshness_requirement_failed")
    if request.effect_class == "NON_IDEMPOTENT_EFFECT" or candidate.effect_class == "NON_IDEMPOTENT_EFFECT": reasons.append("non_idempotent_effect_never_reused")
    if reasons: return ReuseValidation(False,None,tuple(sorted(set(reasons))))
    if request.fingerprint == candidate.request_fingerprint and "EXACT" in candidate.reusable_modes: return ReuseValidation(True,"EXACT")
    if request.fingerprint == candidate.request_fingerprint and request.effect_class == "IDEMPOTENT_WRITE" and "IDEMPOTENT" in candidate.reusable_modes: return ReuseValidation(True,"IDEMPOTENT")
    if "CERTIFIED_EQUIVALENT" in candidate.reusable_modes and candidate.metadata.get("equivalence_certificate_id") and request.semantic_payload == candidate.semantic_payload: return ReuseValidation(True,"CERTIFIED_EQUIVALENT",evidence_ids=tuple(candidate.metadata.get("evidence_ids") or ()))
    if "SUBSUMES" in candidate.reusable_modes:
        if subsumption_validator is None: return ReuseValidation(False,None,("subsumption_validator_required",))
        result=subsumption_validator(request,candidate); ok,reason=(result if isinstance(result,tuple) else (bool(result),""))
        return ReuseValidation(True,"SUBSUMES") if ok else ReuseValidation(False,None,(reason or "subsumption_failed",))
    return ReuseValidation(False,None,("no_sound_reuse_relation",))
