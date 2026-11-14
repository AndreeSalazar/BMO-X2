#include "../../userspace/runtime/abi/bmo_abi.h"

#ifdef __cplusplus
extern "C" {
#define BMO_ASSERT static_assert
#define BMO_NORETURN [[noreturn]]
#else
#define BMO_ASSERT _Static_assert
#define BMO_NORETURN _Noreturn
#endif

BMO_ASSERT(sizeof(bmo_word) == 8, "BMO word size");
BMO_ASSERT(sizeof(bmo_result) == 16, "BMO result size");

#ifdef BMO_ABI_QEMU
BMO_NORETURN void doom_probe_complete(void);
#else
static volatile bmo_word result;
#endif

void bmo_main(void) {
#ifdef BMO_ABI_SECOND
    const bmo_word marker = 0x32584d42;
#else
    const bmo_word marker = 0x324f4d42;
#endif
    bmo_result echo = bmo_invoke(1, BMO_OP_ECHO, marker, 0, 0);
    bmo_result wait = bmo_wait(1, 0, 0);
#ifdef BMO_ABI_QEMU
    bmo_result denied = bmo_invoke(0, BMO_OP_ECHO, 0, 0, 0);
    if (echo.status == BMO_OK && echo.value == marker &&
        wait.status == BMO_NOT_READY && wait.value == 0 &&
        denied.status == BMO_BAD_CAP && denied.value == 0) {
        doom_probe_complete();
    }
#else
    result = echo.status == BMO_OK && wait.status == BMO_NOT_READY ? echo.value : 0;
#endif
    for (;;) {}
}

#ifdef __cplusplus
}
#endif
