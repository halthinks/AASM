---- MODULE AASMScopeHierarchy ----
EXTENDS Naturals, FiniteSets, TLC

CONSTANTS Root, Strategy, ArchitectureA, ImplementationA, ArchitectureB, ImplementationB

Scopes == {Root, Strategy, ArchitectureA, ImplementationA, ArchitectureB, ImplementationB}
BranchA == {ArchitectureA, ImplementationA}
BranchB == {ArchitectureB, ImplementationB}
Parents == [s \in Scopes |->
              CASE s = Root -> Root
                [] s = Strategy -> Root
                [] s = ArchitectureA -> Strategy
                [] s = ImplementationA -> ArchitectureA
                [] s = ArchitectureB -> Strategy
                [] s = ImplementationB -> ArchitectureB]

VARIABLES activeScopes, pinnedScopes, hardKnowledge, parentKnowledge,
          localOverride, branchAActive, branchBActive, restarted

vars == <<activeScopes, pinnedScopes, hardKnowledge, parentKnowledge,
          localOverride, branchAActive, branchBActive, restarted>>

Init == /\ activeScopes = Scopes
        /\ pinnedScopes = {Root, Strategy}
        /\ hardKnowledge = {"certified"}
        /\ parentKnowledge = "strategy-value"
        /\ localOverride = "none"
        /\ branchAActive = TRUE
        /\ branchBActive = TRUE
        /\ restarted = FALSE

OverrideA == /\ localOverride = "none"
             /\ localOverride' = "architecture-a-value"
             /\ UNCHANGED <<activeScopes, pinnedScopes, hardKnowledge,
                             parentKnowledge, branchAActive, branchBActive, restarted>>

BackjumpA == /\ branchAActive
             /\ branchAActive' = FALSE
             /\ activeScopes' = activeScopes \ BranchA
             /\ UNCHANGED <<pinnedScopes, hardKnowledge, parentKnowledge,
                             localOverride, branchBActive, restarted>>

RestartA == /\ ~restarted
           /\ restarted' = TRUE
           /\ branchAActive' = FALSE
           /\ activeScopes' = activeScopes \ BranchA
           /\ UNCHANGED <<pinnedScopes, hardKnowledge, parentKnowledge,
                           localOverride, branchBActive>>

Stutter == UNCHANGED vars
Next == OverrideA \/ BackjumpA \/ RestartA \/ Stutter
Spec == Init /\ [][Next]_vars

TypeOK == /\ activeScopes \subseteq Scopes
          /\ pinnedScopes \subseteq Scopes
          /\ branchAActive \in BOOLEAN
          /\ branchBActive \in BOOLEAN
          /\ restarted \in BOOLEAN

HierarchyIsAcyclic == /\ Parents[Root] = Root
                      /\ Parents[Strategy] = Root
                      /\ Parents[ArchitectureA] = Strategy
                      /\ Parents[ImplementationA] = ArchitectureA
                      /\ Parents[ArchitectureB] = Strategy
                      /\ Parents[ImplementationB] = ArchitectureB
RootAuthorityRetained == Root \in activeScopes
StrategyAuthorityRetained == Strategy \in activeScopes
PinnedParentRetained == pinnedScopes \subseteq activeScopes
CertifiedHardKnowledgeRetained == "certified" \in hardKnowledge
LocalOverrideDoesNotMutateParent == parentKnowledge = "strategy-value"
SiblingBranchPreserved == branchBActive /\ BranchB \subseteq activeScopes
CausalBackjumpOnlyInvalidatesBranchA == ~branchAActive => BranchA \cap activeScopes = {}
ScopedRestartPreservesParentsAndSiblings == restarted => {Root, Strategy} \cup BranchB \subseteq activeScopes

=============================================================================
