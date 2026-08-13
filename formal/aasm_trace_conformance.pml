#define KNOWN 1
#define UNKNOWN 2
#define SUPPORTED 1
#define UNSUPPORTED 2

byte source[3];
byte projected[3];
byte support[3];
byte count = 0;

init {
    atomic {
        source[0] = KNOWN;
        source[1] = UNKNOWN;
        source[2] = KNOWN;
    }
    do
    :: count < 3 ->
        atomic {
            projected[count] = source[count];
            if
            :: source[count] == UNKNOWN -> support[count] = UNSUPPORTED
            :: else -> support[count] = SUPPORTED
            fi;
            count++
        }
    :: else -> break
    od;
    assert(count == 3);
    assert(projected[0] == source[0]);
    assert(projected[1] == source[1]);
    assert(projected[2] == source[2]);
    assert(support[0] == SUPPORTED);
    assert(support[1] == UNSUPPORTED);
    assert(support[2] == SUPPORTED);
}
