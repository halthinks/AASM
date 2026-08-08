# Declarative machines and model checking

AASM v0.4 allows the control graph to be defined as data instead of being hard-coded into an agent loop.

A `MachineDefinition` contains a start state, terminal states, and a transition relation. JSON and TOML are supported with the Python standard library. YAML is accepted when PyYAML is installed, but PyYAML is not a core dependency.

```json
{
  "schema_version": 1,
  "name": "verified-build",
  "start_state": "INGEST",
  "terminal_states": ["COMPLETE", "FAIL"],
  "transitions": {
    "INGEST": ["PLAN", "FAIL"],
    "PLAN": ["EXECUTE", "FAIL"],
    "EXECUTE": ["VERIFY", "FAIL"],
    "VERIFY": ["EXECUTE", "COMPLETE", "FAIL"],
    "COMPLETE": [],
    "FAIL": []
  }
}
```

Load and run it with:

```python
from aasm import AASMEngine, MachineDefinition, ProblemSpec

definition = MachineDefinition.load("examples/machine.json")
engine = AASMEngine(ProblemSpec("Build and verify"), definition=definition)
engine.transition("PLAN", "requirements formalized")
```

## Static model checking

`check_machine()` analyzes the transition graph before execution. The current checker reports:

- transition targets that are not defined;
- outgoing edges from terminal states;
- unreachable states;
- reachable non-terminal dead ends;
- reachable states that cannot reach any terminal state;
- machines where no terminal state is reachable from the start.

Run it from the CLI:

```bash
aasm verify-machine examples/machine.json
```

A valid machine exits with status 0. A machine with structural errors exits with status 2 and prints a structured report. Warnings such as unreachable states do not by themselves invalidate a machine.

## Runtime compatibility

The original AASM lifecycle remains the default `MachineDefinition`, so existing `AASMEngine(ProblemSpec(...))` call sites keep the same behavior. Custom state names are allowed; when a state matches the built-in `MachineState` enum, `engine.state` remains enum-compatible, otherwise it is returned as a string.
