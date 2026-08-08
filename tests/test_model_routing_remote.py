import threading
from http.server import ThreadingHTTPServer
import pytest

from aasm import AASMEngine, ProblemSpec, SQLiteStore, ResourceRecord, WorkerRecord, TaskDemand
from aasm.model_routing import ModelProfile, ModelRouteRequest, ModelStrengthRouter
from aasm.remote import AASMRemoteClient
from aasm.server import make_handler


def test_model_strength_routing_cost_and_quality():
    router=ModelStrengthRouter()
    profiles=[
        ModelProfile('luna','provider',['code','scan'],strength=.45,cost_per_1k_output=.2,latency_score=.95,context_window=100_000),
        ModelProfile('terra','provider',['code','scan','test'],strength=.72,cost_per_1k_output=1.0,latency_score=.75,context_window=200_000),
        ModelProfile('sol','provider',['code','scan','test','review'],strength=.96,cost_per_1k_output=4.0,latency_score=.45,context_window=300_000),
    ]
    assert router.route(profiles,ModelRouteRequest('scan',['scan'],min_strength=.4,optimize='cost')).selected_model_id=='luna'
    assert router.route(profiles,ModelRouteRequest('review',['review'],min_strength=.9,optimize='strength')).selected_model_id=='sol'
    assert router.route(profiles,ModelRouteRequest('test',['test'],min_strength=.7,max_cost_per_1k_output=2,optimize='balanced')).selected_model_id=='terra'


def test_model_routes_are_durable_and_fork_aware(tmp_path):
    store=SQLiteStore(tmp_path/'m.db'); e=AASMEngine(ProblemSpec('route models'),store=store)
    e.register_model_profile(ModelProfile('cheap','p',['scan'],strength=.5,cost_per_1k_output=.1)); seq=e.events[-1].sequence
    e.register_model_profile(ModelProfile('strong','p',['review'],strength=.95,cost_per_1k_output=5))
    assert e.route_model(ModelRouteRequest('r',['review'],min_strength=.9,optimize='strength')).selected_model_id=='strong'
    mid=e.snapshot.machine_id; assert len(AASMEngine.resume(mid,store).list_model_profiles())==2
    fork=e.fork(seq); assert [m['model_id'] for m in fork.list_model_profiles()]==['cheap']; store.close()


def test_remote_worker_can_claim_and_complete_over_http(tmp_path):
    db=str(tmp_path/'remote.db'); store=SQLiteStore(db); e=AASMEngine(ProblemSpec('remote work'),store=store)
    e.register_resource(ResourceRecord('cpu','worker',['code'],capacity=2)); mid=e.snapshot.machine_id; store.close()
    server=ThreadingHTTPServer(('127.0.0.1',0),make_handler(db,'secret')); t=threading.Thread(target=server.serve_forever,daemon=True); t.start()
    try:
        client=AASMRemoteClient(f'http://127.0.0.1:{server.server_port}','secret'); assert client.health()['ok'] is True
        client.register_worker(mid,WorkerRecord('w1','cpu')); lease=client.claim(mid,'w1',TaskDemand('task-1',['code'],demand=1),lease_seconds=30); assert lease['status']=='ACTIVE'
        done=client.complete(mid,lease['lease_id'],{'ok':True}); assert done['status']=='COMPLETED'; assert client.state(mid)['leases'][-1]['status']=='COMPLETED'
    finally:
        server.shutdown(); server.server_close()


def test_postgres_store_has_clear_optional_dependency_error():
    try: import psycopg  # noqa
    except ImportError:
        from aasm.persistence.postgres import PostgresStore
        with pytest.raises(RuntimeError): PostgresStore('postgresql://invalid')
