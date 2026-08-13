from __future__ import annotations
from pathlib import Path
import pytest
from aasm import (
    AASMEngine, ProblemSpec, SQLiteStore, __version__, build_trace_corpus, project_trace, semantic_trace_check,
    trace_contract, validate_public_api_contract, provenance_contract, export_provenance, verify_provenance_export,
    create_selective_provenance_export, DomainPackage, ProblemDefinition, ProblemModel, ProblemInstance,
    Entity, Predicate, Objective, Operator, Observer, Verifier, build_problem_instance,
    validate_problem_instance, semantic_problem_contract, semantic_problem_document,
)
from aasm.model import Event
from aasm.cli import build_parser

def event(sequence:int,event_type:str,*,data=None)->Event:
    return Event(event_id=f"E{sequence}",ts=float(sequence),event_type=event_type,from_state=None,to_state=None,reason="fixture",data=data or {},machine_id="M1",sequence=sequence)

def test_trace_contract_and_version_are_public():
    assert __version__=="0.35.0"; assert trace_contract()["contract_id"]=="aasm.trace.v1"; assert provenance_contract()["contract_id"]=="aasm.provenance.v1"; assert semantic_problem_contract()["contract_id"]=="aasm.semantic.problem.v1"; assert validate_public_api_contract()["valid"] is True

def test_lossless_projection_preserves_order_identity_and_digests():
    source=[event(1,"machine_created"),event(2,"transition_committed"),event(3,"evidence_added")]; first=project_trace(source); assert first==project_trace(source); assert [s["event_id"] for s in first["steps"]]==["E1","E2","E3"]
def test_unknown_transition_is_explicitly_unsupported_not_dropped(): assert project_trace([event(1,"future_event")])["steps"][0]["support_status"]=="UNSUPPORTED"
def test_snapshot_only_input_is_rejected():
    with pytest.raises(ValueError,match="snapshot-only"): project_trace({"snapshot":{"state":"COMPLETE"}})
def test_semantic_counterexample_links_exact_source_event():
    source=[event(1,"snapshot_patched",data={"semantic_witness":{"pre_state":{"hard":["C1"]},"post_state":{"hard":[]},"properties":{"restart_retains_hard_knowledge":False}}})]; report=semantic_trace_check(source); assert report["status"]=="FAIL"; assert report["issues"][0]["event_id"]=="E1"
def test_trace_corpus_is_deterministic_and_sorted():
    histories={"b":[event(1,"machine_created")],"a":[event(1,"machine_created"),event(2,"transition_committed")]}; first=build_trace_corpus(histories); assert first==build_trace_corpus(histories)
def test_engine_projects_its_actual_durable_history():
    engine=AASMEngine(ProblemSpec("trace me")); assert engine.trace_projection()["event_count"]==len(engine.events)
def test_signed_export_detects_tamper_and_wrong_key(tmp_path:Path):
    engine=AASMEngine(ProblemSpec("portable")); destination=tmp_path/"export"; export_provenance(engine,destination,key=b"secret",signer_id="operator"); assert verify_provenance_export(destination,key=b"secret",signer_id="operator")["valid"] is True; assert verify_provenance_export(destination,key=b"wrong")["valid"] is False; (destination/"events.json").write_bytes((destination/"events.json").read_bytes()+b"tamper"); assert verify_provenance_export(destination,key=b"secret")["valid"] is False
def test_selective_disclosure_retains_parent_manifest_lineage(tmp_path:Path):
    engine=AASMEngine(ProblemSpec("selective")); parent,child=tmp_path/"parent",tmp_path/"child"; export_provenance(engine,parent,key="secret",signer_id="operator"); create_selective_provenance_export(parent,child,["trace.json"],key="secret",signer_id="operator"); report=verify_provenance_export(child,key="secret",signer_id="operator"); assert report["valid"] is True; assert len(report["parent_manifest_sha256"])==64

