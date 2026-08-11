from __future__ import annotations

from copy import deepcopy
from typing import Any

from .assurance import (
    AssurancePolicy,
    CertificateRecord,
    ProjectionCertificateVerifier,
    assert_hard_constraint_certification,
    check_history,
    fingerprint,
    hard_constraint_certification_issues,
    normalize_assurance_state,
    projection_payload,
)
from .calculus import validate_explanation
from .conflict_minimization import ConflictOracle, minimize_conflict_core
from .runtime_v23 import AASMEngine as V23Engine, default_profile_registry


class AASMEngine(V23Engine):
    """v0.24 runtime: independent assurance over learned machine knowledge."""

    def _assurance_state(self) -> dict[str, Any]:
        return normalize_assurance_state(getattr(self.snapshot, "assurance_state", {}) or {})

    def _assert_assurance_invariants(self, calculus: dict[str, Any]) -> None:
        assert_hard_constraint_certification(
            calculus,
            self._assurance_state(),
            current_sequence=self._sequence() + 1,
        )

    def _validate_calculus_state_for_commit(self, state: dict[str, Any]) -> dict[str, Any]:
        normalized = super()._validate_calculus_state_for_commit(state)
        self._assert_assurance_invariants(normalized)
        return normalized

    def _commit_calculus(self, state: dict[str, Any], reason: str):
        """Enforce assurance on every inherited calculus mutation."""

        normalized = self._validate_calculus_state_for_commit(state)
        self.patch_snapshot({"calculus": normalized}, reason)
        return deepcopy(normalized)

    def learn_constraint(
        self,
        explanation_id: str,
        constraint_id: str,
        *,
        strength: str = "HARD",
        reason: str = "calculus constraint learned",
    ):
        policy = AssurancePolicy.from_dict(self._assurance_state().get("policy"))
        effective_strength = strength
        if strength == "HARD" and policy.require_certificate_for_hard_constraint:
            effective_strength = "SOFT"
        learned = super().learn_constraint(
            explanation_id,
            constraint_id,
            strength=effective_strength,
            reason=reason,
        )
        if strength == "HARD" and effective_strength == "SOFT":
            learned["requested_strength"] = "HARD"
            learned["assurance_status"] = "CERTIFICATE_REQUIRED"
        return learned

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
            "hard_constraint_issues": [
                issue.to_dict()
                for issue in hard_constraint_certification_issues(
                    self._begin_calculus(),
                    state,
                    current_sequence=self._sequence(),
                )
            ],
        }

    def configure_assurance(
        self,
        policy: AssurancePolicy,
        *,
        reason: str = "assurance policy configured",
    ) -> dict[str, Any]:
        state = self._assurance_state()
        proposed = deepcopy(state)
        proposed["policy"] = policy.to_dict()
        assert_hard_constraint_certification(
            self._begin_calculus(),
            proposed,
            current_sequence=self._sequence() + 1,
        )
        self.patch_snapshot({"assurance_state": proposed}, reason)
        return deepcopy(proposed["policy"])

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
            scope=deepcopy(constraint.get("scope") or {}),
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
        state["certificates"][certificate_id]["status"] = (
            "VERIFIED" if verification.valid else "REJECTED"
        )
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
        expected = fingerprint(projection_payload(constraint))
        if certificate.get("payload_fingerprint") != expected:
            raise ValueError("constraint changed after certification")
        verification = state["verifications"].get(certificate.get("verification_id"))
        policy = AssurancePolicy.from_dict(state.get("policy"))
        if verification is None or verification.get("valid") is not True:
            raise ValueError("hard promotion requires an accepted durable verification")
        if verification.get("level") not in policy.accepted_verification_levels:
            raise ValueError(
                f"verification level {verification.get('level')} is not accepted by policy"
            )
        constraint["strength"] = "HARD"
        constraint["status"] = "ACTIVE"
        constraint["certificate_id"] = certificate_id
        constraint["certification_sequence"] = self._sequence() + 1
        constraint.pop("assurance_status", None)
        self._commit_calculus(calculus, reason)
        return deepcopy(constraint)

    def check_durable_history(
        self,
        *,
        persist: bool = True,
        reason: str = "durable history checked",
    ) -> dict[str, Any]:
        refresh = getattr(self, "_refresh_canonical_snapshot", None)
        if refresh is not None:
            refresh()
        report = check_history(self.snapshot, self.events).to_dict()
        if persist:
            state = self._assurance_state()
            recorded = deepcopy(report)
            recorded["recorded_sequence"] = self._sequence() + 1
            state["history_checks"].append(recorded)
            self.patch_snapshot({"assurance_state": state}, reason)
        return report

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

        if adopt:
            if not result.minimized_literals:
                raise ValueError(
                    "an empty minimized core is a root conflict and cannot be adopted as a learned no-good explanation"
                )
            successor_id = (
                f"{explanation_id}.min."
                + fingerprint(result.minimized_literals)[:12]
            )
            existing = calculus["explanations"].get(successor_id)
            if existing is None:
                successor = deepcopy(explanation)
                successor["explanation_id"] = successor_id
                successor["assumption_literals"] = deepcopy(result.minimized_literals)
                successor["minimality"] = (
                    result.minimality
                    if result.minimality in {"IRREDUCIBLE", "PROVEN_MINIMAL"}
                    else "NONE"
                )
                successor["method"] = "DELTA_DEBUGGING"
                successor["created_sequence"] = self._sequence() + 1
                successor_certificate = deepcopy(successor.get("certificate") or {})
                source_lineage = deepcopy(
                    (explanation.get("certificate") or {}).get("aasm_lineage") or {}
                )
                successor_certificate["aasm_lineage"] = {
                    "supersedes_explanation_id": explanation_id,
                    "version": int(source_lineage.get("version", 1)) + 1,
                    "created_sequence": self._sequence() + 1,
                }
                successor["certificate"] = successor_certificate
                validate_explanation(calculus, successor)
                calculus["explanations"][successor_id] = successor
                conflict["explanation_ids"] = sorted(
                    set(conflict.get("explanation_ids", [])) | {successor_id}
                )
            elif existing.get("assumption_literals") != result.minimized_literals:
                raise ValueError("minimized explanation identity collision")
            result.metadata["adopted_explanation_id"] = successor_id
            calculus = self._validate_calculus_state_for_commit(calculus)

        state["minimizations"][key] = result.to_dict()
        patch: dict[str, Any] = {"assurance_state": state}
        if adopt:
            patch["calculus"] = calculus
        self.patch_snapshot(patch, reason)
        return result.to_dict()
