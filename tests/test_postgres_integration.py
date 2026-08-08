import os
import pytest

DSN=os.getenv("AASM_TEST_POSTGRES_DSN")
pytestmark=pytest.mark.skipif(not DSN,reason="AASM_TEST_POSTGRES_DSN not configured")


def test_postgres_multi_connection_claim_exclusion():
    from aasm import AASMEngine, ProblemSpec, ResourceRecord, WorkerRecord, TaskDemand
    from aasm.persistence.postgres import PostgresStore
    a=PostgresStore(DSN); e=AASMEngine(ProblemSpec('pg'),store=a); e.register_resource(ResourceRecord('cpu','worker',['code'],capacity=2)); e.register_worker(WorkerRecord('w1','cpu')); mid=e.snapshot.machine_id
    b=PostgresStore(DSN); other=AASMEngine.resume(mid,b); other.register_worker(WorkerRecord('w2','cpu'))
    e.claim_task(TaskDemand('same',['code']),'w1',lease_seconds=60)
    with pytest.raises(ValueError,match='already claimed'):
        other.claim_task(TaskDemand('same',['code']),'w2',lease_seconds=60)
    a.close(); b.close()
