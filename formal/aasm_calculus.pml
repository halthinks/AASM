mtype = { MODEL, EXECUTE, VERIFY, CONFLICT, RESTART, COMPLETE, FAIL };

mtype phase = MODEL;
byte active_mask = 0;
byte candidate_mask = 0;
bool soft_knowledge = false;
bool registered_certificate = false;
bool verified_certificate = false;
bool hard_knowledge = false;
bool conflict_open = false;
bool resolved_conflict = false;
bool unresolved_mandatory = true;
bool locked = true;
byte epoch = 0;
byte fairness_debt = 0;

#define MAX_EPOCH 2
#define MAX_FAIRNESS_DEBT 2
#define TERMINAL (phase == COMPLETE || phase == FAIL)
#define CAN_DELAY (!unresolved_mandatory || fairness_debt < MAX_FAIRNESS_DEBT)
#define HARD_REQUIRES_CERT (!hard_knowledge || verified_certificate)
#define VERIFIED_REQUIRES_REGISTRATION (!verified_certificate || registered_certificate)
#define HARD_COMES_FROM_SOFT (!hard_knowledge || soft_knowledge)
#define COMPLETE_SAFE (phase != COMPLETE || !unresolved_mandatory)
#define RESOLVED_NOT_OPEN (!resolved_conflict || !conflict_open)
#define CANDIDATE_ATOMIC (active_mask == 0 || active_mask == 3)
#define NO_PENDING_OUTSIDE_MODEL (phase == MODEL || candidate_mask == 0)

inline AGE_FAIRNESS()
{
    if
    :: (unresolved_mandatory && fairness_debt < MAX_FAIRNESS_DEBT) -> fairness_debt++
    :: else -> skip
    fi
}

inline CHECK_INVARIANTS()
{
    assert(HARD_REQUIRES_CERT);
    assert(VERIFIED_REQUIRES_REGISTRATION);
    assert(HARD_COMES_FROM_SOFT);
    assert(COMPLETE_SAFE);
    assert(RESOLVED_NOT_OPEN);
    assert(CANDIDATE_ATOMIC);
    assert(NO_PENDING_OUTSIDE_MODEL)
}

active proctype AASM()
{
    CHECK_INVARIANTS();
    do
    :: (phase == MODEL && candidate_mask == 0 && CAN_DELAY) ->
         candidate_mask = 3;
         AGE_FAIRNESS();
         CHECK_INVARIANTS()

    :: (phase == MODEL && candidate_mask != 0 && CAN_DELAY) ->
         atomic {
             active_mask = candidate_mask;
             candidate_mask = 0;
             phase = EXECUTE;
             AGE_FAIRNESS()
         };
         CHECK_INVARIANTS()

    :: (phase == EXECUTE && CAN_DELAY) ->
         phase = VERIFY;
         AGE_FAIRNESS();
         CHECK_INVARIANTS()

    :: ((phase == EXECUTE || phase == VERIFY) && CAN_DELAY) ->
         phase = CONFLICT;
         conflict_open = true;
         resolved_conflict = false;
         AGE_FAIRNESS();
         CHECK_INVARIANTS()

    :: (phase == CONFLICT && conflict_open && !soft_knowledge && CAN_DELAY) ->
         soft_knowledge = true;
         AGE_FAIRNESS();
         CHECK_INVARIANTS()

    :: (phase == CONFLICT && conflict_open && soft_knowledge && !registered_certificate && CAN_DELAY) ->
         registered_certificate = true;
         AGE_FAIRNESS();
         CHECK_INVARIANTS()

    :: (phase == CONFLICT && conflict_open && registered_certificate && !verified_certificate && CAN_DELAY) ->
         verified_certificate = true;
         AGE_FAIRNESS();
         CHECK_INVARIANTS()

    :: (phase == CONFLICT && conflict_open && soft_knowledge && verified_certificate && !hard_knowledge && CAN_DELAY) ->
         hard_knowledge = true;
         conflict_open = false;
         resolved_conflict = true;
         phase = MODEL;
         AGE_FAIRNESS();
         CHECK_INVARIANTS()

    :: (phase == CONFLICT && conflict_open && CAN_DELAY) ->
         conflict_open = false;
         resolved_conflict = true;
         phase = MODEL;
         AGE_FAIRNESS();
         CHECK_INVARIANTS()

    :: ((phase == MODEL || phase == EXECUTE || phase == VERIFY) && epoch < MAX_EPOCH && CAN_DELAY) ->
         atomic {
             active_mask = 0;
             candidate_mask = 0;
             phase = RESTART;
             epoch++;
             AGE_FAIRNESS()
         };
         CHECK_INVARIANTS()

    :: (phase == RESTART && CAN_DELAY) ->
         phase = MODEL;
         AGE_FAIRNESS();
         CHECK_INVARIANTS()

    :: (!TERMINAL && locked && CAN_DELAY) ->
         locked = false;
         AGE_FAIRNESS();
         CHECK_INVARIANTS()

    :: (!TERMINAL && unresolved_mandatory) ->
         unresolved_mandatory = false;
         fairness_debt = 0;
         CHECK_INVARIANTS()

    :: (!TERMINAL && !unresolved_mandatory) ->
         phase = COMPLETE;
         CHECK_INVARIANTS()

    :: (!TERMINAL) ->
         phase = FAIL;
         CHECK_INVARIANTS()

    :: TERMINAL ->
         CHECK_INVARIANTS();
         break
    od
}

ltl fairness_progress {
    [] (unresolved_mandatory -> <> (!unresolved_mandatory || TERMINAL))
}
