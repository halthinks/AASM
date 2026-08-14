------------------------ MODULE AASMOptimizationPortfolio ------------------------
EXTENDS Naturals

VARIABLES model_admitted, task_leased, result_committed, result_evidence, policy_acted, truth_authorized

vars == <<model_admitted, task_leased, result_committed, result_evidence, policy_acted, truth_authorized>>

Init ==
  /\ model_admitted = FALSE
  /\ task_leased = FALSE
  /\ result_committed = FALSE
  /\ result_evidence = FALSE
  /\ policy_acted = FALSE
  /\ truth_authorized = FALSE

AdmitModel ==
  /\ ~model_admitted
  /\ model_admitted' = TRUE
  /\ UNCHANGED <<task_leased, result_committed, result_evidence, policy_acted, truth_authorized>>

LeaseTask ==
  /\ model_admitted
  /\ ~task_leased
  /\ task_leased' = TRUE
  /\ UNCHANGED <<model_admitted, result_committed, result_evidence, policy_acted, truth_authorized>>

CommitSolverResult ==
  /\ task_leased
  /\ ~result_committed
  /\ result_committed' = TRUE
  /\ result_evidence' = TRUE
  /\ UNCHANGED <<model_admitted, task_leased, policy_acted, truth_authorized>>

PolicyAuthorize ==
  /\ result_evidence
  /\ ~truth_authorized
  /\ policy_acted' = TRUE
  /\ truth_authorized' = TRUE
  /\ UNCHANGED <<model_admitted, task_leased, result_committed, result_evidence>>

Quiesce == UNCHANGED vars

Next == AdmitModel \/ LeaseTask \/ CommitSolverResult \/ PolicyAuthorize \/ Quiesce

ResultRequiresLease == result_committed => task_leased
ResultIsEvidence == result_committed => result_evidence
SolverNeverDirectlyAuthorizesKnowledge == truth_authorized => policy_acted

Spec == Init /\ [][Next]_vars

=============================================================================
