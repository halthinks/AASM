bool pool_started = false;
bool partial_mode = false;
bool cursor_durable = false;
byte solution_count = 0;
byte exclusion_count = 0;
bool exhausted = false;
bool checker_independent = false;
bool checker_passed = false;
bool complete = false;
bool policy_acted = false;
bool truth_authorized = false;

active proctype AASMSolutionPools() {
  atomic { pool_started = true; cursor_durable = true; }
  do
  :: (!exhausted && solution_count < 3) ->
       atomic { solution_count++; exclusion_count++; cursor_durable = true; }
  :: (!exhausted && solution_count == 3) -> exhausted = true
  :: (exhausted && !checker_passed) ->
       atomic { checker_independent = true; checker_passed = true; }
  :: (exhausted && checker_independent && checker_passed && exclusion_count == solution_count && !partial_mode) ->
       complete = true
  :: complete -> break
  od;
  assert(!complete || exhausted);
  assert(!complete || checker_independent);
  assert(!complete || checker_passed);
  assert(!complete || cursor_durable);
  assert(!complete || exclusion_count == solution_count);
  assert(!partial_mode || !complete);
  if
  :: complete -> atomic { policy_acted = true; truth_authorized = true; }
  :: else -> skip
  fi;
  assert(!truth_authorized || policy_acted);
}
