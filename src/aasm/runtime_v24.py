from __future__ import annotations

from copy import deepcopy
from typing import Any

from .assurance import (
    AssurancePolicy,
    CertificateRecord,
    ProjectionCertificateVerifier,
    check_history,
    projection_payload,
)
from .conflict_minimization import ConflictOracle, minimize_conflict_core
from .runtime_v23 import AASMEngine as V23Engine, default_profile_registry


class AASMEngine(V23Engine):
    """v0.24 runtime: independent assurance over learned machine knowledge."""

    def _assurance_state(self) -> dict[str, Any]:
        return deepcopy(getattr(self.snapshot, "assurance_state", {}) or {
            "schema_version": 1,
            "policy": {"require_certificate_for_hard_constraint": True},
            "certificates": {},
            "verifications": {},
            "history_checks": [],
            "minimizations": {},
            "generalizations": {},
        })

    def assurance_report(self) -> dict[str, Any]:
        state = self._assurance_state()
        return {
            "policy": deepcopy(state["policy"]),
            "certificate_count": len(state["certificates"]),
            "verified_certificate_count": sum(
                1 for row in state["certificates"].values() if row.get("status") == "VERIFIED"
            ),
            "verification_count": len(state["verifications"]),
            "history_check_count": len(state["history_checks"]),
            "minimization_count": len(state["minimizations"]),
        }

    def configure_assurance(
        self,
        policy: AssurancePolicy,
        *,
        reason: str = "assurance policy configured",
    ) -> dict[str, Any]:
        state = self._assurance_state()
        state["policy"] = policy.to_dict()
        self.patch_snapshot({"assurance_state": state}, reason)
        return deepcopy(state["policy"])

    def register_projection_certificate(
        self,
        constraint_id: str,
        *,
        certificate_id: str,
        verifier_id: str = "aasm.projection",
        reason: str = "projection certificate registered",
    ) -> dict[str, Any]:
        calculus = self._begin_calculus()
        constraint = calculus["constraints"].get(constraint_id)
        if constraint is None:
            raise KeyError(constraint_id)
        state = self._assurance_state()
        if certificate_id in state["certificates"]:
            raise ValueError(f"certificate already exists: {certificate_id}")
        record = CertificateRecord(
            certificate_id=certificate_id,
            kind="PROJECTION",
            subject_type="LEARNED_CONSTRAINT",
            subject_id=constraint_id,
            payload=projection_payload(constraint),
            verifier_id=verifier_id,
            created_sequence=self._sequence() + 1,
        )
        state["certificates"][certificate_id] = record.to_dict()
        self.patch_snapshot({"assurance_state": state}, reason)
        return deepcopy(state["certificates"][certificate_id])

    def verify_projection_certificate(
        self,
        certificate_id: str,
        *,
        reason: str = "projection certificate independently verified",
    ) -> dict[str, Any]:
        state = self._assurance_state()
        raw = state["certificates"].get(certificate_id)
        if raw is None:
            raise KeyError(certificate_id)
        record = CertificateRecord(
            certificate_id=raw["certificate_id"],
            kind=raw["kind"],
            subject_type=raw["subject_type"],
            subject_id=raw["subject_id"],
            payload=deepcopy(raw["payload"]),
            verifier_id=raw["verifier_id"],
            status=raw["status"],
            scope=deepcopy(raw.get("scope") or {}),
            created_sequence=int(raw.get("created_sequence", 0)),
            verified_sequence=raw.get("verified_sequence"),
        )
        calculus = self._begin_calculus()
        constraint = calculus["constraints"].get(record.subject_id)
        if constraint is None:
            raise KeyError(record.subject_id)
        verifier = ProjectionCertificateVerifier()
        verification = verifier.verify(record, constraint, sequence=self._sequence() + 1)
        state = self._assurance_state()
        state["verifications"][verification.verification_id] = verification.to_dict()
        state["certificates"][certificate_id]["status"] = "VERIFIED" if verification.valid else "REJECTED"
        state["certificates"][certificate_id]["verified_sequence"] = self._sequence() + 1
        state["certificates"][certificate_id]["verification_id"] = verification.verification_id
        self.patch_snapshot({"assurance_state": state}, reason)
        return verification.to_dict()

    def promote_constraint_hard(
        self,
        constraint_id: str,
        certificate_id: str,
        *,
        reason: str = "certified learned constraint promoted to hard",
    ) -> dict[str, Any]:
        state = self._assurance_state()
        certificate = state["certificates"].get(certificate_id)
        if certificate is None or certificate.get("status") != "VERIFIED":
            raise ValueError("hard promotion requires a verified certificate")
        if certificate.get("subject_id") != constraint_id:
            raise ValueError("certificate does not cover the requested constraint")
        calculus = self._begin_calculus()
        constraint = calculus["constraints"].get(constraint_id)
        if constraint is None:
            raise KeyError(constraint_id)
        if certificate.get("payload_fingerprint") != __import__("hashlib").sha256(
            __import__("json").dumps(projection_payload(constraint), sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
        ).hexdigest():
            raise ValueError("constraint changed after certification")
        constraint["strength"] = "HARD"
        constraint["status"] = "ACTIVE"
        constraint["certificate_id"] = certificate_id
        constraint["certification_sequence"] = self._sequence() + 1
        self._commit_calculus(calculus, reason)
        return deepcopy(constraint)

    def check_durable_history(
        self,
        *,
        persist: bool = True,
        reason: str = "durable history checked",
    ) -> dict[str, Any]:
        report = check_history(self.snapshot, self.events)
        if persist:
            state = self._assurance_state()
            state["history_checks"].append(report.to_dict())
            self.patch_snapshot({"assurance_state": state}, reason)
        return report.to_dict()

    def minimize_conflict(
        self,
        conflict_id: str,
        explanation_id: str,
        oracle: ConflictOracle,
        *,
        mode: str = "GREEDY_IRREDUCIBLE",
        max_calls: int = 256,
        adopt: bool = False,
        reason: str = "conflict core minimized",
    ) -> dict[str, Any]:
        calculus = self._begin_calculus()
        conflict = calculus["conflicts"].get(conflict_id)
        explanation = calculus["explanations"].get(explanation_id)
        if conflict is None:
            raise KeyError(conflict_id)
        if explanation is None or explanation.get("conflict_id") != conflict_id:
            raise KeyError(explanation_id)
        result = minimize_conflict_core(
            conflict_id,
            explanation_id,
            explanation.get("assumption_literals") or [],
            oracle,
            mode=mode,
            max_calls=max_calls,
        )
        state = self._assurance_state()
        key = f"{conflict_id}:{explanation_id}:{len(state['minimizations'])}"
        state["minimizations"][key] = result.to_dict()
        self.patch_snapshot({"assurance_state": state}, reason)
        if adopt and result.minimized_literals:
            calculus = self._begin_calculus()
            calculus["explanations"][explanation_id]["assumption_literals"] = deepcopy(result.minimized_literals)
            calculus["explanations"][explanation_id]["minimality"] = result.minimality if result.minimality in {"IRREDUCIBLE", "PROVEN_MINIMAL"} else "NONE"
            self._commit_calculus(calculus, "minimized conflict core adopted")
        return result.to_dict()
