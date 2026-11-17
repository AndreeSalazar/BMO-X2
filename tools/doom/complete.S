#ifdef BMO_ABI_REUSE
.section .abi_complete,"ax",@progbits
#else
.text
#endif
.globl doom_probe_complete
#ifndef _WIN32
.type doom_probe_complete,@function
#endif
doom_probe_complete:
    # The ABI probe records the hardware frame and scrubs both user pages.
    mov $0x40002000, %esp
    movabs $0x2133524553554d42, %rax
    push %rax
    mov $0x100000, %ebx
    mov (%rbx), %ecx
    ud2
#ifndef _WIN32
.size doom_probe_complete, .-doom_probe_complete
.section .note.GNU-stack,"",@progbits
#endif
