from aasm import AASMEngine, BackendBudget, DecisionRecord, ProblemSpec


engine = AASMEngine(ProblemSpec("Choose a maintenance window and inspection mode"))
for record in [
    DecisionRecord("D-window-early", "window", "early"),
    DecisionRecord("D-window-late", "window", "late"),
    DecisionRecord("D-mode-visual", "mode", "visual"),
    DecisionRecord("D-mode-instrumented", "mode", "instrumented"),
]:
    engine.register_decision(record)

batch = engine.generate_candidate_batch(
    "aasm.finite-domain",
    budget=BackendBudget(max_candidates=4),
)
print("candidates", len(batch["candidates"]))
record = engine.candidate_records(status="ADMISSIBLE")[0]
candidate_id = record["candidate"]["candidate_id"]
engine.select_candidate(candidate_id)
print(engine.activate_candidate(candidate_id)["active_model"])
