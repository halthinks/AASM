---- MODULE AASMHierarchicalMemory ----
EXTENDS Naturals
VARIABLES decision, obligation, evidence, history, stale, visible, tombstone, private, principal, selected, indexTouched, identity, used, budget
vars == <<decision, obligation, evidence, history, stale, visible, tombstone, private, principal, selected, indexTouched, identity, used, budget>>
Init == /\ decision=FALSE /\ obligation=FALSE /\ evidence=FALSE /\ history=FALSE /\ stale=FALSE /\ visible=FALSE /\ tombstone=FALSE /\ private\in BOOLEAN /\ principal\in BOOLEAN /\ selected=FALSE /\ indexTouched=FALSE /\ identity=1 /\ used=0 /\ budget=2
Propose == /\ ~decision /\ decision'=TRUE /\ UNCHANGED <<obligation,evidence,history,stale,visible,tombstone,private,principal,selected,indexTouched,identity,used,budget>>
Open == /\ decision /\ ~obligation /\ obligation'=TRUE /\ UNCHANGED <<decision,evidence,history,stale,visible,tombstone,private,principal,selected,indexTouched,identity,used,budget>>
Commit == /\ obligation /\ ~evidence /\ evidence'=TRUE /\ history'=TRUE /\ visible'=TRUE /\ UNCHANGED <<decision,obligation,stale,tombstone,private,principal,selected,indexTouched,identity,used,budget>>
Invalidate == /\ evidence /\ ~stale /\ stale'=TRUE /\ visible'=FALSE /\ selected'=FALSE /\ UNCHANGED <<decision,obligation,evidence,history,tombstone,private,principal,indexTouched,identity,used,budget>>
Forget == /\ evidence /\ ~tombstone /\ tombstone'=TRUE /\ visible'=FALSE /\ selected'=FALSE /\ UNCHANGED <<decision,obligation,evidence,history,stale,private,principal,indexTouched,identity,used,budget>>
Index == /\ evidence /\ ~indexTouched /\ indexTouched'=TRUE /\ UNCHANGED <<decision,obligation,evidence,history,stale,visible,tombstone,private,principal,selected,identity,used,budget>>
Project == /\ evidence /\ ~selected /\ selected'= visible /\ (~private \/ principal) /\ UNCHANGED <<decision,obligation,evidence,history,stale,visible,tombstone,private,principal,indexTouched,identity,used,budget>>
Consume == /\ used<budget /\ used'=used+1 /\ UNCHANGED <<decision,obligation,evidence,history,stale,visible,tombstone,private,principal,selected,indexTouched,identity,budget>>
Next == Propose \/ Open \/ Commit \/ Invalidate \/ Forget \/ Index \/ Project \/ Consume \/ UNCHANGED vars
Spec == Init /\ [][Next]_vars
MemoryAdmissionRequiresDecisionObligationEvidence == visible => decision /\ obligation /\ evidence
StaleSemanticMemoryExcluded == stale => ~visible /\ ~selected
TombstonePreservesHistory == tombstone => history /\ ~visible
DerivedIndexCannotChangeMemoryIdentity == indexTouched => identity=1
PrivateProjectionRequiresPrincipal == private /\ selected => principal
ContextBudgetBounded == used<=budget
=============================================================================
