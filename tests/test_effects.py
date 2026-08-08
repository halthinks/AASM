from pathlib import Path
import os
import subprocess
import sys

import pytest

from aasm import (
    AASMEngine,
    EffectExecutionError,
    EffectSpec,
    EffectStatus,
    EffectUnknownOutcome,
    ProblemSpec,
    RetryPolicy,
    SQLiteStore,
)


def test_successful_effect_is_not_executed_twice():
    e=AASMEngine(ProblemSpec("effect dedupe"))
    calls=[]
    spec=EffectSpec("write", {"value": 1}, idempotency_key="stable-key")
    record=e.propose_effect(spec)
    e.authorize_effect(record.spec.effect_id)
    def executor(spec,key):
        calls.append((spec.effect_type,key))
        return {"ok": True}
    first=e.execute_effect(record.spec.effect_id,executor)
    second=e.execute_effect(record.spec.effect_id,executor)
    assert first.status == EffectStatus.SUCCEEDED.value
    assert second.status == EffectStatus.SUCCEEDED.value
    assert len(calls) == 1


def test_same_idempotency_key_returns_original_effect():
    e=AASMEngine(ProblemSpec("idempotency"))
    one=e.propose_effect(EffectSpec("api", idempotency_key="request-42"))
    two=e.propose_effect(EffectSpec("api", idempotency_key="request-42"))
    assert one.spec.effect_id == two.spec.effect_id


def test_failed_effect_retries_with_same_idempotency_key():
    e=AASMEngine(ProblemSpec("retry"))
    rec=e.propose_effect(EffectSpec("api", idempotency_key="stable", retry_policy=RetryPolicy(max_attempts=2,retry_on_failure=True)))
    e.authorize_effect(rec.spec.effect_id)
    keys=[]
    def executor(spec,key):
        keys.append(key)
        if len(keys)==1:
            raise RuntimeError("temporary")
        return {"attempt": len(keys)}
    failed=e.execute_effect(rec.spec.effect_id,executor)
    assert failed.status == EffectStatus.FAILED.value
    succeeded=e.execute_effect(rec.spec.effect_id,executor)
    assert succeeded.status == EffectStatus.SUCCEEDED.value
    assert keys == ["stable","stable"]


def test_sqlite_effect_execution_has_single_owner_across_connections(tmp_path:Path):
    from threading import Event, Thread

    db=tmp_path/"single-owner.db"
    first_store=SQLiteStore(db)
    first=AASMEngine(ProblemSpec("single effect owner"),store=first_store)
    rec=first.propose_effect(EffectSpec("external-write",idempotency_key="single-owner"))
    first.authorize_effect(rec.spec.effect_id)
    mid=first.snapshot.machine_id

    second_store=SQLiteStore(db)
    second=AASMEngine.resume(mid,second_store)
    entered=Event(); release=Event(); calls=[]; result_box={}; error_box={}

    def first_executor(spec,key):
        calls.append("first")
        entered.set()
        if not release.wait(10):
            raise TimeoutError("test executor was not released")
        return {"owner":"first"}

    def run_first():
        try:
            result_box["record"]=first.execute_effect(rec.spec.effect_id,first_executor)
        except Exception as exc:
            error_box["error"]=exc

    thread=Thread(target=run_first,daemon=True)
    thread.start()
    try:
        assert entered.wait(10), "first executor never reached the external boundary"
        with pytest.raises(EffectExecutionError,match="already RUNNING"):
            second.execute_effect(rec.spec.effect_id,lambda spec,key: calls.append("second") or {})
        assert calls == ["first"]
    finally:
        release.set(); thread.join(10)
        first_store.close(); second_store.close()

    assert not thread.is_alive()
    assert "error" not in error_box
    assert result_box["record"].status == EffectStatus.SUCCEEDED.value


def test_passive_resume_does_not_reclassify_live_effect_as_crashed(tmp_path:Path):
    db=tmp_path/"passive-resume.db"
    store=SQLiteStore(db)
    e=AASMEngine(ProblemSpec("live effect"),store=store)
    rec=e.propose_effect(EffectSpec("external-write",idempotency_key="live-op"))
    e.authorize_effect(rec.spec.effect_id)
    running=store.load_effect(e.snapshot.machine_id,rec.spec.effect_id)
    running.status=EffectStatus.RUNNING.value
    store.save_effect(running)
    mid=e.snapshot.machine_id

    passive=AASMEngine.resume(mid,store)
    assert passive.list_effects()[0].status == EffectStatus.RUNNING.value

    recovered=AASMEngine.resume(mid,store,recover_effects=True)
    assert recovered.list_effects()[0].status == EffectStatus.UNKNOWN.value
    store.close()


def test_running_effect_becomes_unknown_after_unclean_exit(tmp_path:Path):
    db=tmp_path/"effects.db"
    marker=tmp_path/"mid.txt"
    external=tmp_path/"external.txt"
    root=Path(__file__).resolve().parents[1]
    code=f'''
import os
from aasm import AASMEngine, EffectSpec, ProblemSpec, SQLiteStore
store=SQLiteStore(r"{db}")
e=AASMEngine(ProblemSpec("effect crash"),store=store)
r=e.propose_effect(EffectSpec("external-write",{{"path":r"{external}"}},idempotency_key="external-op"))
e.authorize_effect(r.spec.effect_id)
open(r"{marker}","w").write(e.snapshot.machine_id+"\\n"+r.spec.effect_id)
def executor(spec,key):
    open(r"{external}","a").write("performed\\n")
    os._exit(73)
e.execute_effect(r.spec.effect_id,executor)
'''
    env=dict(os.environ); env["PYTHONPATH"]=str(root/"src")
    proc=subprocess.run([sys.executable,"-c",code],cwd=root,env=env)
    assert proc.returncode == 73
    machine_id,effect_id=marker.read_text().splitlines()
    assert external.read_text().splitlines() == ["performed"]

    store=SQLiteStore(db)
    recovered=AASMEngine.resume(machine_id,store,recover_effects=True)
    effect=store.load_effect(machine_id,effect_id)
    assert effect.status == EffectStatus.UNKNOWN.value
    with pytest.raises(EffectUnknownOutcome):
        recovered.execute_effect(effect_id,lambda spec,key: {"should_not": "run"})
    assert external.read_text().splitlines() == ["performed"]
    reconciled=recovered.reconcile_effect(effect_id,succeeded=True,result={"observed": True},evidence=["external file exists"])
    assert reconciled.status == EffectStatus.SUCCEEDED.value
    assert recovered.execute_effect(effect_id,lambda spec,key: {"duplicate": True}).result == {"observed": True}
    store.close()


def test_effects_persist_across_restart(tmp_path:Path):
    store=SQLiteStore(tmp_path/"aasm.db")
    e=AASMEngine(ProblemSpec("persist effects"),store=store)
    r=e.propose_effect(EffectSpec("tool",idempotency_key="tool-1"))
    e.authorize_effect(r.spec.effect_id,"quorum")
    e.execute_effect(r.spec.effect_id,lambda spec,key:{"value":7})
    mid=e.snapshot.machine_id
    store.close()
    store=SQLiteStore(tmp_path/"aasm.db")
    recovered=AASMEngine.resume(mid,store)
    records=recovered.list_effects()
    assert len(records)==1
    assert records[0].status == EffectStatus.SUCCEEDED.value
    assert records[0].authority == "quorum"
    assert records[0].result == {"value":7}
    store.close()
