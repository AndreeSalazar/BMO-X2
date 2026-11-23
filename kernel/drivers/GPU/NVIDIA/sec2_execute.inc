# GA106 signed BOOTER_LOAD. The board opens DMA only between prepare and run.
# Aliases: SEC2 and GSP Falcon windows. The IOVAs refer to the prepared domain.
.set SEC2_BOOTER_IOVA, 0x0a107000
.set SEC2_WPR_IOVA, 0x0a106000
.set SEC2_LIBOS_IOVA, 0x0a082000
.set SEC2_IMEM_BYTES, 35584
.set SEC2_DMEM_BYTES, 25088

# RCX = SEC2, RDX = GSP, R8 = ticks per 10 ms. Return 1 if both are ready.
.Lprepare_sec2_engines:
    push %r12
    push %r13
    push %r15
    mov %rcx, %r12
    mov %rdx, %r13
    mov %r8, %r11
    call .Lsec2_reset_engine
    jc .Lsec2_engines_reject
    movl $0x111, 0x1668(%r13)      # Select GSP RISC-V with Boot ROM fetch.
    mov 0x1668(%r13), %eax
    call .Lvalid_read
    jc .Lsec2_engines_reject
    and $0x111, %eax
    cmp $0x111, %eax
    jne .Lsec2_engines_reject
    movl $SEC2_LIBOS_IOVA, 0x40(%r13)
    movl $0, 0x44(%r13)
    cmpl $SEC2_LIBOS_IOVA, 0x40(%r13)
    jne .Lsec2_engines_reject
    cmpl $0, 0x44(%r13)
    jne .Lsec2_engines_reject
    movl $0, 0xc00(%r13)          # MSGQ v2: initialize CPU producer once.
    cmpl $0, 0xc00(%r13)
    jne .Lsec2_engines_reject
    mov %r12, %r13
    call .Lsec2_reset_engine
    jc .Lsec2_engines_reject
    mov 0x1668(%r13), %eax
    call .Lvalid_read
    jc .Lsec2_engines_reject
    test $0x10, %eax
    jz .Lsec2_engine_selected
    movl $0, 0x1668(%r13)
    mov %r11, %r10
    call .Lprep_deadline
.Lsec2_engine_select:
    mov 0x1668(%r13), %eax
    call .Lvalid_read
    jc .Lsec2_engines_reject
    and $0x11, %eax
    cmp $1, %eax
    je .Lsec2_engine_selected
    call .Lwithin_deadline
    jb .Lsec2_engine_select
    jmp .Lsec2_engines_reject
.Lsec2_engine_selected:
    movl $0xb76000a1, 0x84(%r13)
    mov $1, %eax
    jmp .Lsec2_engines_done
.Lsec2_engines_reject:
    xor %eax, %eax
.Lsec2_engines_done:
    pop %r15
    pop %r13
    pop %r12
    ret

# R13 = Falcon, R11 = ticks per 10 ms. CF clear after reset and scrub.
.Lsec2_reset_engine:
    mov 0x3c0(%r13), %eax
    call .Lvalid_read
    jc .Lsec2_reset_fail
    test $1, %eax
    jnz .Lsec2_reset_fail
    or $1, %eax
    mov %eax, 0x3c0(%r13)
    mov 0x3c0(%r13), %eax
    call .Lvalid_read
    jc .Lsec2_reset_fail
    test $1, %al
    jz .Lsec2_reset_fail
    mov %r11, %rax
    xor %edx, %edx
    mov $1000, %r10d
    div %r10
    lea 1(%rax), %r10
    call .Lprep_deadline
.Lsec2_hold_reset:
    call .Lwithin_deadline
    jb .Lsec2_hold_reset
    mov 0x3c0(%r13), %eax
    call .Lvalid_read
    jc .Lsec2_reset_fail
    and $-2, %eax
    mov %eax, 0x3c0(%r13)
    mov 0x3c0(%r13), %eax
    call .Lvalid_read
    jc .Lsec2_reset_fail
    test $1, %al
    jnz .Lsec2_reset_fail
    lea (%r11,%r11), %r10
    call .Lprep_deadline
.Lsec2_scrub:
    mov 0xf4(%r13), %eax
    call .Lvalid_read
    jc .Lsec2_reset_fail
    test $0x1000, %eax
    jz .Lsec2_reset_ok
    call .Lwithin_deadline
    jb .Lsec2_scrub
.Lsec2_reset_fail:
    stc
.Lsec2_reset_ok:
    ret

