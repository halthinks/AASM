from __future__ import annotations

from .profile_packages import (
    AASMPackageManifest,
    AASMProfile,
    ProfileEvolutionPolicy,
    ProfileRegistry,
)


def research_profile() -> AASMProfile:
    """Return the built-in offline research-synthesis hero profile."""

    return AASMProfile(
        profile_id="aasm.research-synthesis",
        profile_version="1.0.0",
        description=(
            "Offline-first research and evidence-synthesis profile for causal questions, "
            "explicit evidence contracts, contradiction handling, provenance, and "
            "replayable final artifacts."
        ),
        machine_definition="aasm.default",
        decision_namespaces=["report", "research", "synthesis"],
        obligation_kinds=[
            "artifact",
            "causal_assessment",
            "contradiction_resolution",
            "evidence_extraction",
            "provenance_audit",
            "source_review",
            "steering_requirement",
        ],
        evidence_kinds=[
            "contradiction",
            "provenance_check",
            "resolution",
            "study_claim",
            "study_method",
            "study_result",
        ],
        artifact_kinds=[
            "evidence_matrix",
            "replay_report",
            "synthesis_report",
        ],
        policies={
            "evidence_contracts": {
                "source_review": ["provenance_check"],
                "evidence_extraction": ["study_result"],
                "causal_assessment": ["study_result", "resolution"],
                "contradiction_resolution": ["contradiction", "resolution"],
                "provenance_audit": ["provenance_check"],
                "artifact": ["resolution", "provenance_check"],
            },
            "hard_constraint_certification": ["PROVEN", "VALIDATED"],
            "validation_classifications": [
                "PASS",
                "LOCAL_DEFECT",
                "INFORMATION_GAP",
                "ASSUMPTION_CONFLICT",
                "EVIDENCE_CONFLICT",
                "POLICY_CONFLICT",
                "FATAL",
            ],
            "default_fairness": {
                "max_hidden_epochs": 20,
                "max_lock_age_epochs": 20,
                "max_lock_count": 10,
                "max_deferral_epochs": 5,
                "enforcement": "BLOCK_PLANNING",
                "review_batch_size": 1,
            },
            "default_governance_budget": {
                "max_reviews": 12,
                "max_total_cost": 25.0,
                "require_human_above_risk": "high",
            },
            "default_model_routing": {
                "extraction": "deterministic_fixture",
                "contradiction_resolution": "strongest_available",
                "artifact_generation": "deterministic_fixture",
            },
        },
        capabilities=[
            "causal-backjump",
            "claim-level-provenance",
            "conflict-learning",
            "fixed-corpus-replay",
            "offline-reference-run",
            "selective-steering",
        ],
        evolution_policy=ProfileEvolutionPolicy(
            mode="PROPOSAL_ONLY",
            allow_runtime_proposals=True,
            require_explicit_activation=True,
            require_conformance=True,
            require_migration_for_breaking=True,
            minimum_evidence_count=2,
            allowed_activation_actors=["research-owner"],
            metadata={"hero_profile": True},
        ),
        metadata={
            "hero_profile": True,
            "reference_application": "research-synthesis",
            "offline": True,
            "corpus_id": "aasm-research-corpus-v1",
        },
    )


def research_package() -> AASMPackageManifest:
    """Return the package manifest paired with :func:`research_profile`."""

    profile = research_profile()
    return AASMPackageManifest(
        package_id="aasm.research-synthesis.package",
        package_version="1.0.0",
        description=(
            "Canonical offline research-synthesis hero profile and reference "
            "application for AASM."
        ),
        profiles=[profile.profile_id],
        distribution_name="aasm-runtime",
        authors=["AASM contributors"],
        license="MIT",
        homepage="https://github.com/halthinks/AASM",
        evolution_policy=profile.evolution_policy,
        metadata={
            "built_in": True,
            "hero_profile": True,
            "profile_fingerprint": profile.fingerprint,
            "reference_application": "research-synthesis",
            "corpus_id": "aasm-research-corpus-v1",
        },
    )


class ResearchProfileRegistry(ProfileRegistry):
    """Profile registry that adds the adoption-grade research hero profile."""

    def __init__(self, *, include_builtins: bool = True):
        super().__init__(include_builtins=include_builtins)
        if include_builtins:
            self.register(research_profile(), source="builtin")
