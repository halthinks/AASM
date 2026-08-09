"""Domain-neutral package example: a small community-garden field study.

The example deliberately contains no source repository, coding agent, SAT solver,
or Planner/Builder topology. It uses the same AASM kernel contracts.
"""

from aasm import (
    AASMEngine,
    AASMProfile,
    DecisionRecord,
    ObligationRecord,
    ProblemSpec,
    ProducerRef,
    ProfileEvolutionPolicy,
    SemanticResultEnvelope,
)


profile = AASMProfile(
    profile_id="example.garden-study",
    profile_version="1.0.0",
    description="Repeatable evidence contract for a small garden watering study.",
    decision_namespaces=["method"],
    obligation_kinds=["measurement", "review", "work"],
    evidence_kinds=["human_attestation", "measurement", "observation"],
    artifact_kinds=["physical", "record"],
    policies={
        "validation_classifications": [
            "PASS",
            "LOCAL_DEFECT",
            "INFORMATION_GAP",
            "ASSUMPTION_CONFLICT",
            "EVIDENCE_CONFLICT",
            "POLICY_CONFLICT",
            "FATAL",
        ]
    },
    evolution_policy=ProfileEvolutionPolicy(mode="PROPOSAL_ONLY"),
)

engine = AASMEngine(
    ProblemSpec("Determine which watering schedule best supports the garden trial")
)
engine.bind_profile(profile, configuration={"plot_count": 6}, actor="study-owner")

engine.register_decision(
    DecisionRecord("D-schedule", "method.schedule", "soil_triggered")
)
engine.activate_decision("D-schedule")
engine.register_obligation(
    ObligationRecord(
        "O-measure",
        "Record plant measurements after each scheduled observation period",
        activation_condition={
            "decision": {
                "subject": "method.schedule",
                "op": "EQ",
                "value": "soil_triggered",
            }
        },
    )
)
engine.enable_obligation("O-measure")

engine.record_semantic_result(
    SemanticResultEnvelope(
        result_id="result-week-1",
        producer=ProducerRef("human", "garden-team", version="1"),
        subject_ids=["O-measure"],
        classification="PASS",
        summary="Week-one observations were recorded under the selected schedule.",
        observations=[{"plot_count": 6, "measurement_period": "week-1"}],
        evidence=[{"kind": "measurement", "record": "garden-log-week-1"}],
        confidence=1.0,
    )
)

print(engine.profile_report())
print(engine.semantic_results_report())
