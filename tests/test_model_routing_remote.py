import threading
from http.server import ThreadingHTTPServer
from urllib.request import urlopen
import pytest

from aasm import AASMEngine, ProblemSpec, SQLiteStore, ResourceRecord, WorkerRecord, TaskDemand
from aasm.control_center import html_document
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
    server=ThreadingHTTPServer(('127.0.0.1',0),make_handler(db,'secret')); threading.Thread(target=server.serve_forever,daemon=True).start()
    try:
        client=AASMRemoteClient(f'http://127.0.0.1:{server.server_port}','secret'); assert client.health()['ok'] is True
        client.register_worker(mid,WorkerRecord('w1','cpu')); lease=client.claim(mid,'w1',TaskDemand('task-1',['code'],demand=1),lease_seconds=30); assert lease['status']=='ACTIVE'
        done=client.complete(mid,lease['lease_id'],{'ok':True}); assert done['status']=='COMPLETED'; assert client.state(mid)['leases'][-1]['status']=='COMPLETED'
    finally:
        server.shutdown(); server.server_close()


def test_control_center_has_security_headers_and_escaped_dynamic_labels(tmp_path):
    db=str(tmp_path/'ui.db')
    server=ThreadingHTTPServer(('127.0.0.1',0),make_handler(db,'secret')); threading.Thread(target=server.serve_forever,daemon=True).start()
    try:
        with urlopen(f'http://127.0.0.1:{server.server_port}/ui') as response:
            assert response.headers['Cache-Control']=='no-store'
            assert response.headers['X-Content-Type-Options']=='nosniff'
            assert "frame-ancestors 'none'" in response.headers['Content-Security-Policy']
        page=html_document()
        assert 'function esc(value)' in page
        assert '${esc(m.model_id)}' in page
        assert '${esc(w.worker_id)}' in page
        assert '${esc(l.task_id)}' in page
    finally:
        server.shutdown(); server.server_close()


def test_remote_server_refuses_public_bind_without_authentication(tmp_path,monkeypatch):
    from aasm.server import serve
    monkeypatch.delenv('AASM_SERVER_TOKEN',raising=False)
    with pytest.raises(ValueError,match='refuses non-loopback binding'):
        serve(str(tmp_path/'public.db'),host='0.0.0.0',port=0,token=None)


def test_postgres_store_has_clear_optional_dependency_error():
    try: import psycopg  # noqa
    except ImportError:
        from aasm.persistence.postgres import PostgresStore
        with pytest.raises(RuntimeError): PostgresStore('postgresql://invalid')


def test_claim_next_uses_scheduled_priority(tmp_path):
    store=SQLiteStore(tmp_path/'next.db'); e=AASMEngine(ProblemSpec('next'),store=store)
    e.register_resource(ResourceRecord('cpu','worker',['code'],capacity=1)); e.register_worker(WorkerRecord('w','cpu'))
    e.schedule([TaskDemand('low',['code'],priority=1),TaskDemand('high',['code'],priority=10)])
    lease=e.claim_next_task('w',lease_seconds=20)
    assert lease['task_id']=='high'; store.close()


def test_remote_worker_loop_pulls_scheduled_task(tmp_path):
    from aasm import RemoteWorkerLoop
    db=str(tmp_path/'loop.db'); store=SQLiteStore(db); e=AASMEngine(ProblemSpec('loop'),store=store)
    e.register_resource(ResourceRecord('cpu','worker',['code'],capacity=1)); e.schedule([TaskDemand('job',['code'],priority=5,metadata={'prompt':'do it'})]); mid=e.snapshot.machine_id; store.close()
    server=ThreadingHTTPServer(('127.0.0.1',0),make_handler(db,'secret')); threading.Thread(target=server.serve_forever,daemon=True).start()
    try:
        client=AASMRemoteClient(f'http://127.0.0.1:{server.server_port}','secret')
        loop=RemoteWorkerLoop(client,mid,WorkerRecord('loop-worker','cpu'),lambda lease:{'seen':lease['metadata']['prompt']},lease_seconds=30,heartbeat_interval=5)
        assert loop.run_once() is True
        assert client.state(mid)['leases'][-1]['status']=='COMPLETED'
    finally:
        server.shutdown(); server.server_close()
