#include "m_fixed.h"

/* Return zero only when the original DoomGeneric arithmetic agrees. */
int doom_fixed_check(void) {
    return FixedMul(FRACUNIT + FRACUNIT / 2, FRACUNIT * 2) != FRACUNIT * 3
        || FixedMul(-FRACUNIT, FRACUNIT / 2) != -FRACUNIT / 2
        || FixedDiv(FRACUNIT * 3, FRACUNIT * 2) != FRACUNIT + FRACUNIT / 2
        || FixedDiv(FRACUNIT, 0) != 2147483647;
}

#ifdef BMO_HOST
int main(void) {
    return doom_fixed_check();
}
#else
#include "../../userspace/runtime/abi/bmo_abi.h"

extern _Noreturn void doom_probe_complete(void);

void bmo_main(void) {
    if (doom_fixed_check()) {
        __builtin_trap();
    }
    bmo_result reply = bmo_invoke(1, BMO_OP_ECHO, FRACUNIT * 3, 0, 0);
    if (reply.status != BMO_OK || reply.value != FRACUNIT * 3) {
        __builtin_trap();
    }
    reply = bmo_invoke(0, BMO_OP_ECHO, 0, 0, 0);
    if (reply.status != -2 || reply.value != 0) {
        __builtin_trap();
    }
    reply = bmo_wait(1, 0, 0);
    if (reply.status != -4 || reply.value != 0) {
        __builtin_trap();
    }
    doom_probe_complete();
}
#endif
