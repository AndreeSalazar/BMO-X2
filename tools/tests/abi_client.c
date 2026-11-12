#include "../../userspace/runtime/abi/bmo_abi.h"

_Static_assert(sizeof(bmo_word) == 8, "BMO word size");
_Static_assert(sizeof(bmo_result) == 16, "BMO result size");

static volatile bmo_word result;

void bmo_main(void) {
    bmo_result echo = bmo_invoke(1, BMO_OP_ECHO, 0x324f4d42, 0, 0);
    bmo_result wait = bmo_wait(1, 0, 0);
    result = echo.status == BMO_OK && wait.status == BMO_NOT_READY ? echo.value : 0;
    for (;;) {}
}
