mtype = { MODEL, EXECUTE, VERIFY, CONFLICT, RESTART, COMPLETE, FAIL };

mtype phase = MODEL;
bool hard_knowledge = false;
bool certified_knowledge = false;
bool conflict_open = false;
bool resolved_conflict = false;
bool unresolved_mandatory = true;
byte epoch = 0;

#define TERMINAL (phase == COMPLETE || phase == FAIL)
#define HARD_REQUIRES_CERT (!hard_knowledge || certified_knowledge)
#define COMPLETE_SAFE (phase != COMPLETE || !unresolved_mandatory)
#define RESOLVED_NOT_OPEN (!resolved_conflict || !conflict_open)

inline CHECK_INVARIANTS()
{
    assert(HARD_REQUIRES_CERT);
    assert(COMPLETE_SAFE);
    assert(RESOLVED_NOT_OPEN)
}

active proctype AASM()
{
    CHECK_INVARIANTS();
    do
    :: phase == MODEL ->
         phase = EXECUTE;
         CHECK_INVARIANTS()
    :: (phase == EXECUTE || phase == VERIFY) ->
         if
         :: phase = VERIFY
         :: phase = CONFLICT; conflict_open = true; resolved_conflict = false
         fi;
         CHECK_INVARIANTS()
    :: phase == CONFLICT && conflict_open ->
         certified_knowledge = true;
         hard_knowledge = true;
         conflict_open = false;
         resolved_conflict = true;
         phase = MODEL;
         CHECK_INVARIANTS()
    :: !TERMINAL ->
         phase = RESTART;
         epoch++;
         CHECK_INVARIANTS()
    :: phase == RESTART ->
         phase = MODEL;
         CHECK_INVARIANTS()
    :: !TERMINAL && unresolved_mandatory ->
         unresolved_mandatory = false;
         CHECK_INVARIANTS()
    :: !TERMINAL && !unresolved_mandatory ->
         phase = COMPLETE;
         CHECK_INVARIANTS()
    :: !TERMINAL ->
         phase = FAIL;
         CHECK_INVARIANTS()
    :: TERMINAL ->
         CHECK_INVARIANTS();
         skip
    od
}
