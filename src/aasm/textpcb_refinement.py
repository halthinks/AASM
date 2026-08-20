from __future__ import annotations

"""S5.6 TextPCB qualification adapter for the generic AASM RefinementLoop.

This module is deliberately not a TextPCB refinement runtime.  It provides a
small typed boundary that proves TextPCB evaluators can emit domain findings
and an ordinary ``RefinementProposal`` without acquiring mutation, truth, or
authority powers.  Canonical application remains exclusively in the existing
S5.1 refinement runtime.
"""

from copy import deepcopy
from dataclasses import dataclass, field
import re
from typing import Any, Mapping, Sequence

from .refinement import RefinementProposal, refinement_contract
from .semantic_result import semantic_fingerprint


TEXTPCB_REFINEMENT_QUALIFICATION_CONTRACT_ID = "aasm.textpcb.refinement-qualification.v1"
TEXTPCB_REFINEMENT_QUALIFICATION_CONTRACT_VERSION = "0.1.0"
TEXTPCB_REFINEMENT_STABILITY = "QUALIFICATION_ONLY"
TEXTPCB_REFINEMENT_GATE = "aasm/textpcb-refinement"
TEXTPCB_REQUIRED_REFINEMENT_GATE = "aasm/refinement"
TEXTPCB_REQUIRED_SAFETY_GATE = "aasm/safety-governance"
TEXTPCB_S4_SAFETY_SUITE_FINGERPRINT = "e53391300409d3a18a0dfca88b97c3ba758881228e5b670aecc970b1aa66b5d4"

TEXTPCB_EVALUATOR_DOMAINS = (
    "DRC_ERC",
    "SPICE",
    "EM",
    "THERMAL_PDN",
    "MECHANICAL_MANUFACTURING",
    "EXTERNAL_MEASUREMENT",
    "ARTIFACT_TOOL_FEEDBACK",
)
TEXTPCB_EVALUATOR_RESULTS = ("PASS", "FAIL", "INCONCLUSIVE")
TEXTPCB_INCONCLUSIVE_PROPOSAL_KINDS = ("REQUIRED_OBSERVATION", "VERIFICATION_ESCALATION")

TEXTPCB_REFINEMENT_AUTHORITY_CEILING = {
    "evaluator_output_authority": "NONE",
    "evaluator_direct_problem_mutation": "FORBIDDEN",
    "evaluator_direct_artifact_acceptance": "FORBIDDEN",
    "evaluator_direct_effect_dispatch": "FORBIDDEN",
    "proposal_application_authority": "EXISTING_S5.1_SCOPED_AUTHORITY_ONLY",
    "revision_transition": "EXISTING_SEMANTIC_EVOLUTION_RUNTIME_ONLY",
    "safety_floor": "EXISTING_AASM_SAFETY_GOVERNANCE_ONLY",
    "runtime_admission": "QUALIFICATION_ONLY_NO_RUNTIME_SURFACE",
    "public_admission": "PRE_ADMISSION_ONLY",
}

_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _required(name: str, value: Any) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError(f"TextPCB refinement {name} is required")
    return text


