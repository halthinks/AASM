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

vars == << phase,
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
           epoch >>

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
    /\ UNCHANGED << phase,
                     active,
                     softKnowledge,
                     registeredCertificates,
                     verifiedCertificates,
                     hardKnowledge,
                     locked,
                     conflictOpen,
                     resolvedConflict,
                     unresolvedMandatory,
                     epoch >>

ActivateCandidate ==
    /\ phase = "MODEL"
    /\ pendingCandidate # {}
    /\ active' = pendingCandidate
    /\ pendingCandidate' = {}
    /\ phase' = "EXECUTE"
    /\ UNCHANGED << softKnowledge,
                     registeredCertificates,
                     verifiedCertificates,
                     hardKnowledge,
                     locked,
                     conflictOpen,
                     resolvedConflict,
                     unresolvedMandatory,
                     epoch >>

BeginVerify ==
    /\ phase = "EXECUTE"
    /\ phase' = "VERIFY"
    /\ UNCHANGED << active,
                     pendingCandidate,
                     softKnowledge,
                     registeredCertificates,
                     verifiedCertificates,
                     hardKnowledge,
                     locked,
                     conflictOpen,
                     resolvedConflict,
                     unresolvedMandatory,
                     epoch >>

ObserveConflict ==
    /\ phase \in {"EXECUTE", "VERIFY"}
    /\ phase' = "CONFLICT"
    /\ conflictOpen' = TRUE
    /\ resolvedConflict' = FALSE
    /\ UNCHANGED << active,
                     pendingCandidate,
                     softKnowledge,
                     registeredCertificates,
                     verifiedCertificates,
                     hardKnowledge,
                     locked,
                     unresolvedMandatory,
                     epoch >>

LearnSoft ==
    /\ phase = "CONFLICT"
    /\ conflictOpen
    /\ \E d \in (Decisions \ softKnowledge) :
         softKnowledge' = softKnowledge \cup {d}
    /\ UNCHANGED << phase,
                     active,
                     pendingCandidate,
                     registeredCertificates,
                     verifiedCertificates,
                     hardKnowledge,
                     locked,
                     conflictOpen,
                     resolvedConflict,
                     unresolvedMandatory,
                     epoch >>

RegisterCertificate ==
    /\ phase = "CONFLICT"
    /\ conflictOpen
    /\ \E d \in (softKnowledge \ registeredCertificates) :
         registeredCertificates' = registeredCertificates \cup {d}
    /\ UNCHANGED << phase,
                     active,
                     pendingCandidate,
                     softKnowledge,
                     verifiedCertificates,
                     hardKnowledge,
                     locked,
                     conflictOpen,
                     resolvedConflict,
                     unresolvedMandatory,
                     epoch >>

VerifyCertificate ==
    /\ phase = "CONFLICT"
    /\ conflictOpen
    /\ \E d \in (registeredCertificates \ verifiedCertificates) :
         verifiedCertificates' = verifiedCertificates \cup {d}
    /\ UNCHANGED << phase,
                     active,
                     pendingCandidate,
                     softKnowledge,
                     registeredCertificates,
                     hardKnowledge,
                     locked,
                     conflictOpen,
                     resolvedConflict,
                     unresolvedMandatory,
                     epoch >>

PromoteHard ==
    /\ phase = "CONFLICT"
    /\ conflictOpen
    /\ \E d \in ((softKnowledge \cap verifiedCertificates) \ hardKnowledge) :
         hardKnowledge' = hardKnowledge \cup {d}
    /\ conflictOpen' = FALSE
    /\ resolvedConflict' = TRUE
    /\ phase' = "MODEL"
    /\ UNCHANGED << active,
                     pendingCandidate,
                     softKnowledge,
                     registeredCertificates,
                     verifiedCertificates,
                     locked,
                     unresolvedMandatory,
                     epoch >>

ResolveWithoutHard ==
    /\ phase = "CONFLICT"
    /\ conflictOpen
    /\ conflictOpen' = FALSE
    /\ resolvedConflict' = TRUE
    /\ phase' = "MODEL"
    /\ UNCHANGED << active,
                     pendingCandidate,
                     softKnowledge,
                     registeredCertificates,
                     verifiedCertificates,
                     hardKnowledge,
                     locked,
                     unresolvedMandatory,
                     epoch >>

Restart ==
    /\ phase \in {"MODEL", "EXECUTE", "VERIFY"}
    /\ epoch < MaxEpoch
    /\ phase' = "RESTART"
    /\ active' \in SUBSET active
    /\ pendingCandidate' = {}
    /\ epoch' = epoch + 1
    /\ UNCHANGED << softKnowledge,
                     registeredCertificates,
                     verifiedCertificates,
                     hardKnowledge,
                     locked,
                     conflictOpen,
                     resolvedConflict,
                     unresolvedMandatory >>

RestartReturn ==
    /\ phase = "RESTART"
    /\ phase' = "MODEL"
    /\ UNCHANGED << active,
                     pendingCandidate,
                     softKnowledge,
                     registeredCertificates,
                     verifiedCertificates,
                     hardKnowledge,
                     locked,
                     conflictOpen,
                     resolvedConflict,
                     unresolvedMandatory,
                     epoch >>

Unlock ==
    /\ phase \notin Terminal
    /\ \E o \in locked : locked' = locked \ {o}
    /\ UNCHANGED << phase,
                     active,
                     pendingCandidate,
                     softKnowledge,
                     registeredCertificates,
                     verifiedCertificates,
                     hardKnowledge,
                     conflictOpen,
                     resolvedConflict,
                     unresolvedMandatory,
                     epoch >>

Dispose ==
    /\ phase \notin Terminal
    /\ \E o \in unresolvedMandatory :
         unresolvedMandatory' = unresolvedMandatory \ {o}
    /\ UNCHANGED << phase,
                     active,
                     pendingCandidate,
                     softKnowledge,
                     registeredCertificates,
                     verifiedCertificates,
                     hardKnowledge,
                     locked,
                     conflictOpen,
                     resolvedConflict,
                     epoch >>

Complete ==
    /\ phase \notin Terminal
    /\ unresolvedMandatory = {}
    /\ phase' = "COMPLETE"
    /\ UNCHANGED << active,
                     pendingCandidate,
                     softKnowledge,
                     registeredCertificates,
                     verifiedCertificates,
                     hardKnowledge,
                     locked,
                     conflictOpen,
                     resolvedConflict,
                     unresolvedMandatory,
                     epoch >>

Fail ==
    /\ phase \notin Terminal
    /\ phase' = "FAIL"
    /\ UNCHANGED << active,
                     pendingCandidate,
                     softKnowledge,
                     registeredCertificates,
                     verifiedCertificates,
                     hardKnowledge,
                     locked,
                     conflictOpen,
                     resolvedConflict,
                     unresolvedMandatory,
                     epoch >>

TerminalStutter ==
    /\ phase \in Terminal
    /\ UNCHANGED vars

Next == StageCandidate
     \/ ActivateCandidate
     \/ BeginVerify
     \/ ObserveConflict
     \/ LearnSoft
     \/ RegisterCertificate
     \/ VerifyCertificate
     \/ PromoteHard
     \/ ResolveWithoutHard
     \/ Restart
     \/ RestartReturn
     \/ Unlock
     \/ Dispose
     \/ Complete
     \/ Fail
     \/ TerminalStutter

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
