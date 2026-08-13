---- MODULE AASMReusePlane ----
VARIABLES sourceValid, visible, environmentValid, dependencyValid, fresh, effectReusable, certified, skipped

vars == <<sourceValid, visible, environmentValid, dependencyValid, fresh, effectReusable, certified, skipped>>

Init ==
    /\ sourceValid \in BOOLEAN
    /\ visible \in BOOLEAN
    /\ environmentValid \in BOOLEAN
    /\ dependencyValid \in BOOLEAN
    /\ fresh \in BOOLEAN
    /\ effectReusable \in BOOLEAN
    /\ certified = FALSE
    /\ skipped = FALSE

Certify ==
    /\ sourceValid /\ visible /\ environmentValid /\ dependencyValid /\ fresh /\ effectReusable
    /\ ~certified
    /\ certified' = TRUE
    /\ UNCHANGED <<sourceValid, visible, environmentValid, dependencyValid, fresh, effectReusable, skipped>>

Skip ==
    /\ certified /\ ~skipped
    /\ skipped' = TRUE
    /\ UNCHANGED <<sourceValid, visible, environmentValid, dependencyValid, fresh, effectReusable, certified>>

Next == Certify \/ Skip
Spec == Init /\ [][Next]_vars

SkipRequiresCertificate == skipped => certified
CertificateRequiresValidation == certified => sourceValid /\ visible /\ environmentValid /\ dependencyValid /\ fresh /\ effectReusable
CacheDeletionDoesNotDefineTruth == TRUE
====
