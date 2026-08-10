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

active proctype AASM()
{
    do
    :: phase == MODEL -> phase = EXECUTE
    :: (phase == EXECUTE || phase == VERIFY) ->
         if
         :: phase = VERIFY
         :: phase = CONFLICT; conflict_open = true; resolved_conflict = false
         fi
    :: phase == CONFLICT && conflict_open ->
         certified_knowledge = true;
         hard_knowledge = true;
         conflict_open = false;
         resolved_conflict = true;
         phase = MODEL
    :: !TERMINAL -> phase = RESTART; epoch++
    :: phase == RESTART -> phase = MODEL
    :: !TERMINAL && unresolved_mandatory -> unresolved_mandatory = false
    :: !TERMINAL && !unresolved_mandatory -> phase = COMPLETE
    :: !TERMINAL -> phase = FAIL
    :: TERMINAL -> skip
    od
}

never {
T0_init:
    if
    :: (!HARD_REQUIRES_CERT || !COMPLETE_SAFE || !RESOLVED_NOT_OPEN) -> goto accept_all
    :: else -> goto T0_init
    fi;
accept_all:
    skip
}
