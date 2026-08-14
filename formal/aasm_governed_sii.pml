bool proposer_bound = false;
bool meter_bound = false;
bool policy_active = false;
bool measurement_recorded = false;
bool lease_issued = false;
bool required_verification_enabled = true;
bool truth_promoted_by_sii = false;
bool state_mutated_by_sii = false;
bool self_verified_by_sii = false;
byte budget_limit = 2;
byte budget_used = 0;
byte resource_authority = 1; /* 1 == PROPOSER */

active proctype AASMGovernedSII() {
  do
  :: (!proposer_bound) -> proposer_bound = true
  :: (proposer_bound && !meter_bound) -> meter_bound = true
  :: (proposer_bound && !policy_active) -> policy_active = true
  :: (proposer_bound && meter_bound && policy_active && !measurement_recorded) ->
       measurement_recorded = true;
       assert(proposer_bound && meter_bound && policy_active)
  :: (!meter_bound) ->
       /* unbound/self-style measurement attempt is rejected */
       assert(!measurement_recorded)
  :: (proposer_bound && policy_active && !lease_issued) ->
       lease_issued = true;
       resource_authority = 1;
       assert(resource_authority == 1)
  :: (lease_issued && budget_used < budget_limit) ->
       budget_used++;
       assert(budget_used <= budget_limit)
  :: (lease_issued && budget_used == budget_limit) ->
       /* an overspend attempt has no state transition */
       assert(budget_used <= budget_limit)
  :: else ->
       assert(!measurement_recorded || (proposer_bound && meter_bound && policy_active));
       assert(!lease_issued || (proposer_bound && policy_active));
       assert(resource_authority == 1);
       assert(budget_used <= budget_limit);
       assert(required_verification_enabled);
       assert(!truth_promoted_by_sii);
       assert(!state_mutated_by_sii);
       assert(!self_verified_by_sii);
       break
  od
}
