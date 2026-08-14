---------------------- MODULE AASMSolutionPools ----------------------
EXTENDS Naturals

VARIABLES pool_started, partial_mode, cursor_durable, solution_count,
          exclusion_count, exhausted, checker_independent, checker_passed,
          complete, truth_authorized, policy_acted

vars == <<pool_started, partial_mode, cursor_durable, solution_count,
          exclusion_count, exhausted, checker_independent, checker_passed,
          complete, truth_authorized, policy_acted>>

Init ==
  /\ pool_started = FALSE
  /\ partial_mode = FALSE
  /\ cursor_durable = FALSE
  /\ solution_count = 0
  /\ exclusion_count = 0
  /\ exhausted = FALSE
  /\ checker_independent = FALSE
  /\ checker_passed = FALSE
  /\ complete = FALSE
  /\ truth_authorized = FALSE
  /\ policy_acted = FALSE

StartComplete ==
  /\ ~pool_started
  /\ pool_started' = TRUE
  /\ cursor_durable' = TRUE
  /\ UNCHANGED <<partial_mode, solution_count, exclusion_count, exhausted,
                  checker_independent, checker_passed, complete,
                  truth_authorized, policy_acted>>

StartPartial ==
  /\ ~pool_started
  /\ pool_started' = TRUE
  /\ partial_mode' = TRUE
  /\ UNCHANGED <<cursor_durable, solution_count, exclusion_count, exhausted,
                  checker_independent, checker_passed, complete,
                  truth_authorized, policy_acted>>

AcceptUnique ==
  /\ pool_started
  /\ ~exhausted
  /\ solution_count < 3
  /\ solution_count' = solution_count + 1
  /\ exclusion_count' = exclusion_count + 1
  /\ UNCHANGED <<pool_started, partial_mode, cursor_durable, exhausted,
                  checker_independent, checker_passed, complete,
                  truth_authorized, policy_acted>>

AdvanceCursor ==
  /\ pool_started
  /\ ~partial_mode
  /\ cursor_durable' = TRUE
  /\ UNCHANGED <<pool_started, partial_mode, solution_count, exclusion_count,
                  exhausted, checker_independent, checker_passed, complete,
                  truth_authorized, policy_acted>>

Exhaust ==
  /\ pool_started
  /\ ~partial_mode
  /\ cursor_durable
  /\ solution_count = 3
  /\ exhausted' = TRUE
  /\ UNCHANGED <<pool_started, partial_mode, cursor_durable, solution_count,
                  exclusion_count, checker_independent, checker_passed,
                  complete, truth_authorized, policy_acted>>

IndependentCheckPass ==
  /\ exhausted
  /\ ~partial_mode
  /\ checker_independent' = TRUE
  /\ checker_passed' = TRUE
  /\ UNCHANGED <<pool_started, partial_mode, cursor_durable, solution_count,
                  exclusion_count, exhausted, complete,
                  truth_authorized, policy_acted>>

CertifyComplete ==
  /\ exhausted
  /\ checker_independent
  /\ checker_passed
  /\ exclusion_count = solution_count
  /\ complete' = TRUE
  /\ UNCHANGED <<pool_started, partial_mode, cursor_durable, solution_count,
                  exclusion_count, exhausted, checker_independent,
                  checker_passed, truth_authorized, policy_acted>>

PolicyAuthorize ==
  /\ complete
  /\ policy_acted' = TRUE
  /\ truth_authorized' = TRUE
  /\ UNCHANGED <<pool_started, partial_mode, cursor_durable, solution_count,
                  exclusion_count, exhausted, checker_independent,
                  checker_passed, complete>>

Quiesce == UNCHANGED vars

Next == StartComplete \/ StartPartial \/ AcceptUnique \/ AdvanceCursor \/ Exhaust \/ IndependentCheckPass \/ CertifyComplete \/ PolicyAuthorize \/ Quiesce

CompleteImpliesExhausted == complete => exhausted
CompleteImpliesIndependentChecker == complete => checker_independent
CompleteImpliesPassingChecker == complete => checker_passed
CompleteImpliesDurableCursor == complete => cursor_durable
CompleteImpliesExclusionPerSolution == complete => exclusion_count = solution_count
PartialModeNeverClaimsComplete == partial_mode => ~complete
CompletenessNeverDirectlyAuthorizesTruth == truth_authorized => policy_acted

Spec == Init /\ [][Next]_vars

=============================================================================
