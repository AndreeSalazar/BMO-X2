.text
.globl doom_probe_complete
.type doom_probe_complete,@function
doom_probe_complete:
    # The ABI probe records the hardware frame and scrubs both user pages.
    mov $0x40002000, %esp
    movabs $0x2133524553554d42, %rax
    push %rax
    mov $0x100000, %ebx
    mov (%rbx), %ecx
    ud2
.size doom_probe_complete, .-doom_probe_complete
.section .note.GNU-stack,"",@progbits
