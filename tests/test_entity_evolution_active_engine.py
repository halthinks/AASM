from __future__ import annotations

import importlib.util
from pathlib import Path

from aasm import AASMEngine as ActiveEngine
from aasm.entity_evolution_runtime import EntityEvolutionRuntimeMixin


_CORPUS_PATH = Path(__file__).with_name("test_entity_evolution.py")
_SPEC = importlib.util.spec_from_file_location("_aasm_entity_evolution_corpus_active_engine", _CORPUS_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError("unable to load entity-evolution qualification corpus")
corpus = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(corpus)

# Rebind the original qualification helpers so every existing adversarial and
# restart/replay test executes against the exported engine rather than the
# temporary pre-admission composition class.
corpus.EntityEvolutionEngine = ActiveEngine


def test_active_engine_composes_entity_evolution_runtime():
    assert issubclass(ActiveEngine, EntityEvolutionRuntimeMixin)
    assert hasattr(ActiveEngine, "record_entity_evolution")
    assert hasattr(ActiveEngine, "entity_evolution_report")
    assert hasattr(ActiveEngine, "entity_evolutions_report")


for _name in dir(corpus):
    if _name.startswith("test_"):
        globals()[f"test_active_engine_corpus_{_name[5:]}"] = getattr(corpus, _name)
