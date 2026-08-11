----------------------------- MODULE AASMCalculus -----------------------------
EXTENDS Naturals, TLC

CONSTANTS Decisions, Obligations, MaxEpoch

VARIABLES phase,
          active,
          pendingCandidate,
          softKnowledge,
          registeredCertificates,
          verifiedCertificates,
          hardKnowledge,
          locked,
          conflictOpen,
          resolvedConflict,
          unresolvedMandatory,
          epoch

vars == << phase, active, pendingCandidate, softKnowledge,
           registeredCertificates, verifiedCertificates, hardKnowledge,
           locked, conflictOpen, resolvedConflict, unresolvedMandatory, epoch >>

Knowledge == << softKnowledge, registeredCertificates,
                verifiedCertificates, hardKnowledge >>
ConflictState == << conflictOpen, resolvedConflict >>
ObligationState == << locked, unresolvedMandatory >>

Phases == {"MODEL", "EXECUTE", "VERIFY", "CONFLICT", "RESTART", "COMPLETE", "FAIL"}
Terminal == {"COMPLETE", "FAIL"}

Init ==
    /\ phase = "MODEL"
    /\ active = {}
    /\ pendingCandidate = {}
    /\ softKnowledge = {}
    /\ registeredCertificates = {}
    /\ verifiedCertificates = {}
    /\ hardKnowledge = {}
    /\ locked \in SUBSET Obligations
    /\ conflictOpen = FALSE
    /\ resolvedConflict = FALSE
    /\ unresolvedMandatory \in SUBSET Obligations
    /\ epoch = 0

StageCandidate ==
    /\ phase = "MODEL"
    /\ pendingCandidate = {}
    /\ \E candidate \in SUBSET Decisions :
         /\ candidate # {}
         /\ pendingCandidate' = candidate
    /\ UNCHANGED << phase, active, Knowledge, ObligationState,
                     ConflictState, epoch >>

ActivateCandidate ==
    /\ phase = "MODEL"
    /\ pendingCandidate # {}
    /\ active' = pendingCandidate
    /\ pendingCandidate' = {}
    /\ phase' = "EXECUTE"
    /\ UNCHANGED << Knowledge, ObligationState, ConflictState, epoch >>

BeginVerify ==
    /\ phase = "EXECUTE"
    /\ phase' = "VERIFY"
    /\ UNCHANGED << active, pendingCandidate, Knowledge,
                     ObligationState, ConflictState, epoch >>

ObserveConflict ==
    /\ phase \in {"EXECUTE", "VERIFY"}
    /\ phase' = "CONFLICT"
    /\ conflictOpen' = TRUE
    /\ resolvedConflict' = FALSE
    /\ UNCHANGED << active, pendingCandidate, Knowledge,
                     ObligationState, epoch >>

LearnSoft ==
    /\ phase = "CONFLICT"
    /\ conflictOpen
    /\ \E d \in (Decisions \ softKnowledge) :
         softKnowledge' = softKnowledge \cup {d}
    /\ UNCHANGED << phase, active, pendingCandidate,
                     registeredCertificates, verifiedCertificates, hardKnowledge,
                     ObligationState, ConflictState, epoch >>

RegisterCertificate ==
    /\ phase = "CONFLICT"
    /\ conflictOpen
    /\ \E d \in (softKnowledge \ registeredCertificates) :
         registeredCertificates' = registeredCertificates \cup {d}
    /\ UNCHANGED << phase, active, pendingCandidate, softKnowledge,
                     verifiedCertificates, hardKnowledge,
                     ObligationState, ConflictState, epoch >>

VerifyCertificate ==
    /\ phase = "CONFLICT"
    /\ conflictOpen
    /\ \E d \in (registeredCertificates \ verifiedCertificates) :
         verifiedCertificates' = verifiedCertificates \cup {d}
    /\ UNCHANGED << phase, active, pendingCandidate, softKnowledge,
                     registeredCertificates, hardKnowledge,
                     ObligationState, ConflictState, epoch >>