def _optional(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _sha256(name: str, value: Any) -> str:
    text = _required(name, value).lower()
    if not _SHA256.fullmatch(text):
        raise ValueError(f"TextPCB refinement {name} must be a lowercase 64-hex SHA-256 digest")
    return text


def _uniq(values: Sequence[Any], *, name: str, allow_empty: bool = True) -> tuple[str, ...]:
    out = tuple(sorted({_required(name, value) for value in values}))
    if not out and not allow_empty:
        raise ValueError(f"TextPCB refinement requires at least one {name}")
    return out


def _portable(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        return _portable(value.to_dict())
    if isinstance(value, Mapping):
        return {
            str(key): _portable(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (tuple, list, set)):
        return [_portable(item) for item in value]
    if isinstance(value, float):
        raise TypeError("binary floating-point values are forbidden in TextPCB refinement identity")
    if isinstance(value, (str, int, bool)) or value is None:
        return value
    raise TypeError(f"TextPCB refinement value is not portable JSON: {type(value)!r}")


def _portable_rows(values: Sequence[Mapping[str, Any]]) -> tuple[dict[str, Any], ...]:
    rows = tuple(_portable(dict(value)) for value in values)
    return tuple(sorted(rows, key=semantic_fingerprint))


@dataclass(frozen=True)
class TextPCBEvaluatorResult:
    evaluator_id: str
    domain: str
    workspace_id: str
    scope_id: str
    base_revision_id: str
    base_revision_fingerprint: str
    result: str
    evidence_ids: tuple[str, ...]
    counterexamples: tuple[Mapping[str, Any], ...] = ()
    diagnoses: tuple[str, ...] = ()
    artifact_ids: tuple[str, ...] = ()
    proposal: RefinementProposal | Mapping[str, Any] | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    result_id: str = ""

    def __post_init__(self) -> None:
        for name in ("evaluator_id", "workspace_id", "scope_id", "base_revision_id"):
            object.__setattr__(self, name, _required(name, getattr(self, name)))
        domain = _required("domain", self.domain).upper()
        if domain not in TEXTPCB_EVALUATOR_DOMAINS:
            raise ValueError(f"unsupported TextPCB evaluator domain: {domain}")
        object.__setattr__(self, "domain", domain)
        object.__setattr__(
            self,
            "base_revision_fingerprint",
            _sha256("base_revision_fingerprint", self.base_revision_fingerprint),
        )
        result = _required("result", self.result).upper()
        if result not in TEXTPCB_EVALUATOR_RESULTS:
            raise ValueError(f"unsupported TextPCB evaluator result: {result}")
        object.__setattr__(self, "result", result)
        object.__setattr__(self, "evidence_ids", _uniq(self.evidence_ids, name="evidence_id", allow_empty=False))
        object.__setattr__(self, "counterexamples", _portable_rows(self.counterexamples))
        object.__setattr__(self, "diagnoses", _uniq(self.diagnoses, name="diagnosis"))
        object.__setattr__(self, "artifact_ids", _uniq(self.artifact_ids, name="artifact_id"))
        object.__setattr__(self, "metadata", _portable(dict(self.metadata)))

        proposal = self.proposal
        if proposal is not None and not isinstance(proposal, RefinementProposal):
            proposal = RefinementProposal.from_dict(proposal)
        object.__setattr__(self, "proposal", proposal)

        if result == "PASS" and proposal is not None:
            raise ValueError("TextPCB PASS result cannot smuggle a semantic refinement proposal")
        if result == "FAIL" and not self.counterexamples and not self.diagnoses:
            raise ValueError("TextPCB FAIL result requires a counterexample or diagnosis")
        if result == "INCONCLUSIVE" and not self.diagnoses:
            raise ValueError("TextPCB INCONCLUSIVE result requires an explicit diagnosis")

        if proposal is not None:
            if proposal.workspace_id != self.workspace_id or proposal.scope_id != self.scope_id:
                raise ValueError("TextPCB evaluator proposal workspace/scope must exactly match evaluator result")
            if proposal.base_revision_id != self.base_revision_id:
                raise ValueError("TextPCB evaluator proposal base revision ID must exactly match evaluator result")
            if proposal.base_revision_fingerprint != self.base_revision_fingerprint:
                raise ValueError("TextPCB evaluator proposal base revision fingerprint must exactly match evaluator result")
            if proposal.producer_principal_id != self.evaluator_id:
                raise ValueError("TextPCB evaluator must be the producer of its emitted RefinementProposal")
            if not set(self.evidence_ids).issubset(set(proposal.trigger_evidence_ids)):
                raise ValueError("TextPCB evaluator Evidence must be retained as RefinementProposal trigger Evidence")
            if result == "INCONCLUSIVE" and proposal.refinement_kind not in TEXTPCB_INCONCLUSIVE_PROPOSAL_KINDS:
                raise ValueError(
                    "TextPCB INCONCLUSIVE result may only request observation or verification escalation"
                )

        supplied = _optional(self.result_id)
        derived = f"textpcb-evaluator-result-{semantic_fingerprint(self.identity_payload())[:24]}"
        if supplied and supplied != derived:
            raise ValueError("TextPCB evaluator result_id does not match canonical identity")
        object.__setattr__(self, "result_id", derived)

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": TEXTPCB_REFINEMENT_QUALIFICATION_CONTRACT_ID,
            "contract_version": TEXTPCB_REFINEMENT_QUALIFICATION_CONTRACT_VERSION,
            "evaluator_id": self.evaluator_id,
            "domain": self.domain,
            "workspace_id": self.workspace_id,
            "scope_id": self.scope_id,
            "base_revision_id": self.base_revision_id,
            "base_revision_fingerprint": self.base_revision_fingerprint,
            "result": self.result,
            "evidence_ids": list(self.evidence_ids),
            "counterexamples": [_portable(row) for row in self.counterexamples],
            "diagnoses": list(self.diagnoses),
            "artifact_ids": list(self.artifact_ids),
            "proposal": None if self.proposal is None else self.proposal.to_dict(),
            "metadata": _portable(self.metadata),
            "authority_claim": "NONE",
            "artifact_acceptance_claim": "NONE",
            "direct_mutation_capability": "NONE",
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"result_id": self.result_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"result_id": self.result_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "TextPCBEvaluatorResult":
        payload = deepcopy(dict(value))
        supplied = _optional(payload.pop("fingerprint", ""))
        payload.pop("contract_id", None)
        payload.pop("contract_version", None)
        payload.pop("authority_claim", None)
        payload.pop("artifact_acceptance_claim", None)
        payload.pop("direct_mutation_capability", None)
        for name in ("evidence_ids", "counterexamples", "diagnoses", "artifact_ids"):
            payload[name] = tuple(payload.get(name) or ())
        item = cls(**payload)
        if supplied and supplied != item.fingerprint:
            raise ValueError("TextPCB evaluator result fingerprint mismatch")
        return item


def validate_textpcb_evaluator_result(value: TextPCBEvaluatorResult | Mapping[str, Any]) -> dict[str, Any]:
    try:
        item = value if isinstance(value, TextPCBEvaluatorResult) else TextPCBEvaluatorResult.from_dict(value)
    except Exception as exc:
        return {"valid": False, "errors": [f"{type(exc).__name__}: {exc}"], "proposal": None}
    return {
        "valid": True,
        "errors": [],
        "result_id": item.result_id,
        "domain": item.domain,
        "result": item.result,
        "proposal": None if item.proposal is None else item.proposal.to_dict(),
        "proposal_only": item.proposal is not None,
        "authority": "NONE",
        "artifact_acceptance": "NONE",
        "canonical_application_path": (
            "RefinementProposal -> independent RefinementValidation -> existing scoped "
            "problem.refinement.apply authority -> existing ProblemDelta/ProblemRevision transition"
        ),
    }


def textpcb_refinement_contract() -> dict[str, Any]:
    generic = refinement_contract()
    return {
        "contract_id": TEXTPCB_REFINEMENT_QUALIFICATION_CONTRACT_ID,
        "contract_version": TEXTPCB_REFINEMENT_QUALIFICATION_CONTRACT_VERSION,
        "stability": TEXTPCB_REFINEMENT_STABILITY,
        "gate": TEXTPCB_REFINEMENT_GATE,
        "required_refinement_gate": TEXTPCB_REQUIRED_REFINEMENT_GATE,
        "required_safety_gate": TEXTPCB_REQUIRED_SAFETY_GATE,
        "required_s4_safety_suite_fingerprint": TEXTPCB_S4_SAFETY_SUITE_FINGERPRINT,
        "evaluator_domains": list(TEXTPCB_EVALUATOR_DOMAINS),
        "generic_refinement_contract_id": generic["loop_contract_id"],
        "generic_refinement_contract_version": generic["contract_version"],
        "cycle": "DESIGN -> VERIFY -> BUILD/GENERATE -> OPERATE/OBSERVE -> LEARN -> REDESIGN",
        "evaluator_output": "EVIDENCE_COUNTEREXAMPLE_DIAGNOSIS_OPTIONAL_REFINEMENT_PROPOSAL",
        "canonical_mutation": "EXISTING_S5.1_REFINEMENT_RUNTIME_ONLY",
        "authority_ceiling": deepcopy(TEXTPCB_REFINEMENT_AUTHORITY_CEILING),
    }


__all__ = [
    "TEXTPCB_REFINEMENT_QUALIFICATION_CONTRACT_ID",
    "TEXTPCB_REFINEMENT_QUALIFICATION_CONTRACT_VERSION",
    "TEXTPCB_REFINEMENT_STABILITY",
    "TEXTPCB_REFINEMENT_GATE",
    "TEXTPCB_REQUIRED_REFINEMENT_GATE",
    "TEXTPCB_REQUIRED_SAFETY_GATE",
    "TEXTPCB_S4_SAFETY_SUITE_FINGERPRINT",
    "TEXTPCB_EVALUATOR_DOMAINS",
    "TEXTPCB_EVALUATOR_RESULTS",
    "TEXTPCB_INCONCLUSIVE_PROPOSAL_KINDS",
    "TEXTPCB_REFINEMENT_AUTHORITY_CEILING",
    "TextPCBEvaluatorResult",
    "validate_textpcb_evaluator_result",
    "textpcb_refinement_contract",
]
