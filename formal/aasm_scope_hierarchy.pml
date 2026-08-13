#define ROOT 0
#define STRATEGY 1
#define ARCH_A 2
#define IMPL_A 3
#define ARCH_B 4
#define IMPL_B 5

bool scope_active[6];
bool pinned[6];
bool hard_knowledge;
bool parent_knowledge;
bool local_override;
bool branch_a_active;
bool branch_b_active;
bool restarted;

init {
    atomic {
        scope_active[ROOT] = true;
        scope_active[STRATEGY] = true;
        scope_active[ARCH_A] = true;
        scope_active[IMPL_A] = true;
        scope_active[ARCH_B] = true;
        scope_active[IMPL_B] = true;
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
            scope_active[ARCH_A] = false;
            scope_active[IMPL_A] = false;
        }
    :: !restarted ->
        atomic {
            restarted = true;
            branch_a_active = false;
            scope_active[ARCH_A] = false;
            scope_active[IMPL_A] = false;
        }
    :: else -> break
    od;

    assert(scope_active[ROOT]);
    assert(scope_active[STRATEGY]);
    assert(!pinned[ROOT] || scope_active[ROOT]);
    assert(!pinned[STRATEGY] || scope_active[STRATEGY]);
    assert(hard_knowledge);
    assert(parent_knowledge);
    assert(branch_b_active);
    assert(scope_active[ARCH_B]);
    assert(scope_active[IMPL_B]);
    assert(branch_a_active || (!scope_active[ARCH_A] && !scope_active[IMPL_A]));
    assert(!restarted || (scope_active[ROOT] && scope_active[STRATEGY] && scope_active[ARCH_B] && scope_active[IMPL_B]));
}
