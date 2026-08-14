----------------------------- MODULE AASMGovernedSII -----------------------------
EXTENDS Naturals

VARIABLES proposer_bound,
          meter_bound,
          policy_active,
          measurement_recorded,
          lease_issued,
          resource_authority,
          budget_limit,
          budget_used,
          required_verification_enabled,
          truth_promoted_by_sii,
          state_mutated_by_sii,
          self_verified_by_sii

vars == <<proposer_bound, meter_bound, policy_active, measurement_recorded,
          lease_issued, resource_authority, budget_limit, budget_used,
          required_verification_enabled, truth_promoted_by_sii,
          state_mutated_by_sii, self_verified_by_sii>>

Init ==
  /\ proposer_bound = FALSE
  /\ meter_bound = FALSE
  /\ policy_active = FALSE
  /\ measurement_recorded = FALSE
  /\ lease_issued = FALSE
  /\ resource_authority = "PROPOSER"
  /\ budget_limit = 2
  /\ budget_used = 0
  /\ required_verification_enabled = TRUE
  /\ truth_promoted_by_sii = FALSE
  /\ state_mutated_by_sii = FALSE
  /\ self_verified_by_sii = FALSE

BindProposer ==
  /\ ~proposer_bound
  /\ proposer_bound' = TRUE
  /\ UNCHANGED <<meter_bound, policy_active, measurement_recorded,
                  lease_issued, resource_authority, budget_limit, budget_used,
                  required_verification_enabled, truth_promoted_by_sii,
                  state_mutated_by_sii, self_verified_by_sii>>

BindIndependentMeter ==
  /\ proposer_bound
  /\ ~meter_bound
  /\ meter_bound' = TRUE
  /\ UNCHANGED <<proposer_bound, policy_active, measurement_recorded,
                  lease_issued, resource_authority, budget_limit, budget_used,
                  required_verification_enabled, truth_promoted_by_sii,
                  state_mutated_by_sii, self_verified_by_sii>>

ActivatePolicy ==
  /\ proposer_bound
  /\ ~policy_active
  /\ policy_active' = TRUE
  /\ UNCHANGED <<proposer_bound, meter_bound, measurement_recorded,
                  lease_issued, resource_authority, budget_limit, budget_used,
                  required_verification_enabled, truth_promoted_by_sii,
                  state_mutated_by_sii, self_verified_by_sii>>

RecordIndependentMeasurement ==
  /\ proposer_bound
  /\ meter_bound
  /\ policy_active
  /\ ~measurement_recorded
  /\ measurement_recorded' = TRUE
  /\ UNCHANGED <<proposer_bound, meter_bound, policy_active,
                  lease_issued, resource_authority, budget_limit, budget_used,
                  required_verification_enabled, truth_promoted_by_sii,
                  state_mutated_by_sii, self_verified_by_sii>>

AttemptUnboundOrSelfMeasurement ==
  /\ ~meter_bound
  /\ UNCHANGED vars

IssueResourceLease ==
  /\ proposer_bound
  /\ policy_active
  /\ ~lease_issued
  /\ lease_issued' = TRUE
  /\ resource_authority' = "PROPOSER"
  /\ UNCHANGED <<proposer_bound, meter_bound, policy_active, measurement_recorded,
                  budget_limit, budget_used, required_verification_enabled,
                  truth_promoted_by_sii, state_mutated_by_sii,
                  self_verified_by_sii>>

SpendWithinLease ==
  /\ lease_issued
  /\ budget_used < budget_limit
  /\ budget_used' = budget_used + 1
  /\ UNCHANGED <<proposer_bound, meter_bound, policy_active, measurement_recorded,
                  lease_issued, resource_authority, budget_limit,
                  required_verification_enabled, truth_promoted_by_sii,
                  state_mutated_by_sii, self_verified_by_sii>>

AttemptOverspend ==
  /\ lease_issued
  /\ budget_used = budget_limit
  /\ UNCHANGED vars

Quiesce == UNCHANGED vars

Next == BindProposer
     \/ BindIndependentMeter
     \/ ActivatePolicy
     \/ RecordIndependentMeasurement
     \/ AttemptUnboundOrSelfMeasurement
     \/ IssueResourceLease
     \/ SpendWithinLease
     \/ AttemptOverspend
     \/ Quiesce

MeasurementRequiresBoundPrincipal == measurement_recorded => /\ proposer_bound /\ meter_bound /\ policy_active
LeaseRequiresActivePolicy == lease_issued => /\ proposer_bound /\ policy_active
ResourceAuthorityNeverEscalates == resource_authority = "PROPOSER"
SpendNeverExceedsLease == budget_used <= budget_limit
RequiredVerificationNeverReduced == required_verification_enabled
SIINeverPromotesTruth == ~truth_promoted_by_sii
SIINeverMutatesCanonicalState == ~state_mutated_by_sii
SIINeverSelfVerifies == ~self_verified_by_sii

Spec == Init /\ [][Next]_vars

=============================================================================
