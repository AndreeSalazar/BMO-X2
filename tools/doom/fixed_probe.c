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
#elif defined(BMO_EXTERNAL)
/* The experimental session gate returns its scalar in RAX. */
static unsigned long invoke(unsigned long cap, unsigned long op,
                            unsigned long rect, unsigned long color) {
    register unsigned long arg1 __asm__("r10") = color;
    unsigned long status = 0;
    __asm__ volatile("syscall" : "+a"(status), "+D"(cap), "+S"(op),
                     "+d"(rect), "+r"(arg1) :: "rcx", "r11", "r8", "r9", "memory");
    return status;
}

static const volatile fixed_t operands[] __attribute__((section(".rodata.doom"))) = {
    FRACUNIT + FRACUNIT / 2, FRACUNIT * 2
};
static volatile fixed_t seed = FRACUNIT * 3;
static volatile fixed_t result;

#ifdef BMO_WAD
static unsigned long read_wad(unsigned long offset) {
    return invoke(4, 4, offset, 0);
}

static int find_e1m1(void) {
    if (invoke(1, 4, 0, 0) != ~0ul || read_wad(~0ul) != ~0ul
        || read_wad(0) != 0x44415749) {
        return 0;
    }
    unsigned long count = read_wad(4);
    unsigned long directory = read_wad(8);
    if (count == 0 || count > 65536 || directory < 12 || directory > 0x1000000) {
        return 0;
    }
    if (read_wad(directory + 16 * count - 4) == ~0ul) {
        return 0;
    }
    for (unsigned long i = 0; i < count; ++i) {
        unsigned long record = directory + 16 * i;
        if (read_wad(record + 8) == 0x314d3145 && read_wad(record + 12) == 0) {
            return 1;
        }
    }
    return 0;
}
#endif

void bmo_main(void) {
    if (doom_fixed_check() || result != 0) {
        __builtin_trap();
    }
    fixed_t product = FixedMul(operands[0], operands[1]);
    if (product != seed || product != FRACUNIT * 3) {
        __builtin_trap();
    }
    seed = product / 3;
    result = product;
#ifdef BMO_WAD
    if (!find_e1m1()) {
        __builtin_trap();
    }
#endif
    const unsigned long rect = 24ul | 32ul << 16 | 96ul << 32 | 40ul << 48;
    if (invoke(2, 1, rect, 0xff0000) != 257
        || invoke(1, 1, rect, 0x6ee7b7) != 0) {
        __builtin_trap();
    }
    for (;;) {
        __asm__ volatile("pause");
    }
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
