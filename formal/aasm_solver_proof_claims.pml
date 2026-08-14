bool solver_claimed = false;
bool proof_checked = false;
bool checker_independent = false;
bool exact_binding = false;
bool proof_passed = false;
bool proof_failed = false;
bool proof_unsupported = false;
bool proof_certified = false;
bool policy_acted = false;
bool truth_authorized = false;

active proctype ProofClaims() {
  solver_claimed = true;

  if
  :: proof_checked = true;
     checker_independent = true;
     exact_binding = true;
     proof_passed = true
  :: proof_checked = true;
     checker_independent = true;
     exact_binding = true;
     proof_failed = true
  :: proof_checked = true;
     checker_independent = true;
     exact_binding = true;
     proof_unsupported = true
  fi;

  if
  :: (proof_checked && checker_independent && exact_binding && proof_passed) -> proof_certified = true
  :: else -> skip
  fi;

  assert(!proof_certified || checker_independent);
  assert(!proof_certified || exact_binding);
  assert(!proof_certified || proof_passed);
  assert(!proof_certified || proof_checked);
  assert(!proof_failed || !proof_certified);
  assert(!proof_unsupported || !proof_certified);

  if
  :: proof_certified -> policy_acted = true; truth_authorized = true
  :: else -> skip
  fi;

  assert(!truth_authorized || policy_acted)
}
