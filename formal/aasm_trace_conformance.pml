#define KNOWN 1
#define UNKNOWN 2
#define SUPPORTED 1
#define UNSUPPORTED 2

byte source[3];
byte projected[3];
byte support[3];
byte count = 0;
byte compiler_stage = 0;
bool source_valid;
bool candidate_ready = false;
bool admission_evidence = false;
bool durable_admitted = false;

init {
    atomic {
        source[0] = KNOWN; source[1] = UNKNOWN; source[2] = KNOWN;
        if :: source_valid = true :: source_valid = false fi;
    }
    do
    :: count < 3 ->
        atomic {
            projected[count] = source[count];
            if :: source[count] == UNKNOWN -> support[count] = UNSUPPORTED :: else -> support[count] = SUPPORTED fi;
            count++
        }
    :: compiler_stage < 4 -> compiler_stage++
    :: compiler_stage == 4 ->
        if
        :: source_valid -> compiler_stage = 5
        :: else -> compiler_stage = 8
        fi
    :: compiler_stage == 5 -> compiler_stage = 6
    :: compiler_stage == 6 && source_valid -> atomic { compiler_stage = 7; candidate_ready = true }
    :: candidate_ready && !admission_evidence -> admission_evidence = true
    :: candidate_ready && admission_evidence && !durable_admitted -> durable_admitted = true
    :: else -> break
    od;
    assert(count <= 3);
    assert(!candidate_ready || source_valid);
    assert(!durable_admitted || (source_valid && candidate_ready && admission_evidence));
    assert(source_valid || !durable_admitted);
    if
    :: count == 3 ->
        assert(projected[0] == source[0]); assert(projected[1] == source[1]); assert(projected[2] == source[2]);
        assert(support[0] == SUPPORTED); assert(support[1] == UNSUPPORTED); assert(support[2] == SUPPORTED)
    :: else -> skip
    fi
}
