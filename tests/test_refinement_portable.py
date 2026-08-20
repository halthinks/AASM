from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from aasm.refinement_portable import (
    PORTABLE_REFINEMENT_EXCLUDED_ENGINES,
    REFINEMENT_PORTABLE_AUTHORITY_CEILING,
    PortableProblemTransitionRef,
    PortableRefinementBoundary,
    PortableRevisionRef,
    project_portable_refinement_boundary,
    refinement_portable_boundary_contract,
)


R1_FP = "1" * 64
R2_FP = "2" * 64
DELTA_FP = "3" * 64


def _projection() -> dict:
    return {
        "valid": True,
        "issues": [],
        "proposals": {
            "proposal-1": {
                "proposal": {
                    "workspace_id": "workspace-1",
                    "scope_id": "scope-1",
                    "base_revision_id": "revision-1",
                    "trigger_evidence_ids": ["ev-trigger"],
                    "trigger_conflict_ids": ["conflict-1"],
                    "trigger_core_ids": ["core-1"],
                    "expected_semantic_effect": {"impacted_obligation_ids": ["obligation-1"]},
                    "proposed_semantic_payload": {
                        "solver_model": "must-not-cross-portable-boundary",
                        "cad_geometry": {"opaque": True},
                    },
                    "metadata": {"provider": "must-not-cross-portable-boundary"},
                },
                "evidence_id": "ev-proposal",
            },
            "proposal-other-scope": {
                "proposal": {
                    "workspace_id": "workspace-1",
                    "scope_id": "other-scope",
                    "base_revision_id": "revision-1",
                    "trigger_evidence_ids": ["ev-other"],
                    "expected_semantic_effect": {},
                },
                "evidence_id": "ev-other-proposal",
            },
        },
        "validations": {
            "validation-1": {
                "validation": {
                    "proposal_id": "proposal-1",
                    "supporting_evidence_ids": ["ev-validation-support"],
                },
                "evidence_id": "ev-validation",
            }
        },
        "applications": {
            "application-1": {
                "application": {
                    "proposal_id": "proposal-1",
                    "scoped_authorization_evidence_id": "ev-authority",
                    "problem_transition_evidence_id": "ev-transition",
                },
                "evidence_id": "ev-application",
                "truth_impact_evidence_id": "ev-truth-impact",
            }
        },
        "terminations": {
            "termination-1": {
                "termination": {
                    "problem_id": "problem-1",
                    "evidence_ids": ["ev-termination-support"],
                    "blocking_obligation_ids": ["obligation-2"],
                },
                "evidence_id": "ev-termination",
            }
        },
        "semantic_evolution": {
            "valid": True,
            "issues": [],
            "revisions": {
                "revision-1": {"revision": {"revision_id": "revision-1", "problem_id": "problem-1", "fingerprint": R1_FP}},
                "revision-2": {"revision": {"revision_id": "revision-2", "problem_id": "problem-1", "fingerprint": R2_FP}},
                "revision-other": {"revision": {"revision_id": "revision-other", "problem_id": "problem-other", "fingerprint": "4" * 64}},
            },
            "transitions": {
                "delta-1": {
                    "delta": {
                        "delta_id": "delta-1",
                        "base_revision_id": "revision-1",
                        "fingerprint": DELTA_FP,
                        "solver_payload": {"must": "not-port"},
                    },
                    "target_revision": {"revision_id": "revision-2", "problem_id": "problem-1", "fingerprint": R2_FP},
                    "transition_evidence_id": "ev-transition",
                }
            },
        },
    }


def test_projection_carries_only_reference_abi() -> None:
    boundary = project_portable_refinement_boundary(
        _projection(), workspace_id="workspace-1", scope_id="scope-1", problem_id="problem-1"
    )
    payload = boundary.to_dict()
    assert payload["proposal_ids"] == ["proposal-1"]
    assert payload["validation_ids"] == ["validation-1"]
    assert payload["application_ids"] == ["application-1"]
    assert payload["termination_ids"] == ["termination-1"]
    assert payload["obligation_ids"] == ["obligation-1", "obligation-2"]
    assert payload["conflict_ids"] == ["conflict-1"]
    assert payload["core_ids"] == ["core-1"]
    assert payload["embedded_engines"] == []
    assert payload["authority_claim"] == "NONE"
    encoded = json.dumps(payload, sort_keys=True)
    assert "solver_model" not in encoded
    assert "cad_geometry" not in encoded
    assert "solver_payload" not in encoded
    assert "must-not-cross-portable-boundary" not in encoded


