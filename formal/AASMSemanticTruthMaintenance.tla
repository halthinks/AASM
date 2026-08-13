---- MODULE AASMSemanticTruthMaintenance ----
EXTENDS Naturals, FiniteSets

CONSTANTS Root, Dependent, Sibling

VARIABLES planRecorded, applied, stale, decisionState, obligationState, reactiveDerived, handlerExecuted
vars == <<planRecorded, applied, stale, decisionState, obligationState, reactiveDerived, handlerExecuted>>

Init == /\ planRecorded = FALSE
        /\ applied = FALSE
        /\ stale = {}
        /\ decisionState = "ACTIVE"
        /\ obligationState = "COMMITTED"
        /\ reactiveDerived = FALSE
        /\ handlerExecuted = FALSE

RecordPlan == /\ ~planRecorded
              /\ planRecorded' = TRUE
              /\ UNCHANGED <<applied, stale, decisionState, obligationState, reactiveDerived, handlerExecuted>>

ApplyTruthMaintenance ==
    /\ planRecorded
    /\ ~applied
    /\ applied' = TRUE
    /\ stale' = {Root, Dependent}
    /\ decisionState' = "INVALIDATED"
    /\ obligationState' = "NEEDS_REVALIDATION"
    /\ UNCHANGED <<planRecorded, reactiveDerived, handlerExecuted>>

DeriveReactive ==
    /\ ~reactiveDerived
    /\ reactiveDerived' = TRUE
    /\ handlerExecuted' = FALSE
    /\ UNCHANGED <<planRecorded, applied, stale, decisionState, obligationState>>

Stutter == UNCHANGED vars
Next == RecordPlan \/ ApplyTruthMaintenance \/ DeriveReactive \/ Stutter

TypeOK == /\ planRecorded \in BOOLEAN
          /\ applied \in BOOLEAN
          /\ stale \subseteq {Root, Dependent, Sibling}
          /\ decisionState \in {"ACTIVE", "INVALIDATED"}
          /\ obligationState \in {"COMMITTED", "NEEDS_REVALIDATION"}
          /\ reactiveDerived \in BOOLEAN
          /\ handlerExecuted \in BOOLEAN
CompletionRequiresPlan == applied => planRecorded
AffectedDescendantsOnly == stale \subseteq {Root, Dependent}
RootAndDependentStaleAfterApply == applied => stale = {Root, Dependent}
UnrelatedSiblingPreserved == Sibling \notin stale
DecisionInvalidatedAfterApply == applied => decisionState = "INVALIDATED"
ConsumedWorkReopensAfterApply == applied => obligationState = "NEEDS_REVALIDATION"
ReactiveDerivationNeverExecutesHandler == ~handlerExecuted

=============================================================================
