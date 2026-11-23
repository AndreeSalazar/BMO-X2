# Change only the RTX graphics requester after verified FWSEC DMA drain.
# Caller owns the live AMD-Vi command ring and keeps RTX PCI BME disabled.
# RBP is the supervisor handoff. Return 1 only after translation completion.
.Lpublish_sec2_domain:
    mov GSP_PHYSICAL_DTE_BASE(%rbp), %r9
    movabs $0x2000000000000403, %rax
    lea 0x207000(%r9), %rdx
    or %rdx, %rax
    cmp %rax, (0x2900*32)(%r9)
    jne .Lsec2_domain_bad
    cmpq $5, (0x2900*32+8)(%r9)
    jne .Lsec2_domain_bad
    mov GSP_POST_DMA_ROOT(%rbp), %r8
    test $4095, %r8d
    jnz .Lsec2_domain_bad
    cmp GSP_STAGE_BASE(%rbp), %r8
    jb .Lsec2_domain_bad
    cmp %r9, %r8
    jae .Lsec2_domain_bad
    mov ((SEC2_WPR_IOVA>>21)*8)(%r8), %r10
    movabs $0xfff0000000000fff, %rax
    and %r10, %rax
    movabs $0x6000000000000201, %rdx
    cmp %rdx, %rax
    jne .Lsec2_domain_bad
    movabs $0x000ffffffffff000, %rax
    and %rax, %r10
    cmp GSP_STAGE_BASE(%rbp), %r10
    jb .Lsec2_domain_bad
    cmp %r9, %r10
    jae .Lsec2_domain_bad
    lea (((SEC2_WPR_IOVA>>12)&511)*8)(%r10), %r10
    lea -0x10000(%r9), %rax
    movabs $0x6000000000000001, %rdx
    or %rdx, %rax
    cmp %rax, (%r10)             # Only WPR is writable here.
    jne .Lsec2_domain_bad
    add $8, %r10
    lea -0xf000(%r9), %rax
    movabs $0x2000000000000001, %rdx
    or %rdx, %rax
    xor %ecx, %ecx
.Lsec2_verify_leaves:
    cmp %rax, (%r10,%rcx,8)
    jne .Lsec2_domain_bad
    add $4096, %rax
    inc %ecx
    cmp $15, %ecx
    jb .Lsec2_verify_leaves
    mov $SEC2_IOMMU_ALIAS, %ecx
    movabs $0x0000220000001405, %rax
    cmp %rax, 0x18(%rcx)
    jne .Lsec2_domain_bad
    lea 511(%r9), %rax
    cmp %rax, (%rcx)
    jne .Lsec2_domain_bad
    movabs $0x0800000000000000, %rax
    lea 0x204000(%r9), %r11
    or %r11, %rax
    cmp %rax, 8(%rcx)
    jne .Lsec2_domain_bad
    cmpq $0, 0x2018(%rcx)
    jne .Lsec2_domain_bad
    testq $3, 0x2020(%rcx)
    jnz .Lsec2_domain_bad
    cmpq $48, 0x2000(%rcx)
    jne .Lsec2_domain_bad
    cmpq $48, 0x2008(%rcx)
    jne .Lsec2_domain_bad
    lea GSP_SEC2_WORKSPACE_OFFSET(%r9), %rax
    or %rdx, %rax
    mov $15, %edx
.Lsec2_publish_leaves:
    mov %rax, (%r10)
    add $4096, %rax
    add $8, %r10
    dec %edx
    jnz .Lsec2_publish_leaves
    movabs $0x6000000000000403, %rax
    or %r8, %rax
    mov %rax, (0x2900*32)(%r9)   # Same domain ID; open the detached GSP root.
    movabs $0x2000000000002900, %rax
    mov %rax, 48(%r11)
    movq $0, 56(%r11)
    movabs $0x8000000000000000, %rax
    mov %rax, 64(%r11)
    movq $0, 72(%r11)
    movabs $0x1000000000000ff9, %rax
    or %r11, %rax
    mov %rax, 80(%r11)
    movq $2, 88(%r11)
    sfence
    movq $96, 0x2008(%rcx)
    mov STORAGE_TSC_10MS(%rbp), %r10
    call .Lprep_deadline
.Lsec2_domain_ack:
    cmpq $0, 0x2018(%rcx)
    jne .Lsec2_domain_bad
    testq $3, 0x2020(%rcx)
    jnz .Lsec2_domain_bad
    cmpq $96, 0x2000(%rcx)
    jne .Lsec2_domain_wait
    cmpq $2, 0xff8(%r11)
    je .Lsec2_domain_ready
.Lsec2_domain_wait:
    call .Lwithin_deadline
    jb .Lsec2_domain_ack
.Lsec2_domain_bad:
    xor %eax, %eax
    ret
.Lsec2_domain_ready:
    mov $1, %eax
    ret
