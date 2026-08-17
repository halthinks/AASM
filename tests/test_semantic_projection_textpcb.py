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

def test_lossy_textpcb_alternatives_remain_only_projection_equivalent():
    definition = lossy_projection()
    left = result(definition, subject('placement-route-a', h('a')), h('c'))
    right = result(definition, subject('placement-route-b', h('b')), h('c'))
    assessment = assess_semantic_equivalence(definition, left, right)
    assert assessment.relation == 'PROJECTION_EQUIVALENT'
    assert assessment.projection_fidelity == 'LOSSY'
    assert any(('lossy' in item for item in assessment.diagnostics))
    assert 'exact route geometry' in definition.discarded_semantics

def test_textpcb_cross_format_artifacts_can_be_projection_equivalent_without_becoming_same_artifact():
    definition = SemanticProjectionDefinition(projection_name='textpcb-artifact-topology', source_type_ids=('textpcb.artifact.brep', 'textpcb.artifact.step'), target_type_id='textpcb.board-topology.v1', purpose='cross-format artifact comparison', fidelity='LOSSY', invariants=(InvariantRef('artifact.topology', 'REPRESENTATIONAL'), InvariantRef('artifact.entity-order', 'REPRESENTATIONAL', 'DISCARDED')), discarded_semantics=('serialization bytes', 'tool-specific entity ordering'), revision_policy='EXPLICIT_CROSS_REVISION')
    step = subject('artifact-revision-step-1', h('a'), semantic_type_id='textpcb.artifact.step', revision_id='artifact-revision-1', revision_fingerprint=h('1'))
    brep = subject('artifact-revision-brep-2', h('b'), semantic_type_id='textpcb.artifact.brep', revision_id='artifact-revision-2', revision_fingerprint=h('2'))
    assessment = assess_semantic_equivalence(definition, result(definition, step, h('f')), result(definition, brep, h('f')))
    assert assessment.relation == 'PROJECTION_EQUIVALENT'
    assert assessment.revision_relation == 'DIFFERENT'
    assert assessment.left_subject.object_id != assessment.right_subject.object_id

def test_projected_fingerprint_difference_is_non_equivalence_only_under_that_projection():
    definition = lossless_projection()
    assessment = assess_semantic_equivalence(definition, result(definition, subject('alt-a', h('a')), h('1')), result(definition, subject('alt-b', h('b')), h('2')))
    assert assessment.relation == 'NON_EQUIVALENT'
    assert assessment.projection_id == definition.projection_id

def test_unsupported_and_indeterminate_projection_results_remain_distinct():
    definition = lossless_projection()
    left_subject = subject('alt-a', h('a'))
    right_subject = subject('alt-b', h('b'))
    unsupported = result(definition, left_subject, h('1'), status='UNSUPPORTED', diagnostics=('projection cannot represent transient thermal field',))
    projected = result(definition, right_subject, h('1'))
    assert assess_semantic_equivalence(definition, unsupported, projected).relation == 'UNSUPPORTED'
    indeterminate = result(definition, left_subject, h('1'), status='INDETERMINATE', diagnostics=('required source fingerprint unavailable',))
    assert assess_semantic_equivalence(definition, indeterminate, projected).relation == 'INDETERMINATE'

def test_non_projected_result_requires_diagnostic_and_cannot_smuggle_projected_fingerprint():
    definition = lossless_projection()
    item = subject('alt-a', h('a'))
    with pytest.raises(ValueError, match='requires diagnostics'):
        result(definition, item, h('1'), status='UNSUPPORTED')
    with pytest.raises(ValueError, match='cannot carry'):
        SemanticProjectionResult(definition.projection_id, definition.fingerprint, item, 'UNSUPPORTED', h('1'), diagnostics=('unsupported',))

def test_exact_revision_policy_fails_closed_across_revision_mismatch():
    definition = lossless_projection(revision_policy='EXACT_MATCH_REQUIRED')
    left = subject('alt-a', h('a'), revision_id='rev-1', revision_fingerprint=h('1'))
    right = subject('alt-b', h('b'), revision_id='rev-2', revision_fingerprint=h('2'))
    assessment = assess_semantic_equivalence(definition, result(definition, left, h('f')), result(definition, right, h('f')))
    assert assessment.relation == 'INDETERMINATE'
    assert assessment.revision_relation == 'DIFFERENT'

def test_explicit_cross_revision_policy_allows_only_projection_relative_comparison():
    definition = lossless_projection(revision_policy='EXPLICIT_CROSS_REVISION')
    left = subject('alt-a', h('a'), revision_id='rev-1', revision_fingerprint=h('1'))
    right = subject('alt-b', h('b'), revision_id='rev-2', revision_fingerprint=h('2'))
    assessment = assess_semantic_equivalence(definition, result(definition, left, h('f')), result(definition, right, h('f')))
    assert assessment.relation == 'PROJECTION_EQUIVALENT'
    assert assessment.revision_relation == 'DIFFERENT'
