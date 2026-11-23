# AMD-Vi private startup transaction. Win64 ABI.
# RCX: writable supervisor IOMMU alias. RDX: writable WB alias of the
# staged 4 KiB command page. R8: calibrated TSC budget in ticks.
# R9: {disabled Control, encoded DTE base, encoded command base,
#      encoded event base, INVALIDATE_DEVTAB_ENTRY low qword, invalidate-all flag}.
# The caller owns the IOMMU, has exclusively staged the matching bases
# and quiesced the devices. This routine never changes PCI Command.
# Returns 0 rejected, 1 active, 2 failed with translation stopped,
# 3 failed with state uncertain (all allocations must stay pinned).
# After stop, the caller owns the event bytes and any pending W1C status.
.text
.set AMDVI_RUN_FLAGS, 0x1005
.set AMDVI_CMD_HEAD, 0x2000
.set AMDVI_CMD_TAIL, 0x2008
.set AMDVI_EVT_HEAD, 0x2010
.set AMDVI_EVT_TAIL, 0x2018
.set AMDVI_STATUS, 0x2020
.set AMDVI_COMPLETION_SLOT, 0xff8
.globl amdvi_start_translation
amdvi_start_translation:
.Lstart_translation:
    test %rdx, %rdx
    jz .Ltranslation_reject
    test $0xfff, %edx
    jnz .Ltranslation_reject
    call .Ltranslation_match
    jc .Ltranslation_reject
    mov (%r9), %rax
    cmp %rax, 0x18(%rcx)
    jne .Ltranslation_reject
    cmpq $0, AMDVI_STATUS(%rcx)
    jne .Ltranslation_reject
    testq $1, 0x20(%rcx)            # Refuse an enabled exclusion window.
    jnz .Ltranslation_reject
    mov AMDVI_CMD_HEAD(%rcx), %rax
    or AMDVI_CMD_TAIL(%rcx), %rax
    or AMDVI_EVT_HEAD(%rcx), %rax
    or AMDVI_EVT_TAIL(%rcx), %rax
    jne .Ltranslation_reject
    mov 16(%r9), %r10
    mov %r10, %rax
    shr $52, %rax
    cmp $0x80, %eax                # One 4 KiB command page, no reserved bits.
    jne .Ltranslation_reject
    mov 32(%r9), %rax
    shr $16, %rax
    movabs $(2 << 44), %r11
    cmp %r11, %rax                  # INVALIDATE_DEVTAB_ENTRY, one DeviceID.
    jne .Ltranslation_reject
    cmpq $1, 40(%r9)
    ja .Ltranslation_reject
    jb .Ltranslation_publish
    mov 0x30(%rcx), %rax
    cmp $-1, %rax
    je .Ltranslation_reject
    test $64, %al                   # EFR.IASup.
    jz .Ltranslation_reject
.Ltranslation_publish:
    movq $0, AMDVI_COMPLETION_SLOT(%rdx)
    mov %rdx, %r11
    cmpq $0, 40(%r9)
    je .Ltranslation_publish_rid
    movabs $0x8000000000000000, %rax
    mov %rax, (%rdx)
    movq $0, 8(%rdx)
    add $16, %rdx
.Ltranslation_publish_rid:
    mov 32(%r9), %rax
    mov %rax, (%rdx)
    movq $0, 8(%rdx)
    # COMPLETION_WAIT writes a fresh token to the last qword of our
    # command page. The ring never advances past that reserved location.
    movabs $0x1000000000000ff9, %rax
    btr $59, %r10                   # Drop the command-page length field.
    or %r10, %rax
    mov %rax, 16(%rdx)
    movq $1, 24(%rdx)
    sub %r11, %rdx
    add $32, %rdx
    sfence
    mov (%r9), %rax
    or $AMDVI_RUN_FLAGS, %rax
    mov %rax, 0x18(%rcx)
    cmp %rax, 0x18(%rcx)
    jne .Ltranslation_rollback
    mov %rdx, AMDVI_CMD_TAIL(%rcx)
    call .Ltranslation_deadline
