# GA106 FWSEC-FRTS V3. Win64 ABI, supervisor only.
# RCX: validated writable BAR0 alias; RDX: invariant TSC ticks per 10 ms.
# R8: read-only IOVA for the verified 15-page FWSEC allocation.
# R9: private zeroed result {phase, transferred, mailbox0, mailbox1,
#                           scratch, wpr2_low, wpr2_high}, all u32.
# The caller owns the cold GPU, has reset and selected the GSP Falcon
# core, and has already granted bounded AMD-Vi DMA to this requester.
# It must close PCI BME and drain/reset on failure before releasing RAM.
# Return 0 rejected, 1 FRTS completed and WPR2 present, 2 DMA failed,
# 3 Falcon or WPR2 failed. A started attempt cannot reuse its receipt.
.text
.set GSP_FALCON, 0x110000
.set FWSEC_IMEM_BYTES, 57856
.set FWSEC_DMEM_BYTES, 2048
.set FWSEC_SIGNATURE_OFFSET, 1444
.set WPR2_LOW, 0x1fa824
.set WPR2_HIGH, 0x1fa828

# RCX = exclusive GA106 BAR0 alias. RDX = calibrated TSC ticks per 10 ms.
# Call before granting GPU bus mastering, with cold firmware and GOP retained.
# Return 1 ready for FWSEC, 0 rejected before writes, 2 state uncertain.
# Uses the GA102 Falcon select/reset/scrub sequence from Nouveau.
.globl nvidia_prepare_ga106_falcon
nvidia_prepare_ga106_falcon:
    test %rcx, %rcx
    jz .Lreject
    cmp $1000000, %rdx
    jb .Lreject
    cmp $100000000, %rdx
    ja .Lreject
    cmpl $0xb76000a1, (%rcx)
    jne .Lreject
    cmpl $0x10, 0x111388(%rcx)
    jne .Lreject
    cmpl $16, WPR2_HIGH(%rcx)
    jae .Lreject
    push %r13
    push %r15
    mov %rdx, %r11
    lea GSP_FALCON(%rcx), %r13
    mov 0x3c0(%r13), %eax
    call .Lvalid_read
    jc .Lprep_reject
    test $1, %eax
    jnz .Lprep_reject
    mov 0x1668(%r13), %eax
    call .Lvalid_read
    jc .Lprep_reject
    test $0x10, %eax
    jz .Lprep_reset
    movl $0, 0x1668(%r13)
    mov %r11, %r10
    call .Lprep_deadline
.Lwait_falcon_select:
    mov 0x1668(%r13), %eax
    call .Lvalid_read
    jc .Lprep_uncertain
    and $0x11, %eax
    cmp $1, %eax
    je .Lprep_reset
    call .Lwithin_deadline
    jb .Lwait_falcon_select
    jmp .Lprep_uncertain
.Lprep_reset:
    mov 0x48(%r13), %eax
    call .Lvalid_read
    jc .Lprep_uncertain
    and $-4, %eax
    mov %eax, 0x48(%r13)
    movl $-1, 0x14(%r13)
    mov 0x3c0(%r13), %eax
    call .Lvalid_read
    jc .Lprep_uncertain
    or $1, %eax
    mov %eax, 0x3c0(%r13)
    mov 0x3c0(%r13), %eax        # Drain posted assertion before timing it.
    call .Lvalid_read
    jc .Lprep_uncertain
    test $1, %eax
    jz .Lprep_uncertain
    mov %r11, %rax
    xor %edx, %edx
    mov $1000, %r10d
    div %r10                      # At least 10 us of reset assertion.
    lea 1(%rax), %r10
    call .Lprep_deadline
.Lhold_reset:
    call .Lwithin_deadline
    jb .Lhold_reset
    mov 0x3c0(%r13), %eax
    call .Lvalid_read
    jc .Lprep_uncertain
    and $-2, %eax
    mov %eax, 0x3c0(%r13)
    mov 0x40(%r13), %eax         # Drain posted deassertion.
    call .Lvalid_read
    jc .Lprep_uncertain
    lea (%r11,%r11), %r10
    call .Lprep_deadline
.Lwait_falcon_scrub:
    mov 0xf4(%r13), %eax
    call .Lvalid_read
    jc .Lprep_uncertain
    and $0x80001000, %eax
    cmp $0x80000000, %eax
    je .Lprep_ready
    call .Lwithin_deadline
    jb .Lwait_falcon_scrub
    jmp .Lprep_uncertain
