bool model_admitted = false;
bool task_leased = false;
bool result_committed = false;
bool result_evidence = false;
bool policy_acted = false;
bool truth_authorized = false;

active proctype AASMOptimizationPortfolio() {
  do
  :: (!model_admitted) -> model_admitted = true
  :: (model_admitted && !task_leased) -> task_leased = true
  :: (task_leased && !result_committed) ->
       result_committed = true;
       result_evidence = true;
       assert(task_leased);
       assert(result_evidence);
       assert(!truth_authorized || policy_acted)
  :: (result_evidence && !truth_authorized) ->
       policy_acted = true;
       truth_authorized = true;
       assert(policy_acted)
  :: else ->
       assert(!result_committed || task_leased);
       assert(!result_committed || result_evidence);
       assert(!truth_authorized || policy_acted);
       break
  od
}
