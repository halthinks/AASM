import json
from pathlib import Path
import pytest

from aasm import AASMEngine, MachineDefinition, ProblemSpec, check_machine


def valid_definition():
    return MachineDefinition.from_dict({
        "name":"tiny",
        "start_state":"START",
        "terminal_states":["DONE","FAIL"],
        "transitions":{
            "START":["WORK","FAIL"],
            "WORK":["DONE","FAIL"],
            "DONE":[],
            "FAIL":[]
        }
    })


def test_declarative_machine_executes_custom_states():
    definition=valid_definition()
    report=check_machine(definition)
    assert report.valid
    e=AASMEngine(ProblemSpec("custom"),definition=definition)
    assert e.state == "START"
    assert e.allowed() == ["FAIL","WORK"]
    e.transition("WORK","begin")
    e.transition("DONE","finished")
    assert e.state == "DONE"
    with pytest.raises(ValueError):
        e.transition("START","terminal cannot restart")


def test_model_checker_detects_dead_end_and_trapped_cycle():
    definition=MachineDefinition.from_dict({
        "name":"bad",
        "start_state":"A",
        "terminal_states":["DONE"],
        "transitions":{"A":["B"],"B":["A"],"DONE":[],"UNUSED":[]}
    })
    report=check_machine(definition)
    codes={issue.code for issue in report.issues}
    assert not report.valid
    assert "cannot_reach_terminal" in codes
    assert "terminal_unreachable" in codes
    assert "unreachable_state" in codes


def test_machine_definition_loads_json(tmp_path:Path):
    path=tmp_path/"machine.json"
    path.write_text(json.dumps(valid_definition().to_dict()))
    loaded=MachineDefinition.load(path)
    assert loaded == valid_definition()


def test_custom_terminal_not_reported_unfinished():
    from aasm.persistence import MemoryStore
    store=MemoryStore()
    e=AASMEngine(ProblemSpec("custom terminal"),definition=valid_definition(),store=store)
    e.transition("WORK","work")
    e.transition("DONE","done")
    assert e.snapshot.machine_id not in store.list_unfinished()
