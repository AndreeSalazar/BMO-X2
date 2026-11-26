# ABI 1 candidate. Inputs follow contracts/ABI.md. RAX/RDX are results.
# RCX and R11 are volatile at the SYSCALL boundary; the caller owns the frame.
.Labi1_dispatch:
    mov %rdx, %rcx
    xor %edx, %edx
    test %r9, %r9
    jnz .Labi1_bad_args
    cmp $1, %rax
    ja .Labi1_bad_gate
    mov %r10, %r11
    or %r8, %r11
    jnz .Labi1_bad_args
    test %rax, %rax
    jnz .Labi1_wait
    cmp $2, %rdi
    je .Labi1_event
    cmp $1, %rdi
    jne .Labi1_bad_cap
    cmp $1, %rsi
    jne .Labi1_bad_op
    mov %rcx, %rdx
.Labi1_ok:
    xor %eax, %eax
    ret
.Labi1_event:
    test %rcx, %rcx
    jnz .Labi1_bad_args
    cmp $2, %rsi
    je .Labi1_clock
    cmp $1, %rsi
    jne .Labi1_bad_op
    incq ABI_EVENT_SEQ
.Labi1_sequence:
    mov ABI_EVENT_SEQ, %rdx
    jmp .Labi1_ok
.Labi1_clock:
    mov ABI_TIME_NS, %rdx
    jmp .Labi1_ok
.Labi1_wait:
    cmp $2, %rdi
    jne .Labi1_bad_cap
    cmp %rsi, ABI_EVENT_SEQ
    jne .Labi1_sequence
    mov %rcx, %rax
    sub ABI_TIME_NS, %rax
    jbe .Labi1_timeout
    cmp $1000000000, %rax
    ja .Labi1_bad_args
.Labi1_sleep:
    sti
    hlt
    cli
    incq ABI_WAIT_WAKES
    cmp %rsi, ABI_EVENT_SEQ
    jne .Labi1_sequence
    cmp %rcx, ABI_TIME_NS
    jb .Labi1_sleep
.Labi1_timeout:
    mov $-6, %rax
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
