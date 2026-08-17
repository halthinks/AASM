from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
import pytest
from aasm.semantic_projection import EQUIVALENCE_RELATIONS, INVARIANT_CLASSIFICATIONS, PROJECTION_FIDELITIES, PROJECTION_STATUSES, REVISION_POLICIES, InvariantRef, SemanticEquivalenceAssessment, SemanticProjectionDefinition, SemanticProjectionResult, SemanticSubjectRef, assess_semantic_equivalence, invariant_contract, semantic_projection_contract
ROOT = Path(__file__).resolve().parents[1]

def h(char: str) -> str:
    return char * 64

def subject(object_id: str, fingerprint: str, *, semantic_type_id: str='textpcb.board.alternative.v1', revision_id: str='problem-revision-7', revision_fingerprint: str='7' * 64) -> SemanticSubjectRef:
    return SemanticSubjectRef(semantic_type_id, object_id, fingerprint, revision_id, revision_fingerprint)

def lossless_projection(*, revision_policy: str='EXACT_MATCH_REQUIRED') -> SemanticProjectionDefinition:
    return SemanticProjectionDefinition(projection_name='textpcb-logical-board', source_type_ids=('textpcb.board.alternative.v1',), target_type_id='textpcb.logical-board.v1', purpose='alternative semantic comparison', fidelity='LOSSLESS', invariants=(InvariantRef('board.connectivity', 'REPRESENTATIONAL'), InvariantRef('board.constraint-shape', 'STATIC_PROTOCOL')), revision_policy=revision_policy)

def lossy_projection(*, revision_policy: str='EXACT_MATCH_REQUIRED') -> SemanticProjectionDefinition:
    return SemanticProjectionDefinition(projection_name='textpcb-functional-board', source_type_ids=('textpcb.board.alternative.v1',), target_type_id='textpcb.functional-board.v1', purpose='functional alternative clustering', fidelity='LOSSY', invariants=(InvariantRef('board.connectivity', 'REPRESENTATIONAL'), InvariantRef('board.clearance-rule', 'STATIC_PROTOCOL'), InvariantRef('board.route-geometry', 'REPRESENTATIONAL', 'DISCARDED'), InvariantRef('board.bench-emission', 'EMPIRICAL', 'UNSUPPORTED')), discarded_semantics=('exact route geometry', 'tool-specific entity ordering'), unsupported_semantics=('bench-measured emissions',), revision_policy=revision_policy)

def result(definition: SemanticProjectionDefinition, item: SemanticSubjectRef, projected_fingerprint: str, *, status: str='PROJECTED', diagnostics: tuple[str, ...]=()) -> SemanticProjectionResult:
    return SemanticProjectionResult(definition.projection_id, definition.fingerprint, item, status, projected_fingerprint if status == 'PROJECTED' else '', evidence_ids=('evidence-projection-1',), diagnostics=diagnostics)

def test_unbound_subjects_are_explicitly_marked_unbound_not_silently_revision_equal():
    definition = lossless_projection()
    left = subject('alt-a', h('a'), revision_id='', revision_fingerprint='')
    right = subject('alt-b', h('b'), revision_id='', revision_fingerprint='')
    assessment = assess_semantic_equivalence(definition, result(definition, left, h('f')), result(definition, right, h('f')))
    assert assessment.revision_relation == 'UNBOUND'
    assert assessment.relation == 'PROJECTION_EQUIVALENT'

def test_subject_type_projection_id_and_projection_fingerprint_attacks_fail_closed():
    definition = lossless_projection()
    wrong_type = subject('alt-a', h('a'), semantic_type_id='other.semantic.type')
    with pytest.raises(ValueError, match='subject type'):
        assess_semantic_equivalence(definition, result(definition, wrong_type, h('1')), result(definition, subject('alt-b', h('b')), h('1')))
    left = result(definition, subject('alt-a', h('a')), h('1'))
    right = result(definition, subject('alt-b', h('b')), h('1'))
    forged_id = SemanticProjectionResult('semantic-projection-' + '0' * 24, definition.fingerprint, left.subject, 'PROJECTED', h('1'))
    with pytest.raises(ValueError, match='projection_id'):
        assess_semantic_equivalence(definition, forged_id, right)
    forged_fingerprint = SemanticProjectionResult(definition.projection_id, h('0'), left.subject, 'PROJECTED', h('1'))
    with pytest.raises(ValueError, match='projection fingerprint'):
        assess_semantic_equivalence(definition, forged_fingerprint, right)