.Ltranslation_wait:
    cmpq $0, AMDVI_EVT_TAIL(%rcx)
    jne .Ltranslation_rollback
    mov AMDVI_STATUS(%rcx), %rax
    test $3, %al                    # Event overflow or event pending.
    jnz .Ltranslation_rollback
    mov 40(%r9), %rdx
    shl $4, %rdx
    add $32, %rdx
    cmp %rdx, AMDVI_CMD_HEAD(%rcx)
    jne .Ltranslation_wait_next
    cmpq $1, AMDVI_COMPLETION_SLOT(%r11)
    je .Ltranslation_started
.Ltranslation_wait_next:
    call .Ltranslation_before_deadline
    jb .Ltranslation_wait
    jmp .Ltranslation_rollback
.Ltranslation_started:
    mov (%r9), %rax
    or $AMDVI_RUN_FLAGS, %rax
    cmp %rax, 0x18(%rcx)
    jne .Ltranslation_rollback
    mov $1, %eax
    ret
.Ltranslation_rollback:
    call .Lstop_translation
    cmp $1, %eax
    jne .Ltranslation_uncertain
    mov $2, %eax
    ret

# The caller first quiesces all requesters and verifies that unauthorized
# bus mastering is closed. Once stopped, the original bases can be restored.
# RCX, R8 and R9 as above. Returns 1 stopped, 0 rejected, 3 uncertain.
.globl amdvi_stop_translation
amdvi_stop_translation:
.Lstop_translation:
    call .Ltranslation_match
    jc .Ltranslation_reject
    mov (%r9), %rax
    mov 0x18(%rcx), %rdx
    cmp %rax, %rdx
    je .Ltranslation_wait_stop
    or $AMDVI_RUN_FLAGS, %rax
    cmp %rax, %rdx
    jne .Ltranslation_uncertain
    mov (%r9), %rax
    mov %rax, 0x18(%rcx)
.Ltranslation_wait_stop:
    call .Ltranslation_deadline
.Ltranslation_stopping:
    mov (%r9), %rax
    cmp %rax, 0x18(%rcx)
    jne .Ltranslation_stop_next
    testq $0x18, AMDVI_STATUS(%rcx) # EventLogRun and CmdBufRun.
    jz .Ltranslation_reset_queues
.Ltranslation_stop_next:
    call .Ltranslation_before_deadline
    jb .Ltranslation_stopping
    jmp .Ltranslation_uncertain
.Ltranslation_reset_queues:
    movq $0, AMDVI_CMD_TAIL(%rcx)
    movq $0, AMDVI_CMD_HEAD(%rcx)
    movq $0, AMDVI_EVT_HEAD(%rcx)
    movq $0, AMDVI_EVT_TAIL(%rcx)
    mov AMDVI_CMD_HEAD(%rcx), %rax
    or AMDVI_CMD_TAIL(%rcx), %rax
    or AMDVI_EVT_HEAD(%rcx), %rax
    or AMDVI_EVT_TAIL(%rcx), %rax
    jne .Ltranslation_uncertain
    mov $1, %eax
    ret
.Ltranslation_uncertain:
    mov $3, %eax
    ret
.Ltranslation_reject:
    xor %eax, %eax
    ret
.Ltranslation_match:
    test %rcx, %rcx
    jz .Ltranslation_no_match
    test %r9, %r9
    jz .Ltranslation_no_match
    test %r8, %r8
    jz .Ltranslation_no_match
    movabs $1000000000, %rax
    cmp %rax, %r8
    ja .Ltranslation_no_match
    mov (%r9), %rax
    test $0x101d, %eax
    jnz .Ltranslation_no_match
    mov 8(%r9), %rax
    cmp %rax, (%rcx)
    jne .Ltranslation_no_match
    mov 16(%r9), %rax
    cmp %rax, 8(%rcx)
    jne .Ltranslation_no_match
    mov 24(%r9), %rax
    cmp %rax, 16(%rcx)
    jne .Ltranslation_no_match
    clc
    ret
.Ltranslation_no_match:
    stc
    ret
.Ltranslation_deadline:
    lfence
    rdtsc
    shl $32, %rdx
    or %rdx, %rax
    lea (%rax,%r8), %r10
    ret
.Ltranslation_before_deadline:
    pause
    lfence
    rdtsc
    shl $32, %rdx
    or %rdx, %rax
    cmp %r10, %rax
    ret
