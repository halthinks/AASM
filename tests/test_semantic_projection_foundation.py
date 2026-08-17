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

def test_projection_contract_relations_and_invariant_classifications_are_exact():
    assert EQUIVALENCE_RELATIONS == ('EXACT_IDENTITY', 'PROJECTION_EQUIVALENT', 'NON_EQUIVALENT', 'INDETERMINATE', 'UNSUPPORTED')
    assert INVARIANT_CLASSIFICATIONS == ('REPRESENTATIONAL', 'STATIC_PROTOCOL', 'DYNAMIC_KERNEL', 'EMPIRICAL')
    assert PROJECTION_FIDELITIES == ('LOSSLESS', 'LOSSY')
    assert PROJECTION_STATUSES == ('PROJECTED', 'UNSUPPORTED', 'INDETERMINATE')
    assert REVISION_POLICIES == ('EXACT_MATCH_REQUIRED', 'EXPLICIT_CROSS_REVISION')

def test_invariant_contract_prevents_static_or_representational_equivalence_from_becoming_proof():
    contract = invariant_contract()
    assert contract['contract_id'] == 'aasm.invariant.v1'
    assert contract['projection_preservation_is_proof'] is False
    assert contract['representational_equivalence_proves_dynamic_kernel'] is False
    assert contract['representational_equivalence_proves_empirical'] is False
    assert contract['truth_authority'] == 'NONE'
    empirical = InvariantRef('board.bench-emission', 'EMPIRICAL', 'PRESERVED')
    assert empirical.classification == 'EMPIRICAL'
    assert empirical.treatment == 'PRESERVED'

def test_projection_definition_identity_is_deterministic_and_round_trips():
    first = lossless_projection()
    second = SemanticProjectionDefinition(projection_name='textpcb-logical-board', source_type_ids=('textpcb.board.alternative.v1',), target_type_id='textpcb.logical-board.v1', purpose='alternative semantic comparison', fidelity='LOSSLESS', invariants=(InvariantRef('board.constraint-shape', 'STATIC_PROTOCOL'), InvariantRef('board.connectivity', 'REPRESENTATIONAL')))
    assert first.projection_id == second.projection_id
    assert first.fingerprint == second.fingerprint
    assert SemanticProjectionDefinition.from_dict(first.to_dict()) == first

def test_lossless_projection_rejects_any_declared_discard():
    with pytest.raises(ValueError, match='LOSSLESS'):
        SemanticProjectionDefinition(projection_name='invalid-lossless', source_type_ids=('x',), target_type_id='y', purpose='test', fidelity='LOSSLESS', invariants=(InvariantRef('shape', 'REPRESENTATIONAL', 'DISCARDED'),))
    with pytest.raises(ValueError, match='LOSSLESS'):
        SemanticProjectionDefinition(projection_name='invalid-lossless-2', source_type_ids=('x',), target_type_id='y', purpose='test', fidelity='LOSSLESS', invariants=(InvariantRef('shape', 'REPRESENTATIONAL'),), discarded_semantics=('bytes',))

def test_lossy_projection_requires_explicit_loss_not_a_bare_same_enough_flag():
    with pytest.raises(ValueError, match='must explicitly declare'):
        SemanticProjectionDefinition(projection_name='invalid-lossy', source_type_ids=('x',), target_type_id='y', purpose='test', fidelity='LOSSY', invariants=(InvariantRef('shape', 'REPRESENTATIONAL'),))

def test_portable_identity_rejects_binary_float_metadata():
    with pytest.raises(TypeError, match='binary floating-point'):
        SemanticProjectionDefinition(projection_name='float-metadata', source_type_ids=('x',), target_type_id='y', purpose='test', fidelity='LOSSLESS', invariants=(InvariantRef('shape', 'REPRESENTATIONAL'),), metadata={'epsilon': 0.1})

def test_exact_identity_requires_same_type_object_fingerprint_and_revision_binding():
    definition = lossless_projection()
    item = subject('alt-a', h('a'))
    left = result(definition, item, h('1'))
    right = result(definition, SemanticSubjectRef.from_dict(item.to_dict()), h('1'))
    assessment = assess_semantic_equivalence(definition, left, right)
    assert assessment.relation == 'EXACT_IDENTITY'
    assert assessment.revision_relation == 'SAME'

def test_same_projected_fingerprint_is_projection_equivalence_not_exact_identity():
    definition = lossless_projection()
    left = result(definition, subject('alt-a', h('a')), h('1'))
    right = result(definition, subject('alt-b', h('b')), h('1'))
    assessment = assess_semantic_equivalence(definition, left, right)
    assert assessment.relation == 'PROJECTION_EQUIVALENT'
    assert assessment.relation != 'EXACT_IDENTITY'
    assert assessment.projection_fidelity == 'LOSSLESS'