# RCX = SEC2, RDX = ticks per 10 ms, R8 = zeroed FWSEC-compatible receipt.
# Return 1 for SEC2 halt with MBOX0=0, 2 DMA failure, 3 other failure.
.globl nvidia_execute_sec2_booter
nvidia_execute_sec2_booter:
.Lexecute_sec2_booter:
    push %rbx
    push %r13
    push %r14
    push %r15
    mov %rcx, %r13
    mov %r8, %r14
    imul $200, %rdx, %r10
    call .Lprep_deadline
    xor %ebx, %ebx
    movl $1, (%r14)
    call .Lwait_dma_slot
    jc .Lsec2_dma_failed
    mov 0x624(%r13), %eax
    call .Lvalid_read
    jc .Lsec2_dma_failed
    or $0x80, %eax
    mov %eax, 0x624(%r13)
    movl $0, 0x10c(%r13)
    mov 0x600(%r13), %eax
    call .Lvalid_read
    jc .Lsec2_dma_failed
    and $0xfffefff8, %eax
    or $5, %eax
    mov %eax, 0x600(%r13)
    movl $(SEC2_BOOTER_IOVA>>8), 0x110(%r13)
    movl $0, 0x128(%r13)
.Lsec2_imem:
    lea 256(%rbx), %r11d
    mov $0x614, %r10d
    call .Lsec2_transfer
    jc .Lsec2_dma_failed
    cmp $SEC2_IMEM_BYTES, %ebx
    jb .Lsec2_imem
    movl $2, (%r14)
    movl $((SEC2_BOOTER_IOVA+256+SEC2_IMEM_BYTES)>>8), 0x110(%r13)
.Lsec2_dmem:
    lea -SEC2_IMEM_BYTES(%rbx), %r11d
    mov $0x600, %r10d
    call .Ltransfer
    jc .Lsec2_dma_failed
    cmp $(SEC2_IMEM_BYTES+SEC2_DMEM_BYTES), %ebx
    jb .Lsec2_dmem
    movl $3, (%r14)
    movl $0x10, 0x1210(%r13)
    movl $1, 0x119c(%r13)
    movl $3, 0x1198(%r13)
    movl $1, 0x1180(%r13)
    movl $SEC2_WPR_IOVA, 0x40(%r13)
    movl $0, 0x44(%r13)
    movl $0x100, 0x104(%r13)
    cmpl $SEC2_WPR_IOVA, 0x40(%r13)
    jne .Lsec2_boot_failed
    cmpl $0, 0x44(%r13)
    jne .Lsec2_boot_failed
    cmpl $0x100, 0x104(%r13)
    jne .Lsec2_boot_failed
    mov 0x100(%r13), %eax
    call .Lvalid_read
    jc .Lsec2_boot_failed
    test $0x40, %al
    jnz .Lsec2_start_alias
    movl $2, 0x100(%r13)
    jmp .Lsec2_wait_halt
.Lsec2_start_alias:
    movl $2, 0x130(%r13)
.Lsec2_wait_halt:
    mov 0x100(%r13), %eax
    call .Lvalid_read
    jc .Lsec2_boot_failed
    test $0x10, %al
    jz .Lsec2_halt_deadline
    # A halted CPU may still expose the argument before STARTCPU takes effect.
    cmpl $SEC2_WPR_IOVA, 0x40(%r13)
    jne .Lsec2_halted
.Lsec2_halt_deadline:
    call .Lwithin_deadline
    jb .Lsec2_wait_halt
    jmp .Lsec2_boot_failed
.Lsec2_halted:
    cmpl $0, 0x40(%r13)
    jne .Lsec2_boot_failed
    movl $4, (%r14)
    mov $1, %eax
    jmp .Lsec2_reply
.Lsec2_boot_failed:
    mov $3, %eax
    jmp .Lsec2_reply
.Lsec2_dma_failed:
    mov $2, %eax
.Lsec2_reply:
    mov 0x40(%r13), %edx
    mov %edx, 8(%r14)
    mov 0x44(%r13), %edx
    mov %edx, 12(%r14)
    pop %r15
    pop %r14
    pop %r13
    pop %rbx
    ret

# SEC2 secure IMEM needs the original source offset for the tag, with local
# IMEM starting at zero. The GSP FWSEC helper uses equal source and destination.
.Lsec2_transfer:
    call .Lwait_dma_slot
    jc .Lsec2_transfer_exit
    mov %ebx, 0x114(%r13)
    mov %r11d, 0x11c(%r13)
    mov %r10d, 0x118(%r13)
    jmp .Lwait_dma_idle
.Lsec2_transfer_exit:
    ret