PromoteHard ==
    /\ phase = "CONFLICT"
    /\ conflictOpen
    /\ \E d \in ((softKnowledge \cap verifiedCertificates) \ hardKnowledge) :
         hardKnowledge' = hardKnowledge \cup {d}
    /\ conflictOpen' = FALSE
    /\ resolvedConflict' = TRUE
    /\ phase' = "MODEL"
    /\ UNCHANGED << active, pendingCandidate, softKnowledge,
                     registeredCertificates, verifiedCertificates,
                     ObligationState, epoch >>

ResolveWithoutHard ==
    /\ phase = "CONFLICT"
    /\ conflictOpen
    /\ conflictOpen' = FALSE
    /\ resolvedConflict' = TRUE
    /\ phase' = "MODEL"
    /\ UNCHANGED << active, pendingCandidate, Knowledge,
                     ObligationState, epoch >>

Restart ==
    /\ phase \in {"MODEL", "EXECUTE", "VERIFY"}
    /\ epoch < MaxEpoch
    /\ phase' = "RESTART"
    /\ active' \in SUBSET active
    /\ pendingCandidate' = {}
    /\ epoch' = epoch + 1
    /\ UNCHANGED << Knowledge, ObligationState, ConflictState >>

RestartReturn ==
    /\ phase = "RESTART"
    /\ phase' = "MODEL"
    /\ UNCHANGED << active, pendingCandidate, Knowledge,
                     ObligationState, ConflictState, epoch >>

Unlock ==
    /\ phase \notin Terminal
    /\ \E o \in locked : locked' = locked \ {o}
    /\ UNCHANGED << phase, active, pendingCandidate, Knowledge,
                     conflictOpen, resolvedConflict, unresolvedMandatory, epoch >>

Dispose ==
    /\ phase \notin Terminal
    /\ \E o \in unresolvedMandatory :
         unresolvedMandatory' = unresolvedMandatory \ {o}
    /\ UNCHANGED << phase, active, pendingCandidate, Knowledge,
                     locked, ConflictState, epoch >>

Complete ==
    /\ phase \notin Terminal
    /\ pendingCandidate = {}
    /\ unresolvedMandatory = {}
    /\ phase' = "COMPLETE"
    /\ UNCHANGED << active, pendingCandidate, Knowledge,
                     ObligationState, ConflictState, epoch >>

Fail ==
    /\ phase \notin Terminal
    /\ pendingCandidate = {}
    /\ phase' = "FAIL"
    /\ UNCHANGED << active, pendingCandidate, Knowledge,
                     ObligationState, ConflictState, epoch >>

TerminalStutter ==
    /\ phase \in Terminal
    /\ UNCHANGED vars

Next == StageCandidate \/ ActivateCandidate \/ BeginVerify \/ ObserveConflict
     \/ LearnSoft \/ RegisterCertificate \/ VerifyCertificate \/ PromoteHard
     \/ ResolveWithoutHard \/ Restart \/ RestartReturn \/ Unlock \/ Dispose
     \/ Complete \/ Fail \/ TerminalStutter

Spec == Init /\ [][Next]_vars /\ WF_vars(Dispose)

TypeOK ==
    /\ phase \in Phases
    /\ active \in SUBSET Decisions
    /\ pendingCandidate \in SUBSET Decisions
    /\ softKnowledge \in SUBSET Decisions
    /\ registeredCertificates \in SUBSET Decisions
    /\ verifiedCertificates \in SUBSET Decisions
    /\ hardKnowledge \in SUBSET Decisions
    /\ locked \in SUBSET Obligations
    /\ unresolvedMandatory \in SUBSET Obligations
    /\ epoch \in 0..MaxEpoch

HardRequiresCertificate == hardKnowledge \subseteq verifiedCertificates
VerifiedRequiresRegistration == verifiedCertificates \subseteq registeredCertificates
HardComesFromSoft == hardKnowledge \subseteq softKnowledge
CompleteIsSafe == phase = "COMPLETE" => unresolvedMandatory = {}
ResolvedNotOpen == resolvedConflict => ~conflictOpen
CandidateActivationIsAtomic == phase # "MODEL" => pendingCandidate = {}
FairnessProgress ==
    [](unresolvedMandatory # {} => <>(unresolvedMandatory = {} \/ phase \in Terminal))

=============================================================================
