import pytest
from aasm import AASMEngine, ContextProjectionRequest, MemoryIndexEntry, ProblemSpec, __version__, hierarchical_memory_contract, run_hierarchical_memory_conformance, validate_public_api_contract

def commit(engine,privacy='PUBLIC',principal=None,retention='permanent'):
    meta={} if principal is None else {'privacy_principal_id':principal}
    p=engine.propose_memory_operation('STORE',scope_id='root',proposer_id='agent',content={'text':'alpha'},privacy_level=privacy,retention_policy=retention,metadata=meta)
    d=p['decision']['decision_id']; engine.authorize_memory_operation(d,authority_id='policy',authority_class='POLICY'); r=engine.commit_memory_operation(d,worker_id='worker'); return p['memory']['memory_id'],r

def test_v40_contract_and_public_api():
    assert __version__=='0.43.0'; assert hierarchical_memory_contract()['contract_id']=='aasm.memory.hierarchical.v1'; report=validate_public_api_contract(); assert report['valid'],report; assert report['contract']['contract_version']=='0.19.0'
def test_governed_memory_path_and_legacy_cache():
    e=AASMEngine(ProblemSpec('memory')); p=e.propose_memory_operation('STORE',scope_id='root',proposer_id='agent',content={'x':1},privacy_level='PUBLIC'); d=p['decision']['decision_id']
    with pytest.raises(ValueError): e.commit_memory_operation(d,worker_id='w')
    e.authorize_memory_operation(d,authority_id='policy',authority_class='POLICY'); out=e.commit_memory_operation(d,worker_id='w'); assert out['memory']['status']=='ACTIVE'; e.memo_put('k',1); assert e.memo_get('k')==1
def test_principal_privacy():
    e=AASMEngine(ProblemSpec('privacy'))
    with pytest.raises(ValueError): e.propose_memory_operation('STORE',scope_id='root',proposer_id='a',content='x',privacy_level='USER')
    mid,_=commit(e,privacy='USER',principal='u1'); assert mid not in {x['memory_id'] for x in e.context_projection(ContextProjectionRequest(metadata={'principal_id':'u2'}))['memory_items']}; assert mid in {x['memory_id'] for x in e.context_projection(ContextProjectionRequest(metadata={'principal_id':'u1'}))['memory_items']}
def test_tombstone_and_index_identity():
    e=AASMEngine(ProblemSpec('forget')); mid,_=commit(e); m=e.hierarchical_memory_report()['memories'][mid]['memory']; e.admit_memory_index(MemoryIndexEntry(mid,m['fingerprint'],'VECTOR','embed','1',score=.9),authority_id='policy',authority_class='POLICY'); assert e.hierarchical_memory_report()['memories'][mid]['memory']['fingerprint']==m['fingerprint']; f=e.propose_memory_forget(mid,proposer_id='u',reason='revoke'); d=f['decision']['decision_id']; e.authorize_memory_operation(d,authority_id='policy',authority_class='POLICY'); e.commit_memory_operation(d,worker_id='w'); assert e.hierarchical_memory_report()['memories'][mid]['status']=='REVOKED'
def test_ttl_and_context_budget():
    e=AASMEngine(ProblemSpec('ttl')); mid,r=commit(e,retention='ttl:10'); row=next(x for x in e.snapshot.evidence['records'] if x['evidence_id']==r['evidence_id']); t=float(row['created_at']); assert e.hierarchical_memory_report(as_of=t+11)['memories'][mid]['status']=='EXPIRED'; ctx=e.context_projection(ContextProjectionRequest(query='alpha',allowed_privacy_levels=('PUBLIC',),max_chars=100)); assert ctx['used_chars']<=100
def test_conformance():
    r=run_hierarchical_memory_conformance(); assert r['status']=='PASS',r; assert all(r['checks'].values())
