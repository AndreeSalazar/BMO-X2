# GA106 clock handoff before executing the SEC2 booter.
# RCX = BAR0 alias, RDX = epoch ns, R8 = sample TSC, R9 = ticks per 10 ms.
.globl nvidia_gsp_seed_ptimer
nvidia_gsp_seed_ptimer:
.Lgsp_seed_ptimer:
    test %rdx, %rdx
    jz .Lgsp_ptimer_done
    test %r8, %r8
    jz .Lgsp_ptimer_done
    cmp $1000000, %r9
    jb .Lgsp_ptimer_done
    cmp $100000000, %r9
    ja .Lgsp_ptimer_done
    mov 0x9430(%rcx), %eax      # NV_PTIMER_TIME_PRIV_LEVEL_MASK.
    call .Lvalid_read
    jc .Lgsp_ptimer_done
    test $0x10, %al             # Level 0 write permission.
    jz .Lgsp_ptimer_done
    mov %rdx, %r10
    lfence
    rdtsc
    shl $32, %rdx
    or %rdx, %rax
    sub %r8, %rax
    jb .Lgsp_ptimer_done
    imul $6000, %r9, %r8
    cmp %r8, %rax
    ja .Lgsp_ptimer_done
    mov $10000000, %r8d
    mul %r8
    div %r9
    add %r10, %rax
    mov %rax, %rdx
    shr $32, %rdx
    mov %edx, 0x9410(%rcx)
    mov %eax, 0x9400(%rcx)      # TIME_0 commits both halves.
    mov 0x9410(%rcx), %eax      # Drain posted MMIO writes before SEC2.
.Lgsp_ptimer_done:
    ret