def test_definition_result_and_assessment_fingerprint_tampering_fail_closed():
    definition = lossless_projection()
    definition_payload = definition.to_dict()
    definition_payload['fingerprint'] = h('0')
    with pytest.raises(ValueError, match='definition fingerprint mismatch'):
        SemanticProjectionDefinition.from_dict(definition_payload)
    left = result(definition, subject('alt-a', h('a')), h('1'))
    result_payload = left.to_dict()
    result_payload['fingerprint'] = h('0')
    with pytest.raises(ValueError, match='result fingerprint mismatch'):
        SemanticProjectionResult.from_dict(result_payload)
    right = result(definition, subject('alt-b', h('b')), h('1'))
    assessment = assess_semantic_equivalence(definition, left, right)
    assessment_payload = assessment.to_dict()
    assessment_payload['fingerprint'] = h('0')
    with pytest.raises(ValueError, match='assessment fingerprint mismatch'):
        SemanticEquivalenceAssessment.from_dict(assessment_payload)

def test_equivalence_assessment_is_symmetric_and_order_independent():
    definition = lossy_projection()
    left = result(definition, subject('alt-z', h('a')), h('f'))
    right = result(definition, subject('alt-a', h('b')), h('f'))
    forward = assess_semantic_equivalence(definition, left, right)
    reverse = assess_semantic_equivalence(definition, right, left)
    assert forward == reverse
    assert forward.assessment_id == reverse.assessment_id
    assert forward.fingerprint == reverse.fingerprint

def test_schema_is_closed_and_carries_exact_projection_equivalence_and_invariant_vocabularies():
    schema = json.loads((ROOT / 'schemas/semantic-projection.schema.json').read_text(encoding='utf-8'))
    for name in ('invariantRef', 'subjectRef', 'projectionDefinition', 'projectionResult', 'equivalenceAssessment'):
        assert schema['$defs'][name]['additionalProperties'] is False
    invariant_enum = schema['$defs']['invariantRef']['properties']['classification']['enum']
    assert invariant_enum == list(INVARIANT_CLASSIFICATIONS)
    relation_enum = schema['$defs']['equivalenceAssessment']['properties']['relation']['enum']
    assert relation_enum == list(EQUIVALENCE_RELATIONS)
    assert schema['$defs']['projectionDefinition']['properties']['contract_id']['const'] == 'aasm.semantic.projection.v1'
    assert schema['$defs']['equivalenceAssessment']['properties']['contract_id']['const'] == 'aasm.semantic.equivalence.v1'

def test_foundation_claim_ceiling_blocks_truth_authority_acceptance_proof_preference_and_reuse():
    contract = semantic_projection_contract()
    assert contract['runtime_admission'] == 'PRE_ADMISSION_ONLY'
    assert contract['public_admission'] == 'PRE_ADMISSION_ONLY'
    assert contract['truth_authority'] == 'NONE'
    assert contract['fact_authority'] == 'NONE'
    assert contract['effect_authority'] == 'NONE'
    assert contract['artifact_acceptance'] == 'NONE'
    assert contract['entity_identity_authority'] == 'NONE'
    assert contract['proof_authority'] == 'NONE'
    assert contract['objective_preference'] == 'NONE'
    assert contract['reuse_admission'] == 'NONE'
    assert contract['parallel_projection_registry'] == 'NONE'
    assert contract['current_projection_pointer'] == 'NONE'
    assert contract['existing_reuse_certified_equivalent'] == 'NOT_REINTERPRETED_OR_ADMITTED_BY_FOUNDATION'

def test_existing_projection_substrates_remain_uncomposed_pre_admission():
    paths = {'quantity': 'src/aasm/quantity.py', 'artifact': 'src/aasm/artifact_lineage.py', 'solver_outcome': 'src/aasm/solver_outcome_v2.py', 'trace': 'src/aasm/trace_conformance.py', 'solution_pools': 'src/aasm/solution_pools.py', 'reuse_validation': 'src/aasm/reuse_validation.py', 'decision_vector': 'src/aasm/decision_vector_ir.py', 'runtime': 'src/aasm/runtime_v56_foundation.py', 'public': 'src/aasm/public_active.py'}
    sources = {name: (ROOT / path).read_text(encoding='utf-8') for name, path in paths.items()}
    for name, source_text in sources.items():
        assert 'from .semantic_projection' not in source_text, name
        assert 'aasm.semantic.projection.v1' not in source_text, name
        assert 'aasm.semantic.equivalence.v1' not in source_text, name
    assert 'canonical_projection_fingerprint' in sources['quantity']
    assert 'semantic_projection_sha256' in sources['artifact']
    assert 'class LegacyStatusProjection' in sources['solver_outcome']
    assert '"lossy": bool(self.lossy)' in sources['solver_outcome']
    assert '"unknown_transition_policy": "UNSUPPORTED_EXPLICIT"' in sources['trace']
    assert '"deduplication": "EXACT_CANONICAL_ASSIGNMENT_FINGERPRINT"' in sources['solution_pools']
    assert '"CERTIFIED_EQUIVALENT"' in sources['reuse_validation']
    assert 'class GovernedDecisionVector' in sources['decision_vector']
