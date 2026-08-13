bool plan_recorded = false;
bool applied = false;
bool root_stale = false;
bool dependent_stale = false;
bool sibling_stale = false;
bool decision_invalidated = false;
bool obligation_revalidation = false;
bool reactive_derived = false;
bool handler_executed = false;

active proctype SemanticTruthMaintenance()
{
    do
    :: !plan_recorded ->
        plan_recorded = true
    :: plan_recorded && !applied ->
        applied = true;
        root_stale = true;
        dependent_stale = true;
        decision_invalidated = true;
        obligation_revalidation = true
    :: !reactive_derived ->
        reactive_derived = true;
        handler_executed = false
    :: else -> break
    od;

    assert(!applied || plan_recorded);
    assert(!applied || root_stale);
    assert(!applied || dependent_stale);
    assert(!sibling_stale);
    assert(!applied || decision_invalidated);
    assert(!applied || obligation_revalidation);
    assert(!handler_executed)
}
