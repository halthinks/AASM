from aasm import (
    AASMEngine,
    AdaptiveModelRouter,
    ModelOutcomeLedger,
    ModelOutcomeRecord,
    ModelProfile,
    ModelRouteRequest,
    ProblemSpec,
    SQLiteStore,
)


def profiles():
    return [
        ModelProfile("luna","openai",["code"],strength=.6,cost_per_1k_output=.2,latency_score=.9),
        ModelProfile("terra","openai",["code"],strength=.8,cost_per_1k_output=1.0,latency_score=.7),
        ModelProfile("sol","openai",["code"],strength=.95,cost_per_1k_output=4.0,latency_score=.5),
    ]


def test_wilson_confidence_is_exposed_and_grows_with_samples():
    ledger=ModelOutcomeLedger()
    for i in range(10): ledger.add(ModelOutcomeRecord(str(i),"backend","terra",True))
    perf=ledger.performance("backend")[0]
    assert perf.samples==10 and perf.acceptance_rate==1.0
    assert 0 < perf.acceptance_lower_bound < 1
    assert perf.confidence > .5


def test_adaptive_router_falls_back_when_evidence_is_insufficient():
    ledger=ModelOutcomeLedger([{"task_id":"1","task_class":"backend","model_id":"luna","accepted":True}])
    router=AdaptiveModelRouter(ledger)
    request=ModelRouteRequest("t",["code"],min_strength=.5,optimize="cost",metadata={"task_class":"backend","min_empirical_samples":3})
    result=router.route(profiles(),request)
    assert result.adaptive is False
    assert result.selected_model_id=="luna"


def test_adaptive_cost_per_quality_prefers_measured_cheaper_success():
    ledger=ModelOutcomeLedger()
    for i in range(8):
        ledger.add(ModelOutcomeRecord(f"l{i}","backend","luna",True,estimated_cost=.2,latency_seconds=3))
        ledger.add(ModelOutcomeRecord(f"t{i}","backend","terra",i<7,estimated_cost=1.0,latency_seconds=2,repair_required=i==7))
    request=ModelRouteRequest("job",["code"],min_strength=.5,metadata={"task_class":"backend","min_empirical_samples":3,"empirical_optimize":"cost_per_quality"})
    result=AdaptiveModelRouter(ledger).route(profiles(),request)
    assert result.adaptive is True
    assert result.selected_model_id=="luna"
    assert result.static_selected_model_id is not None
    assert result.performance["luna"]["samples"]==8


def test_empirical_floor_never_overrides_static_strength_floor():
    ledger=ModelOutcomeLedger()
    for i in range(20): ledger.add(ModelOutcomeRecord(f"l{i}","architecture","luna",True,estimated_cost=.1))
    request=ModelRouteRequest("arch",["code"],min_strength=.9,metadata={"task_class":"architecture","min_empirical_samples":3})
    result=AdaptiveModelRouter(ledger).route(profiles(),request)
    assert result.selected_model_id=="sol"
    assert "luna" in result.rejected and "strength_below_floor" in result.rejected["luna"]


def test_deterministic_calibration_routes_under_sampled_eligible_model():
    ledger=ModelOutcomeLedger()
    for i in range(3): ledger.add(ModelOutcomeRecord(f"l{i}","tests","luna",True))
    request=ModelRouteRequest("cal",["code"],min_strength=.5,metadata={"task_class":"tests","min_empirical_samples":2,"explore_under_sampled":True})
    result=AdaptiveModelRouter(ledger).route(profiles(),request)
    assert result.adaptive is True
    assert result.reason.startswith("deterministic calibration")
    assert result.selected_model_id=="terra"


def test_outcomes_persist_and_change_engine_route_after_restart(tmp_path):
    store=SQLiteStore(tmp_path/"adaptive.db"); engine=AASMEngine(ProblemSpec("adaptive"),store=store)
    for p in profiles(): engine.register_model_profile(p)
    for i in range(6):
        engine.record_model_outcome(ModelOutcomeRecord(f"l{i}","backend","luna",True,estimated_cost=.2))
        engine.record_model_outcome(ModelOutcomeRecord(f"t{i}","backend","terra",i<4,estimated_cost=1.0,repair_required=i>=4))
    mid=engine.snapshot.machine_id; store.close()
    store=SQLiteStore(tmp_path/"adaptive.db"); resumed=AASMEngine.resume(mid,store)
    result=resumed.route_model(ModelRouteRequest("next",["code"],min_strength=.5,metadata={"task_class":"backend","min_empirical_samples":3}))
    assert result.adaptive is True and result.selected_model_id=="luna"
    assert len(resumed.model_performance("backend"))==2
    store.close()


def test_remote_outcome_feedback_reaches_dashboard(tmp_path):
    import threading
    from http.server import ThreadingHTTPServer
    from aasm import AASMRemoteClient
    from aasm.server import make_handler

    db=str(tmp_path/"remote-adaptive.db"); store=SQLiteStore(db); engine=AASMEngine(ProblemSpec("remote adaptive"),store=store); engine.register_model_profile(profiles()[0]); mid=engine.snapshot.machine_id; store.close()
    server=ThreadingHTTPServer(("127.0.0.1",0),make_handler(db,"secret")); threading.Thread(target=server.serve_forever,daemon=True).start()
    try:
        client=AASMRemoteClient(f"http://127.0.0.1:{server.server_port}","secret")
        client.model_outcome(mid,ModelOutcomeRecord("t","scan","luna",True,estimated_cost=.1))
        state=client.state(mid)
        assert state["model_performance"][0]["model_id"]=="luna"
    finally:
        server.shutdown(); server.server_close()
