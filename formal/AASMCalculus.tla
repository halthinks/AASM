----------------------------- MODULE AASMCalculus -----------------------------
EXTENDS Naturals, TLC

CONSTANTS Decisions, Obligations

VARIABLES phase, active, locked, hardKnowledge, certifiedKnowledge,
          conflictOpen, resolvedConflict, unresolvedMandatory, epoch

vars == << phase, active, locked, hardKnowledge, certifiedKnowledge,
           conflictOpen, resolvedConflict, unresolvedMandatory, epoch >>

Phases == {"MODEL", "EXECUTE", "VERIFY", "CONFLICT", "RESTART", "COMPLETE", "FAIL"}
Terminal == {"COMPLETE", "FAIL"}

Init ==
    /\ phase = "MODEL"
    /\ active \in SUBSET Decisions
    /\ locked \in SUBSET Obligations
    /\ hardKnowledge = {}
    /\ certifiedKnowledge = {}
    /\ conflictOpen = FALSE
    /\ resolvedConflict = FALSE
    /\ unresolvedMandatory \in SUBSET Obligations
    /\ epoch = 0

Select ==
    /\ phase = "MODEL"
    /\ phase' = "EXECUTE"
    /\ UNCHANGED << active, locked, hardKnowledge, certifiedKnowledge,
                     conflictOpen, resolvedConflict, unresolvedMandatory, epoch >>

ObserveConflict ==
    /\ phase \in {"EXECUTE", "VERIFY"}
    /\ phase' = "CONFLICT"
    /\ conflictOpen' = TRUE
    /\ resolvedConflict' = FALSE
    /\ UNCHANGED << active, locked, hardKnowledge, certifiedKnowledge,
                     unresolvedMandatory, epoch >>

LearnCertified ==
    /\ phase = "CONFLICT"
    /\ conflictOpen
    /\ \E d \in Decisions :
         /\ certifiedKnowledge' = certifiedKnowledge \cup {d}
         /\ hardKnowledge' = hardKnowledge \cup {d}
    /\ conflictOpen' = FALSE
    /\ resolvedConflict' = TRUE
    /\ phase' = "MODEL"
    /\ UNCHANGED << active, locked, unresolvedMandatory, epoch >>

Restart ==
    /\ phase \notin Terminal
    /\ phase' = "RESTART"
    /\ active' \in SUBSET active
    /\ epoch' = epoch + 1
    /\ UNCHANGED << locked, hardKnowledge, certifiedKnowledge,
                     conflictOpen, resolvedConflict, unresolvedMandatory >>

RestartReturn ==
    /\ phase = "RESTART"
    /\ phase' = "MODEL"
    /\ UNCHANGED << active, locked, hardKnowledge, certifiedKnowledge,
                     conflictOpen, resolvedConflict, unresolvedMandatory, epoch >>

Unlock ==
    /\ phase \notin Terminal
    /\ \E o \in locked : locked' = locked \ {o}
    /\ UNCHANGED << phase, active, hardKnowledge, certifiedKnowledge,
                     conflictOpen, resolvedConflict, unresolvedMandatory, epoch >>

Dispose ==
    /\ phase \notin Terminal
    /\ \E o \in unresolvedMandatory : unresolvedMandatory' = unresolvedMandatory \ {o}
    /\ UNCHANGED << phase, active, locked, hardKnowledge, certifiedKnowledge,
                     conflictOpen, resolvedConflict, epoch >>

Complete ==
    /\ phase \notin Terminal
    /\ unresolvedMandatory = {}
    /\ phase' = "COMPLETE"
    /\ UNCHANGED << active, locked, hardKnowledge, certifiedKnowledge,
                     conflictOpen, resolvedConflict, unresolvedMandatory, epoch >>

Fail ==
    /\ phase \notin Terminal
    /\ phase' = "FAIL"
    /\ UNCHANGED << active, locked, hardKnowledge, certifiedKnowledge,
                     conflictOpen, resolvedConflict, unresolvedMandatory, epoch >>

TerminalStutter ==
    /\ phase \in Terminal
    /\ UNCHANGED vars

Next == Select \/ ObserveConflict \/ LearnCertified \/ Restart \/ RestartReturn \/
        Unlock \/ Dispose \/ Complete \/ Fail \/ TerminalStutter

Spec == Init /\ [][Next]_vars

TypeOK ==
    /\ phase \in Phases
    /\ active \in SUBSET Decisions
    /\ locked \in SUBSET Obligations
    /\ hardKnowledge \in SUBSET Decisions
    /\ certifiedKnowledge \in SUBSET Decisions
    /\ unresolvedMandatory \in SUBSET Obligations
    /\ epoch \in Nat

HardRequiresCertificate == hardKnowledge \subseteq certifiedKnowledge
CompleteIsSafe == phase = "COMPLETE" => unresolvedMandatory = {}
ResolvedNotOpen == resolvedConflict => ~conflictOpen

=============================================================================
