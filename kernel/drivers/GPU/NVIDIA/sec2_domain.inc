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
    push %r8
    push %r9
    push %r10
    mov GSP_STAGE_BASE(%rbp), %rcx
    mov %r9, %rdx
    mov %r10, %r8
    call .Lsec2_check_fwsec_pages
    pop %r10
    pop %r9
    pop %r8
    test %eax, %eax
    jz .Lsec2_domain_bad
    add $8, %r10
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
    # The last reservation page belongs to the monitor, after the CPU-only trace.
    # Install its leaf before switching the RTX requester to the broader root.
    push %r8
    mov GSP_NATIVE_QUEUE_BASE(%rbp), %rcx
    lea GSP_RM_STATE_OFFSET(%r9), %rdx
    lea ((GSP_RM_STATE_IOVA-SEC2_WPR_IOVA)/4096*8-8)(%r10), %r8
    call .Lgsp_install_state_monitor
    pop %r8
    test %eax, %eax
    jz .Lsec2_domain_bad
    mov $SEC2_IOMMU_ALIAS, %ecx
    lea GSP_SEC2_WORKSPACE_OFFSET(%r9), %rax
    movabs $0x2000000000000001, %rdx
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

# Win64: RCX = RMARGS, RDX = reserved zeroed page, R8 = detached leaf slot.
.globl nvidia_gsp_install_state_monitor
nvidia_gsp_install_state_monitor:
.Lgsp_install_state_monitor:
    xor %eax, %eax
    cmpq $0, (%r8)
    jne .Lgsp_rm_state_done
    cmpq $0, 136(%rcx)
    jne .Lgsp_rm_state_done
    cmpq $0, 144(%rcx)
    jne .Lgsp_rm_state_done
    movabs $0x6000000000000001, %rax
    or %rdx, %rax
    mov %rax, (%r8)
    movq $GSP_RM_STATE_IOVA, 136(%rcx)
    movq $4096, 144(%rcx)
    mov $1, %eax
.Lgsp_rm_state_done:
    ret

# Win64: RCX = start of the low firmware reservation, RDX = DTE base,
# R8 = checked broad WPR entry. Both roots must agree on the FWSEC pages.
.globl nvidia_sec2_check_fwsec_pages
nvidia_sec2_check_fwsec_pages:
.Lsec2_check_fwsec_pages:
    lea 0x208000(%rdx), %r9
    movabs $0x2000000000000201, %rax
    or %r9, %rax
    cmp %rax, (0x207000+(SEC2_WPR_IOVA>>21)*8)(%rdx)
    jne .Lsec2_pages_bad
    lea ((((SEC2_WPR_IOVA+4096)>>12)&511)*8)(%r9), %r9
    movabs $0x000ffffffffff000, %rax
    and (%r9), %rax
    sub $4096, %rax              # WPR immediately precedes the FWSEC image.
    cmp %rcx, %rax
    jb .Lsec2_pages_bad
    lea -0x10000(%rdx), %r11
    cmp %r11, %rax
    ja .Lsec2_pages_bad
    movabs $0x6000000000000001, %r11
    or %rax, %r11
    cmp %r11, (%r8)
    jne .Lsec2_pages_bad
    movabs $0x2000000000000001, %r11
    lea 4096(%rax), %r10
    or %r11, %r10
    xor %ecx, %ecx
.Lsec2_verify_leaves:
    cmp %r10, (%r9,%rcx,8)
    jne .Lsec2_pages_bad
    cmp %r10, 8(%r8,%rcx,8)
    jne .Lsec2_pages_bad
    add $4096, %r10
    inc %ecx
    cmp $15, %ecx
    jb .Lsec2_verify_leaves
    mov $1, %eax
    ret
.Lsec2_pages_bad:
    xor %eax, %eax
    ret
