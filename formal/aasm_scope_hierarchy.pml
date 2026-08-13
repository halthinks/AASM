#define ROOT 0
#define STRATEGY 1
#define ARCH_A 2
#define IMPL_A 3
#define ARCH_B 4
#define IMPL_B 5

bool active[6];
bool pinned[6];
bool hard_knowledge;
bool parent_knowledge;
bool local_override;
bool branch_a_active;
bool branch_b_active;
bool restarted;

init {
    atomic {
        active[ROOT] = true;
        active[STRATEGY] = true;
        active[ARCH_A] = true;
        active[IMPL_A] = true;
        active[ARCH_B] = true;
        active[IMPL_B] = true;
        pinned[ROOT] = true;
        pinned[STRATEGY] = true;
        hard_knowledge = true;
        parent_knowledge = true;
        branch_a_active = true;
        branch_b_active = true;
    }

    do
    :: !local_override -> local_override = true
    :: branch_a_active ->
        atomic {
            branch_a_active = false;
            active[ARCH_A] = false;
            active[IMPL_A] = false;
        }
    :: !restarted ->
        atomic {
            restarted = true;
            branch_a_active = false;
            active[ARCH_A] = false;
            active[IMPL_A] = false;
        }
    :: else -> break
    od;

    assert(active[ROOT]);
    assert(active[STRATEGY]);
    assert(!pinned[ROOT] || active[ROOT]);
    assert(!pinned[STRATEGY] || active[STRATEGY]);
    assert(hard_knowledge);
    assert(parent_knowledge);
    assert(branch_b_active);
    assert(active[ARCH_B]);
    assert(active[IMPL_B]);
    assert(branch_a_active || (!active[ARCH_A] && !active[IMPL_A]));
    assert(!restarted || (active[ROOT] && active[STRATEGY] && active[ARCH_B] && active[IMPL_B]));
}