.Lprep_ready:
    cmpl $0x10, 0x111388(%rcx)
    jne .Lprep_uncertain
    mov 0x1668(%r13), %eax
    call .Lvalid_read
    jc .Lprep_uncertain
    test $0x10, %eax
    jnz .Lprep_uncertain
    movl $0xb76000a1, 0x84(%r13)
    mov $1, %eax
    jmp .Lprep_done
.Lprep_reject:
    xor %eax, %eax
    jmp .Lprep_done
.Lprep_uncertain:
    mov $2, %eax
.Lprep_done:
    pop %r15
    pop %r13
    ret
.Lprep_deadline:
    lfence
    rdtsc
    shl $32, %rdx
    or %rdx, %rax
    lea (%rax,%r10), %r15
    ret

.globl nvidia_launch_ga106_fwsec
nvidia_launch_ga106_fwsec:
    test %rcx, %rcx
    jz .Lreject
    test %r9, %r9
    jz .Lreject
    cmpl $0, (%r9)
    jne .Lreject
    cmp $1000000, %rdx
    jb .Lreject
    cmp $100000000, %rdx
    ja .Lreject
    cmp $0x0a107000, %r8
    jne .Lreject
    cmpl $0xb76000a1, (%rcx)          # PMC_BOOT_0, the measured GA106.
    jne .Lreject
    cmpl $0x10, 0x111388(%rcx)       # RISC-V must still be halted.
    jne .Lreject
    cmpl $16, WPR2_HIGH(%rcx)
    jae .Lreject
    lea GSP_FALCON(%rcx), %r10
    mov 0xf4(%r10), %eax
    call .Lvalid_read
    jc .Lreject
    and $0x80001000, %eax
    cmp $0x80000000, %eax           # Ready, with memory scrubbing complete.
    jne .Lreject
    mov 0x108(%r10), %eax
    call .Lvalid_read
    jc .Lreject
    mov %eax, %r11d
    and $0x1ff, %eax
    cmp $(FWSEC_IMEM_BYTES/256), %eax
    jb .Lreject
    and $0x3fe00, %r11d
    cmp $(FWSEC_DMEM_BYTES*2), %r11d
    jb .Lreject
    mov 0x1668(%r10), %eax
    call .Lvalid_read
    jc .Lreject
    test $0x10, %eax               # STARTCPU must target Falcon, not RISC-V.
    jnz .Lreject
    mov 0x624(%r10), %eax
    call .Lvalid_read
    jc .Lreject
    mov 0x600(%r10), %eax
    call .Lvalid_read
    jc .Lreject

    push %rbx
    push %r12
    push %r13
    push %r14
    push %r15
    mov %rcx, %r12
    mov %r10, %r13
    mov %r9, %r14
    imul $200, %rdx, %r11           # One 2-second budget for the attempt.
    lfence
    rdtsc
    shl $32, %rdx
    or %rdx, %rax
    lea (%rax,%r11), %r15

    movl $1, (%r14)
    xor %ebx, %ebx
    call .Lwait_dma_slot
    jc .Ldma_failed
    orl $0x80, 0x624(%r13)          # FBIF physical, no Falcon VM context.
    movl $0, 0x10c(%r13)
    mov 0x600(%r13), %eax
    and $0xfffefff8, %eax
    or $5, %eax                    # Coherent system memory via AMD-Vi.
    mov %eax, 0x600(%r13)
    shr $8, %r8d
    mov %r8d, 0x110(%r13)
    movl $0, 0x128(%r13)
.Limem:
    mov $0x614, %r10d              # 256 B, secure IMEM.
    mov %ebx, %r11d               # Same source tag and destination.
    call .Ltransfer
    jc .Ldma_failed
    cmp $FWSEC_IMEM_BYTES, %ebx
    jb .Limem

    movl $2, (%r14)
    lea (FWSEC_IMEM_BYTES/256)(%r8), %eax
    mov %eax, 0x110(%r13)         # DMEM source base is the end of IMEM.
