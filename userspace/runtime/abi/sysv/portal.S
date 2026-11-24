.text
.globl bmo_invoke
.type bmo_invoke,@function
bmo_invoke:
.Lbmo_invoke:
    mov %rcx,%r10
    xor %r9d,%r9d
    xor %eax,%eax
    syscall
    ret
.size bmo_invoke, .-bmo_invoke

.globl bmo_wait
.type bmo_wait,@function
bmo_wait:
.Lbmo_wait:
    xor %r10d,%r10d
    xor %r8d,%r8d
    xor %r9d,%r9d
    mov $1,%eax
    syscall
    ret
.size bmo_wait, .-bmo_wait

#ifndef BMO_ABI_PORTAL_ONLY
.section .text.startup,"ax",@progbits
.globl _start
.type _start,@function
_start:
    call bmo_main
    ud2
.size _start, .-_start
#endif
.section .note.GNU-stack,"",@progbits
