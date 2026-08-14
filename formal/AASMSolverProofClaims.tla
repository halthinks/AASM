------------------------ MODULE AASMSolverProofClaims ------------------------
EXTENDS Naturals

VARIABLES solver_claimed, proof_checked, checker_independent, exact_binding,
          proof_passed, proof_failed, proof_unsupported, proof_certified,
          policy_acted, truth_authorized

vars == <<solver_claimed, proof_checked, checker_independent, exact_binding,
          proof_passed, proof_failed, proof_unsupported, proof_certified,
          policy_acted, truth_authorized>>

Init ==
  /\ solver_claimed = FALSE
  /\ proof_checked = FALSE
  /\ checker_independent = FALSE
  /\ exact_binding = FALSE
  /\ proof_passed = FALSE
  /\ proof_failed = FALSE
  /\ proof_unsupported = FALSE
  /\ proof_certified = FALSE
  /\ policy_acted = FALSE
  /\ truth_authorized = FALSE

SolverAssert ==
  /\ ~solver_claimed
  /\ solver_claimed' = TRUE
  /\ UNCHANGED <<proof_checked, checker_independent, exact_binding,
                  proof_passed, proof_failed, proof_unsupported, proof_certified,
                  policy_acted, truth_authorized>>

CheckPass ==
  /\ solver_claimed
  /\ ~proof_checked
  /\ proof_checked' = TRUE
  /\ checker_independent' = TRUE
  /\ exact_binding' = TRUE
  /\ proof_passed' = TRUE
  /\ UNCHANGED <<solver_claimed, proof_failed, proof_unsupported, proof_certified,
                  policy_acted, truth_authorized>>

CheckFail ==
  /\ solver_claimed
  /\ ~proof_checked
  /\ proof_checked' = TRUE
  /\ checker_independent' = TRUE
  /\ exact_binding' = TRUE
  /\ proof_failed' = TRUE
  /\ UNCHANGED <<solver_claimed, proof_passed, proof_unsupported, proof_certified,
                  policy_acted, truth_authorized>>

CheckUnsupported ==
  /\ solver_claimed
  /\ ~proof_checked
  /\ proof_checked' = TRUE
  /\ checker_independent' = TRUE
  /\ exact_binding' = TRUE
  /\ proof_unsupported' = TRUE
  /\ UNCHANGED <<solver_claimed, proof_passed, proof_failed, proof_certified,
                  policy_acted, truth_authorized>>

CertifyProof ==
  /\ proof_checked
  /\ checker_independent
  /\ exact_binding
  /\ proof_passed
  /\ ~proof_certified
  /\ proof_certified' = TRUE
  /\ UNCHANGED <<solver_claimed, proof_checked, checker_independent, exact_binding,
                  proof_passed, proof_failed, proof_unsupported,
                  policy_acted, truth_authorized>>

PolicyAuthorize ==
  /\ proof_certified
  /\ ~truth_authorized
  /\ policy_acted' = TRUE
  /\ truth_authorized' = TRUE
  /\ UNCHANGED <<solver_claimed, proof_checked, checker_independent, exact_binding,
                  proof_passed, proof_failed, proof_unsupported, proof_certified>>

Quiesce == UNCHANGED vars

Next == SolverAssert \/ CheckPass \/ CheckFail \/ CheckUnsupported \/ CertifyProof \/ PolicyAuthorize \/ Quiesce

ProofCertifiedImpliesIndependentChecker == proof_certified => checker_independent
ProofCertifiedImpliesExactBinding == proof_certified => exact_binding
ProofCertifiedImpliesPassingCheck == proof_certified => proof_passed
SolverClaimNeverSelfCertifies == proof_certified => proof_checked
FailedProofNeverCertifies == proof_failed => ~proof_certified
UnsupportedProofNeverCertifies == proof_unsupported => ~proof_certified
ProofCertificateNeverDirectlyAuthorizesTruth == truth_authorized => policy_acted

Spec == Init /\ [][Next]_vars

=============================================================================
