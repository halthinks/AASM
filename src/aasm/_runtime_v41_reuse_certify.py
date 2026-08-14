from copy import deepcopy

from .evidence import EvidenceRecord
from .reuse_model import REUSE_CERTIFICATE_CONTRACT_ID, REUSE_CONTRACT_ID
from .semantic_result import canonical_semantic_json, semantic_fingerprint


class ReuseCertificationRuntimeMixin:
    def lookup_reuse(self, request, **kwargs):
        result = super().lookup_reuse(request, **kwargs)
        if not result.get("hit"):
            return result
        candidate = result["candidate"]
        req = result["request"]
        validation = result["validation"]
        registration = self._candidate_registration_evidence_id(candidate["fingerprint"])
        evidence = [registration] if registration else []
        if candidate["source"]["ref_type"] == "EVIDENCE":
            evidence.append(candidate["source"]["ref_id"])
        seed = {
            "request": req["fingerprint"],
            "candidate": candidate["fingerprint"],
            "mode": validation["mode"],
        }
        metadata = {}
        candidate_metadata = deepcopy(candidate.get("metadata") or {})
        if candidate_metadata.get("cross_run"):
            metadata["cross_run"] = {
                "envelope_id": candidate_metadata.get("cross_run_envelope_id"),
                "envelope_fingerprint": candidate_metadata.get("cross_run_envelope_fingerprint"),
                "source_run_id": candidate_metadata.get("source_run_id"),
                "receiving_run_id": candidate_metadata.get("receiving_run_id"),
                "admission_validator_id": candidate_metadata.get("admission_validator_id"),
                "admission_validator_version": candidate_metadata.get("admission_validator_version"),
                "authority_inherited": False,
            }
        result["certificate"] = {
            "certificate_id": "reuse-cert-" + semantic_fingerprint(seed)[:20],
            "request_fingerprint": req["fingerprint"],
            "source": candidate["source"],
            "source_candidate_fingerprint": candidate["fingerprint"],
            "equivalence_mode": validation["mode"],
            "environment_fingerprint": req.get("environment_fingerprint", ""),
            "dependency_fingerprints": req.get("dependency_fingerprints", []),
            "scope_id": req.get("scope_id", "root"),
            "privacy_principal_id": req.get("privacy_principal_id", ""),
            "verifier_ids": [validation.get("validator_id", "aasm.reuse.validator")],
            "evidence_ids": sorted(set(evidence)),
            "valid": True,
            "metadata": metadata,
        }
        result["certificate"]["fingerprint"] = semantic_fingerprint(result["certificate"])
        return result
