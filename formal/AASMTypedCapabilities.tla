---- MODULE AASMTypedCapabilities ----
EXTENDS Naturals

VARIABLES patternAdmitted, eventValid, transitionProposed, guardsSatisfied,
          transitionAuthorized, transitionActive, formalized, taskQueued,
          leaseHeld, solverResult, epistemicVerified, epistemicAuthorized

vars == <<patternAdmitted, eventValid, transitionProposed, guardsSatisfied,
          transitionAuthorized, transitionActive, formalized, taskQueued,
          leaseHeld, solverResult, epistemicVerified, epistemicAuthorized>>

Init ==
    /\ patternAdmitted = FALSE
    /\ eventValid = FALSE
    /\ transitionProposed = FALSE
    /\ guardsSatisfied = FALSE
    /\ transitionAuthorized = FALSE
    /\ transitionActive = FALSE
    /\ formalized = FALSE
    /\ taskQueued = FALSE
    /\ leaseHeld = FALSE
    /\ solverResult = FALSE
    /\ epistemicVerified = FALSE
    /\ epistemicAuthorized = FALSE

AdmitPattern ==
    /\ ~patternAdmitted
    /\ patternAdmitted' = TRUE
    /\ UNCHANGED <<eventValid, transitionProposed, guardsSatisfied, transitionAuthorized,
                   transitionActive, formalized, taskQueued, leaseHeld, solverResult,
                   epistemicVerified, epistemicAuthorized>>

ValidateTypedEvent ==
    /\ patternAdmitted
    /\ ~eventValid
    /\ eventValid' = TRUE
    /\ UNCHANGED <<patternAdmitted, transitionProposed, guardsSatisfied, transitionAuthorized,
                   transitionActive, formalized, taskQueued, leaseHeld, solverResult,
                   epistemicVerified, epistemicAuthorized>>

ProposeTransition ==
    /\ patternAdmitted /\ eventValid /\ ~transitionProposed
    /\ transitionProposed' = TRUE
    /\ UNCHANGED <<patternAdmitted, eventValid, guardsSatisfied, transitionAuthorized,
                   transitionActive, formalized, taskQueued, leaseHeld, solverResult,
                   epistemicVerified, epistemicAuthorized>>

SatisfyGuards ==
    /\ transitionProposed /\ ~guardsSatisfied
    /\ guardsSatisfied' = TRUE
    /\ UNCHANGED <<patternAdmitted, eventValid, transitionProposed, transitionAuthorized,
                   transitionActive, formalized, taskQueued, leaseHeld, solverResult,
                   epistemicVerified, epistemicAuthorized>>

AuthorizeTransition ==
    /\ transitionProposed /\ guardsSatisfied /\ ~transitionAuthorized
    /\ transitionAuthorized' = TRUE
    /\ UNCHANGED <<patternAdmitted, eventValid, transitionProposed, guardsSatisfied,
                   transitionActive, formalized, taskQueued, leaseHeld, solverResult,
                   epistemicVerified, epistemicAuthorized>>

ActivateTransition ==
    /\ transitionAuthorized /\ ~transitionActive
    /\ transitionActive' = TRUE
    /\ UNCHANGED <<patternAdmitted, eventValid, transitionProposed, guardsSatisfied,
                   transitionAuthorized, formalized, taskQueued, leaseHeld, solverResult,
                   epistemicVerified, epistemicAuthorized>>

Formalize ==
    /\ ~formalized
    /\ formalized' = TRUE
    /\ UNCHANGED <<patternAdmitted, eventValid, transitionProposed, guardsSatisfied,
                   transitionAuthorized, transitionActive, taskQueued, leaseHeld, solverResult,
                   epistemicVerified, epistemicAuthorized>>

QueueFormalTask ==
    /\ formalized /\ ~taskQueued
    /\ taskQueued' = TRUE
    /\ UNCHANGED <<patternAdmitted, eventValid, transitionProposed, guardsSatisfied,
                   transitionAuthorized, transitionActive, formalized, leaseHeld, solverResult,
                   epistemicVerified, epistemicAuthorized>>

AcquireLease ==
    /\ taskQueued /\ ~leaseHeld
    /\ leaseHeld' = TRUE
    /\ UNCHANGED <<patternAdmitted, eventValid, transitionProposed, guardsSatisfied,
                   transitionAuthorized, transitionActive, formalized, taskQueued, solverResult,
                   epistemicVerified, epistemicAuthorized>>

SolverReports ==
    /\ formalized /\ leaseHeld /\ ~solverResult
    /\ solverResult' = TRUE
    /\ UNCHANGED <<patternAdmitted, eventValid, transitionProposed, guardsSatisfied,
                   transitionAuthorized, transitionActive, formalized, taskQueued, leaseHeld,
                   epistemicVerified, epistemicAuthorized>>

RecordEpistemicVerification ==
    /\ solverResult /\ ~epistemicVerified
    /\ epistemicVerified' = TRUE
    /\ UNCHANGED <<patternAdmitted, eventValid, transitionProposed, guardsSatisfied,
                   transitionAuthorized, transitionActive, formalized, taskQueued, leaseHeld,
                   solverResult, epistemicAuthorized>>

PolicyAuthorizeKnowledge ==
    /\ epistemicVerified /\ ~epistemicAuthorized
    /\ epistemicAuthorized' = TRUE
    /\ UNCHANGED <<patternAdmitted, eventValid, transitionProposed, guardsSatisfied,
                   transitionAuthorized, transitionActive, formalized, taskQueued, leaseHeld,
                   solverResult, epistemicVerified>>

Stutter == UNCHANGED vars

Next ==
    AdmitPattern \/ ValidateTypedEvent \/ ProposeTransition \/ SatisfyGuards \/
    AuthorizeTransition \/ ActivateTransition \/ Formalize \/ QueueFormalTask \/
    AcquireLease \/ SolverReports \/ RecordEpistemicVerification \/
    PolicyAuthorizeKnowledge \/ Stutter

Spec == Init /\ [][Next]_vars

TypeOK ==
    /\ patternAdmitted \in BOOLEAN /\ eventValid \in BOOLEAN
    /\ transitionProposed \in BOOLEAN /\ guardsSatisfied \in BOOLEAN
    /\ transitionAuthorized \in BOOLEAN /\ transitionActive \in BOOLEAN
    /\ formalized \in BOOLEAN /\ taskQueued \in BOOLEAN /\ leaseHeld \in BOOLEAN
    /\ solverResult \in BOOLEAN /\ epistemicVerified \in BOOLEAN
    /\ epistemicAuthorized \in BOOLEAN

ProposalRequiresAdmittedPattern ==
    transitionProposed => patternAdmitted /\ eventValid

ActiveTransitionRequiresGuardsAndAuthority ==
    transitionActive => patternAdmitted /\ eventValid /\ transitionProposed /\
                        guardsSatisfied /\ transitionAuthorized

SolverResultRequiresFormalizationAndLease ==
    solverResult => formalized /\ taskQueued /\ leaseHeld

SolverNeverDirectlyAuthorizesKnowledge ==
    epistemicAuthorized => epistemicVerified /\ solverResult

=============================================================================
