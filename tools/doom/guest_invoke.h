#ifndef BMO_DOOM_GUEST_INVOKE_H
#define BMO_DOOM_GUEST_INVOKE_H

/* Scalar return convention of the experimental QEMU session gate. */
static inline unsigned long doom_invoke(unsigned long cap, unsigned long op,
                                        unsigned long arg0, unsigned long arg1) {
    register unsigned long r10 __asm__("r10") = arg1;
    unsigned long result = 0;
    __asm__ volatile("syscall" : "+a"(result), "+D"(cap), "+S"(op),
                     "+d"(arg0), "+r"(r10) :: "rcx", "r11", "r8", "r9", "memory");
    return result;
}

#endif
