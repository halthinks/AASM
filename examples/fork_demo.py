from aasm import AASMEngine, MachineState, ProblemSpec, SQLiteStore

store = SQLiteStore("aasm-fork-demo.db")
source = AASMEngine(ProblemSpec("Explore two verified plans"), store=store)
source.transition(MachineState.FORMALIZE, "normalized")
boundary = source.events[-1].sequence
source.transition(MachineState.CLASSIFY, "continue source")

alternate = source.fork(boundary)
alternate.transition(MachineState.CLASSIFY, "alternate hypothesis")

print("source:", source.snapshot.machine_id, source.snapshot.state)
print("fork:  ", alternate.snapshot.machine_id, alternate.snapshot.state)
print("lineage:", alternate.snapshot.metadata["lineage"])
store.close()
