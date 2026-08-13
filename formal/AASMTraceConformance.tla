---- MODULE AASMTraceConformance ----
EXTENDS Naturals, Sequences, FiniteSets

CONSTANT Known, Unknown

CompilerStages == {"PARSE", "RESOLVE", "NORMALIZE", "TYPE_CHECK", "VALIDATE", "FINGERPRINT", "INSTANTIATE", "DONE", "FAILED"}
VARIABLES source, projected, support, sourceValid, compilerStage, candidateReady, admissionEvidence, durableAdmitted
vars == <<source, projected, support, sourceValid, compilerStage, candidateReady, admissionEvidence, durableAdmitted>>

Init == /\ source = <<Known, Unknown, Known>>
        /\ projected = <<>>
        /\ support = <<>>
        /\ sourceValid \in BOOLEAN
        /\ compilerStage = "PARSE"
        /\ candidateReady = FALSE
        /\ admissionEvidence = FALSE
        /\ durableAdmitted = FALSE

ProjectNext == /\ Len(projected) < Len(source)
               /\ LET n == Len(projected) + 1
                      e == source[n]
                  IN /\ projected' = Append(projected, e)
                     /\ support' = Append(support, IF e = Unknown THEN "UNSUPPORTED" ELSE "SUPPORTED")
               /\ UNCHANGED <<source, sourceValid, compilerStage, candidateReady, admissionEvidence, durableAdmitted>>

CompileStep ==
    \/ /\ compilerStage = "PARSE" /\ compilerStage' = "RESOLVE"
       /\ UNCHANGED <<source, projected, support, sourceValid, candidateReady, admissionEvidence, durableAdmitted>>
    \/ /\ compilerStage = "RESOLVE" /\ compilerStage' = "NORMALIZE"
       /\ UNCHANGED <<source, projected, support, sourceValid, candidateReady, admissionEvidence, durableAdmitted>>
    \/ /\ compilerStage = "NORMALIZE" /\ compilerStage' = "TYPE_CHECK"
       /\ UNCHANGED <<source, projected, support, sourceValid, candidateReady, admissionEvidence, durableAdmitted>>
    \/ /\ compilerStage = "TYPE_CHECK" /\ compilerStage' = "VALIDATE"
       /\ UNCHANGED <<source, projected, support, sourceValid, candidateReady, admissionEvidence, durableAdmitted>>
    \/ /\ compilerStage = "VALIDATE"
       /\ compilerStage' = IF sourceValid THEN "FINGERPRINT" ELSE "FAILED"
       /\ UNCHANGED <<source, projected, support, sourceValid, candidateReady, admissionEvidence, durableAdmitted>>
    \/ /\ compilerStage = "FINGERPRINT" /\ compilerStage' = "INSTANTIATE"
       /\ UNCHANGED <<source, projected, support, sourceValid, candidateReady, admissionEvidence, durableAdmitted>>
    \/ /\ compilerStage = "INSTANTIATE" /\ sourceValid
       /\ compilerStage' = "DONE" /\ candidateReady' = TRUE
       /\ UNCHANGED <<source, projected, support, sourceValid, admissionEvidence, durableAdmitted>>

RecordAdmissionEvidence == /\ candidateReady /\ ~admissionEvidence
                           /\ admissionEvidence' = TRUE
                           /\ UNCHANGED <<source, projected, support, sourceValid, compilerStage, candidateReady, durableAdmitted>>
AdmitCandidate == /\ candidateReady /\ admissionEvidence /\ ~durableAdmitted
                  /\ durableAdmitted' = TRUE
                  /\ UNCHANGED <<source, projected, support, sourceValid, compilerStage, candidateReady, admissionEvidence>>
Stutter == UNCHANGED vars
Next == ProjectNext \/ CompileStep \/ RecordAdmissionEvidence \/ AdmitCandidate \/ Stutter
Spec == Init /\ [][Next]_vars

TypeOK == /\ source \in Seq({Known, Unknown})
          /\ projected \in Seq({Known, Unknown})
          /\ support \in Seq({"SUPPORTED", "UNSUPPORTED"})
          /\ sourceValid \in BOOLEAN /\ compilerStage \in CompilerStages
          /\ candidateReady \in BOOLEAN /\ admissionEvidence \in BOOLEAN /\ durableAdmitted \in BOOLEAN
NoDroppedPrefix == projected = SubSeq(source, 1, Len(projected))
SupportAligned == Len(projected) = Len(support)
UnknownExplicit == \A i \in 1..Len(projected): projected[i] = Unknown => support[i] = "UNSUPPORTED"
KnownSupported == \A i \in 1..Len(projected): projected[i] = Known => support[i] = "SUPPORTED"
InvalidSourceNeverAdmitted == ~sourceValid => ~durableAdmitted
CandidateRequiresValidSource == candidateReady => sourceValid
AdmissionRequiresEvidence == durableAdmitted => admissionEvidence /\ candidateReady /\ sourceValid

=============================================================================
