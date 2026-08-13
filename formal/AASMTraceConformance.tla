---- MODULE AASMTraceConformance ----
EXTENDS Naturals, Sequences, FiniteSets

CONSTANT Known, Unknown

VARIABLES source, projected, support
vars == <<source, projected, support>>

Init == /\ source = <<Known, Unknown, Known>>
        /\ projected = <<>>
        /\ support = <<>>

ProjectNext == /\ Len(projected) < Len(source)
               /\ LET n == Len(projected) + 1
                      e == source[n]
                  IN /\ projected' = Append(projected, e)
                     /\ support' = Append(support, IF e = Unknown THEN "UNSUPPORTED" ELSE "SUPPORTED")
               /\ UNCHANGED source

Stutter == UNCHANGED vars
Next == ProjectNext \/ Stutter
Spec == Init /\ [][Next]_vars

TypeOK == /\ source \in Seq({Known, Unknown})
          /\ projected \in Seq({Known, Unknown})
          /\ support \in Seq({"SUPPORTED", "UNSUPPORTED"})
NoDroppedPrefix == projected = SubSeq(source, 1, Len(projected))
SupportAligned == Len(projected) = Len(support)
UnknownExplicit == \A i \in 1..Len(projected): projected[i] = Unknown => support[i] = "UNSUPPORTED"
KnownSupported == \A i \in 1..Len(projected): projected[i] = Known => support[i] = "SUPPORTED"

=============================================================================
