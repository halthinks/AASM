bool pattern_admitted = false;
bool event_valid = false;
bool transition_proposed = false;
bool guards_satisfied = false;
bool transition_authorized = false;
bool transition_active = false;
bool formalized = false;
bool task_queued = false;
bool lease_held = false;
bool solver_result = false;
bool epistemic_verified = false;
bool epistemic_authorized = false;

active proctype AASMTypedCapabilities() {
    do
    :: (!pattern_admitted) -> pattern_admitted = true
    :: (pattern_admitted && !event_valid) -> event_valid = true
    :: (pattern_admitted && event_valid && !transition_proposed) -> transition_proposed = true
    :: (transition_proposed && !guards_satisfied) -> guards_satisfied = true
    :: (transition_proposed && guards_satisfied && !transition_authorized) -> transition_authorized = true
    :: (transition_authorized && !transition_active) -> transition_active = true
    :: (!formalized) -> formalized = true
    :: (formalized && !task_queued) -> task_queued = true
    :: (task_queued && !lease_held) -> lease_held = true
    :: (formalized && lease_held && !solver_result) -> solver_result = true
    :: (solver_result && !epistemic_verified) -> epistemic_verified = true
    :: (epistemic_verified && !epistemic_authorized) -> epistemic_authorized = true
    :: else -> skip
    od
}

ltl proposal_requires_admitted_pattern { [] (transition_proposed -> (pattern_admitted && event_valid)) }
ltl active_transition_requires_guards_and_authority { [] (transition_active -> (pattern_admitted && event_valid && transition_proposed && guards_satisfied && transition_authorized)) }
ltl solver_result_requires_formalization_and_lease { [] (solver_result -> (formalized && task_queued && lease_held)) }
ltl solver_never_directly_authorizes_knowledge { [] (epistemic_authorized -> (epistemic_verified && solver_result)) }
