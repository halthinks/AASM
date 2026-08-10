from aasm import AASMEngine, DecisionRecord, ObligationRecord, ProblemSpec


engine = AASMEngine(ProblemSpec("Observe a domain-neutral run"))
engine.register_decision(DecisionRecord("D-method", "method", "A"))
engine.activate_decision("D-method")
engine.register_obligation(
    ObligationRecord(
        "O-measure",
        "Collect one observation",
        decision_dependencies=["D-method"],
    )
)
report = engine.observability_report()
print("decision nodes", len(report["decision_graph"]["nodes"]))
print("obligation nodes", len(report["obligation_graph"]["nodes"]))
print("fairness records", len(report["fairness_debt"]))