.Ldmem:
    mov $0x604, %r10d              # 256 B, secure DMEM for GA106 FWSEC.
    lea -FWSEC_IMEM_BYTES(%rbx), %r11d
    call .Ltransfer
    jc .Ldma_failed
    cmp $(FWSEC_IMEM_BYTES+FWSEC_DMEM_BYTES), %ebx
    jb .Ldmem

    call .Lwithin_deadline
    jae .Ldma_failed
    mov 0x100(%r13), %eax
    call .Lvalid_read
    jc .Lfirmware_failed
    mov %eax, %r11d
    movl $3, (%r14)
    movl $FWSEC_SIGNATURE_OFFSET, 0x1210(%r13)
    movl $0x400, 0x119c(%r13)      # GSP engine mask.
    movl $9, 0x1198(%r13)          # VBIOS FWSEC ucode ID.
    movl $1, 0x1180(%r13)          # BROM selects RSA-3072 verification.
    movl $0, 0x40(%r13)
    movl $0, 0x104(%r13)
    test $0x40, %r11d
    jnz .Lstart_alias
    movl $2, 0x100(%r13)           # STARTCPU: execute FWSEC-FRTS.
    jmp .Lwait_halt
.Lstart_alias:
    movl $2, 0x130(%r13)
.Lwait_halt:
    mov 0x100(%r13), %eax
    call .Lvalid_read
    jc .Lfirmware_failed
    test $0x10, %eax
    jnz .Lread_reply
    call .Lwithin_deadline
    jb .Lwait_halt
    jmp .Lfirmware_failed
.Lread_reply:
    call .Lrecord_reply
    cmpl $0, 8(%r14)
    jne .Lreply_failed
    cmpl $0x10000, 16(%r14)        # FRTS result is the high half of SCRATCH14.
    jae .Lreply_failed
    # Same 896 KiB window as the cold GA106 FRTS, excluding permission bits.
    mov 20(%r14), %eax
    and $-16, %eax
    cmp $0x02ffe000, %eax
    jne .Lreply_failed
    mov 24(%r14), %edx
    and $-16, %edx
    cmp $0x02ffee00, %edx
    jne .Lreply_failed
    movl $4, (%r14)
    mov $1, %eax
    jmp .Lreturn
.Ldma_failed:
    mov $2, %eax
    jmp .Lreturn
.Lfirmware_failed:
    call .Lrecord_reply
.Lreply_failed:
    mov $3, %eax
.Lreturn:
    pop %r15
    pop %r14
    pop %r13
    pop %r12
    pop %rbx
    ret
.Lreject:
    xor %eax, %eax
    ret

.Ltransfer:
    call .Lwait_dma_slot
    jc .Ltransfer_end
    mov %r11d, 0x114(%r13)
    mov %r11d, 0x11c(%r13)
    mov %r10d, 0x118(%r13)
.Lwait_dma_idle:
    mov 0x118(%r13), %eax
    call .Lvalid_read
    jc .Ltransfer_end
    test $2, %eax
    jnz .Ltransfer_done
    call .Lwithin_deadline
    jb .Lwait_dma_idle
    stc
.Ltransfer_end:
    ret
.Ltransfer_done:
    add $256, %ebx
    mov %ebx, 4(%r14)
    clc
    ret
.Lwait_dma_slot:
    call .Lwithin_deadline
    jae .Lslot_timeout
    mov 0x118(%r13), %eax
    call .Lvalid_read
    jc .Lslot_end
    test $1, %eax
    jz .Lslot_end                  # TEST already cleared carry.
    jmp .Lwait_dma_slot
.Lslot_timeout:
    stc
.Lslot_end:
    ret
.Lvalid_read:
    cmp $-1, %eax
    je .Linvalid_read
    cmp $0xbad00000, %eax
    jb .Lgood_read
    cmp $0xbae00000, %eax
    jb .Linvalid_read
.Lgood_read:
    clc
    ret
.Linvalid_read:
    stc
    ret
.Lwithin_deadline:
    pause
    lfence
    rdtsc
    shl $32, %rdx
    or %rdx, %rax
    cmp %r15, %rax
    ret
.Lrecord_reply:
    mov 0x40(%r13), %eax
    mov %eax, 8(%r14)
    mov 0x44(%r13), %eax
    mov %eax, 12(%r14)
    mov 0x1438(%r12), %eax
    mov %eax, 16(%r14)
    mov WPR2_LOW(%r12), %eax
    mov %eax, 20(%r14)
    mov WPR2_HIGH(%r12), %eax
    mov %eax, 24(%r14)
    ret