def semantic_fixture(*,capabilities=True):
    domain=DomainPackage(
        "example.domain","1.0.0",type_registry={"component":{}},predicate_registry=("ready",),
        required_capabilities=("compute",),
        operators=(Operator("make-ready",required_capabilities=("compute",),effects=({"predicate_id":"ready"},)),),
        observers=(Observer("observe-ready",outputs=("ready",)),),verifiers=(Verifier("verify-ready",accepts=("ready",)),),
    )
    definition=ProblemDefinition("example.problem","1.0.0",goal={"predicate_id":"ready","arguments":["component-1"],"value":True},required_entity_kinds=("component",),required_predicates=("ready",))
    model=ProblemModel("example.model","1.0.0",entities=(Entity("component-1","component"),),predicates=(Predicate("ready",1,("component",)),),operators=domain.operators,observers=domain.observers,verifiers=domain.verifiers,objectives=(Objective("goal-ready","ready"),))
    instance=build_problem_instance(domain,definition,model,instance_id="instance-1",decision_variables={"mode":{"domain":["safe","fast"],"value":"safe"}},facts=({"predicate_id":"ready","arguments":["component-1"],"value":False},),capability_bindings={"compute":{"kind":"worker"}} if capabilities else {})
    return domain,definition,model,instance

def test_semantic_problem_fingerprints_are_deterministic_and_model_is_well_formed():
    first=semantic_fixture(); second=semantic_fixture(); assert first[0].fingerprint==second[0].fingerprint; assert first[2].fingerprint==second[2].fingerprint; assert first[3].fingerprint==second[3].fingerprint; assert first[3].compile_status=="SOLVABLE"; assert validate_problem_instance(*first)["valid"] is True

def test_semantic_problem_missing_capability_is_explicit_not_guessed():
    domain,definition,model,instance=semantic_fixture(capabilities=False); assert instance.compile_status=="BLOCKED_MISSING_CAPABILITIES"; assert "capability:compute" in instance.unresolved_specification; assert validate_problem_instance(domain,definition,model,instance)["valid"] is True

def test_semantic_problem_rejects_duplicate_and_unknown_references():
    domain,definition,_,_=semantic_fixture()
    with pytest.raises(ValueError,match="duplicate semantic IDs"): ProblemModel("bad","1",entities=(Entity("x","component"),Entity("x","component")))
    bad=ProblemModel("bad-model","1",entities=(Entity("x","component"),),predicates=(Predicate("ready",1,("component",)),),objectives=(Objective("bad-objective","missing"),))
    assert validate_problem_instance(domain,definition,bad,build_problem_instance(domain,definition,bad,instance_id="bad"))["valid"] is False

def test_semantic_problem_hard_contradiction_is_rejected_before_admission():
    domain,definition,model,_=semantic_fixture(); instance=build_problem_instance(domain,definition,model,instance_id="contradiction",facts=({"predicate_id":"ready","arguments":["component-1"],"value":True},{"predicate_id":"ready","arguments":["component-1"],"value":False}),capability_bindings={"compute":{}}); assert instance.compile_status=="CONTRADICTORY"; engine=AASMEngine(ProblemSpec("reject"));
    with pytest.raises(ValueError,match="semantic problem rejected"): engine.admit_semantic_problem(domain,definition,model,instance)

def test_semantic_problem_admission_is_event_sourced_and_survives_sqlite_resume(tmp_path:Path):
    domain,definition,model,instance=semantic_fixture(); store=SQLiteStore(str(tmp_path/"semantic.db")); engine=AASMEngine(ProblemSpec("semantic"),store=store); machine_id=engine.snapshot.machine_id; before=len(engine.events); report=engine.admit_semantic_problem(domain,definition,model,instance); assert report["configured"] is True; assert len(engine.events)>before; assert engine.inspect_machine("problem")["problem_instance"]["fingerprint"]==instance.fingerprint; store.close(); resumed_store=SQLiteStore(str(tmp_path/"semantic.db")); resumed=AASMEngine.resume(machine_id,resumed_store); assert resumed.semantic_problem_report()["problem_instance"]["fingerprint"]==instance.fingerprint; assert resumed.replay().canonical_hash()==resumed.snapshot.canonical_hash(); resumed_store.close()

def test_semantic_problem_document_is_canonical_and_cli_commands_visible():
    domain,definition,model,instance=semantic_fixture(); document=semantic_problem_document(domain,definition,model,instance); assert document["contract_id"]=="aasm.semantic.problem.v1"; help_text=build_parser().format_help(); assert "semantic-problem-contract" in help_text and "problem-admit" in help_text and "problem" in help_text and "domain" in help_text
