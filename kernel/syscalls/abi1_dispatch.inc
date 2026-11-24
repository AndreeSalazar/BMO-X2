# ABI 1 candidate. Inputs follow contracts/ABI.md. RAX/RDX are results.
# RCX and R11 are volatile at the SYSCALL boundary; the caller owns the frame.
.Labi1_dispatch:
    mov %rdx, %rcx
    xor %edx, %edx
    test %r9, %r9
    jnz .Labi1_bad_args
    cmp $1, %rax
    je .Labi1_wait
    test %rax, %rax
    jnz .Labi1_bad_gate
    cmp $1, %rdi
    jne .Labi1_bad_cap
    cmp $1, %rsi
    jne .Labi1_bad_op
    mov %r10, %rax
    or %r8, %rax
    jnz .Labi1_bad_args
    mov %rcx, %rdx
    xor %eax, %eax
    ret
.Labi1_wait:
    mov %r10, %rax
    or %r8, %rax
    jnz .Labi1_bad_args
    mov $-4, %rax
    ret
.Labi1_bad_gate:
    mov $-1, %rax
    ret
.Labi1_bad_cap:
    mov $-2, %rax
    ret
.Labi1_bad_args:
    mov $-3, %rax
    ret
.Labi1_bad_op:
    mov $-5, %rax
    ret