def test_evidence_and_transition_lineage_are_preserved() -> None:
    boundary = project_portable_refinement_boundary(
        _projection(), workspace_id="workspace-1", scope_id="scope-1", problem_id="problem-1"
    )
    required = {
        "ev-trigger",
        "ev-proposal",
        "ev-validation-support",
        "ev-validation",
        "ev-authority",
        "ev-transition",
        "ev-application",
        "ev-truth-impact",
        "ev-termination-support",
        "ev-termination",
    }
    assert required.issubset(set(boundary.evidence_ids))
    assert len(boundary.transition_refs) == 1
    transition = boundary.transition_refs[0]
    assert transition.delta_id == "delta-1"
    assert transition.delta_fingerprint == DELTA_FP
    assert transition.base_revision_id == "revision-1"
    assert transition.target_revision_id == "revision-2"
    assert transition.transition_evidence_id == "ev-transition"


def test_round_trip_and_identity_are_deterministic() -> None:
    first = project_portable_refinement_boundary(
        _projection(), workspace_id="workspace-1", scope_id="scope-1", problem_id="problem-1"
    )
    second = PortableRefinementBoundary.from_dict(first.to_dict())
    assert second.to_dict() == first.to_dict()
    assert second.fingerprint == first.fingerprint


def test_schema_accepts_projected_boundary() -> None:
    root = Path(__file__).resolve().parents[1]
    schema = json.loads((root / "schemas" / "refinement-portable-boundary.schema.json").read_text())
    boundary = project_portable_refinement_boundary(
        _projection(), workspace_id="workspace-1", scope_id="scope-1", problem_id="problem-1"
    )
    errors = list(Draft202012Validator(schema).iter_errors(boundary.to_dict()))
    assert errors == []


def test_invalid_durable_projection_fails_closed() -> None:
    projection = _projection()
    projection["valid"] = False
    with pytest.raises(ValueError, match="valid durable refinement report"):
        project_portable_refinement_boundary(
            projection, workspace_id="workspace-1", scope_id="scope-1", problem_id="problem-1"
        )
    projection = _projection()
    projection["semantic_evolution"]["valid"] = False
    with pytest.raises(ValueError, match="valid semantic-evolution history"):
        project_portable_refinement_boundary(
            projection, workspace_id="workspace-1", scope_id="scope-1", problem_id="problem-1"
        )


def test_scope_filter_prevents_cross_scope_refinement_leakage() -> None:
    boundary = project_portable_refinement_boundary(
        _projection(), workspace_id="workspace-1", scope_id="scope-1", problem_id="problem-1"
    )
    assert "proposal-other-scope" not in boundary.proposal_ids
    assert "ev-other" not in boundary.evidence_ids
    assert "ev-other-proposal" not in boundary.evidence_ids


def test_manual_boundary_rejects_unknown_transition_revision() -> None:
    revisions = (PortableRevisionRef("revision-1", R1_FP), PortableRevisionRef("revision-2", R2_FP))
    transition = PortableProblemTransitionRef(
        "delta-1", DELTA_FP, "revision-1", "revision-missing", "ev-transition"
    )
    with pytest.raises(ValueError, match="unknown revision"):
        PortableRefinementBoundary(
            workspace_id="workspace-1",
            scope_id="scope-1",
            problem_id="problem-1",
            revision_refs=revisions,
            evidence_ids=("ev-transition",),
            transition_refs=(transition,),
        )


def test_transport_cannot_claim_authority_or_embed_engines() -> None:
    boundary = project_portable_refinement_boundary(
        _projection(), workspace_id="workspace-1", scope_id="scope-1", problem_id="problem-1"
    )
    payload = boundary.to_dict()
    bad_authority = dict(payload)
    bad_authority["authority_claim"] = "ALLOW"
    with pytest.raises(ValueError, match="cannot carry authority"):
        PortableRefinementBoundary.from_dict(bad_authority)
    bad_engine = dict(payload)
    bad_engine["embedded_engines"] = ["SPICE"]
    with pytest.raises(ValueError, match="cannot embed execution engines"):
        PortableRefinementBoundary.from_dict(bad_engine)


def test_contract_freezes_reference_boundary_not_s6_machine_ir() -> None:
    contract = refinement_portable_boundary_contract()
    assert contract["gate"] == "aasm/refinement"
    assert set(contract["excluded_engines"]) == set(PORTABLE_REFINEMENT_EXCLUDED_ENGINES)
    assert contract["embedded_payloads"] == "NONE_REFERENCE_ONLY"
    assert contract["authority_ceiling"] == REFINEMENT_PORTABLE_AUTHORITY_CEILING
    assert contract["authority_ceiling"]["problem_mutation"] == "NONE"
    assert contract["s6_relationship"] == "REFERENCE_ABI_ONLY_MACHINE_IR_AND_PORTABLE_REDUCER_BEGIN_IN_S6"
