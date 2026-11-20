# QEMU TCG lab only. R12 is the captured row and R13 is its validated
# scratch alias. Retain the firmware DMA buffers after either outcome.
storage_quiesce:
    cmpq $4, AMDVI_POST_STATUS(%rbp)
    jne .Lquiesce_done
    # The emulator's register base is above the positive imm32 range.
    mov $0xfed80000, %eax
    cmp %rax, AMDVI_POST_BASE(%rbp)
    jne .Lquiesce_done
    testb $1, AMDVI_POST_REGISTERS(%rbp)
    jnz .Lquiesce_done
    cmpw $2, STORAGE_STATUS(%r12)
    jne .Lquiesce_done
    mov STORAGE_ID(%r12), %eax
    cmp $0x29228086, %eax
    je .Lquiesce_check_emulator
    cmp $0x00101b36, %eax
    jne .Lquiesce_done
.Lquiesce_check_emulator:
    push %rbx
    mov $0x40000000, %eax
    cpuid
    cmp $0x54474354, %ebx
    pop %rbx
    jne .Lquiesce_done
    cmp $0x43544743, %ecx
    jne .Lquiesce_done
    cmp $0x47435447, %edx
    jne .Lquiesce_done

    # R11 points to the result for this row. R15 counts down from stored.
    mov STORAGE_HEADER(%rbp), %r11d
    sub %r15d, %r11d
    imul $STORAGE_QUIESCE_ROW_BYTES, %r11d
    lea STORAGE_QUIESCE_ROWS(%rbp,%r11), %r11
    movw $1, QUIESCE_STATUS(%r11)
    mov STORAGE_COMMAND_POST(%r12), %ax
    mov %ax, QUIESCE_PCI_AFTER(%r11)
    cmpl $0x010601, STORAGE_CLASS(%r12)
    jne .Lquiesce_nvme_preflight

    cmpl $0x29228086, STORAGE_ID(%r12)
    jne .Lquiesce_done
    cmpq $0x2c, STORAGE_BAR_BYTES(%r12)
    jb .Lquiesce_done
    testl $0x80000000, STORAGE_GLOBAL0(%r12)
    jz .Lquiesce_done
    cmpl $0, STORAGE_PENDING(%r12)
    jne .Lquiesce_done
    # Keep firmware ownership when BIOS-owned or BIOS busy is asserted.
    testl $1, 0x24(%r13)
    jz .Lquiesce_ahci
    testl $0x11, 0x28(%r13)
    jnz .Lquiesce_done
.Lquiesce_ahci:
    call .Lquiesce_writable
    mov STORAGE_GLOBAL1(%r12), %esi
    lea 0x118(%r13), %rdi       # PxCMD for port 0
.Lquiesce_ports:
    shr %esi
    jnc .Lquiesce_next_port
    mov 0x1c(%rdi), %eax        # PxSACT
    or 0x20(%rdi), %eax         # PxCI
    jnz .Lquiesce_done
    andl $~1, (%rdi)            # Stop the command engine before FIS.
    mov $0x8001, %r8d
    xor %r9d, %r9d
    call .Lquiesce_wait
    jc .Lquiesce_done
    andl $~0x10, (%rdi)
    mov $0x4010, %r8d
    call .Lquiesce_wait
    jc .Lquiesce_done
.Lquiesce_next_port:
    add $0x80, %rdi
    test %esi, %esi
    jnz .Lquiesce_ports
    jmp .Lquiesce_revoke_bme

.Lquiesce_nvme_preflight:
    cmpl $0x010802, STORAGE_CLASS(%r12)
    jne .Lquiesce_done
    cmpl $0x00101b36, STORAGE_ID(%r12)
    jne .Lquiesce_done
    mov STORAGE_GLOBAL0(%r12), %eax
    and $0xc001, %eax
    cmp $1, %eax
    jne .Lquiesce_done
    mov STORAGE_GLOBAL1(%r12), %eax
    and $0x4f, %eax
    cmp $1, %eax
    jne .Lquiesce_done
    call .Lquiesce_writable
    orl $0x4000, 0x14(%r13)     # CC.SHN: normal shutdown
    lea 0x1c(%r13), %rdi
    mov $0x4e, %r8d
    mov $8, %r9d                # SHST complete, ST and CFS clear
    call .Lquiesce_wait
    jc .Lquiesce_done
    mov %eax, QUIESCE_ACK(%r11)
    andl $~0xc001, 0x14(%r13)
    mov $0x43, %r8d
    xor %r9d, %r9d
    call .Lquiesce_wait
    jc .Lquiesce_done
    mov %eax, QUIESCE_FINAL1(%r11)
    mov 0x14(%r13), %eax
    mov %eax, QUIESCE_FINAL0(%r11)
    test $0xc001, %eax
    jnz .Lquiesce_done

.Lquiesce_revoke_bme:
    # Write only PCI Command, without acknowledging RW1C PCI Status bits.
    mov $0xcf8, %dx
    in %dx, %eax
    mov %eax, %esi
    movzwl STORAGE_BDF(%r12), %eax
    shl $8, %eax
    or $0x80000004, %eax
    out %eax, %dx
    add $4, %dx
    in %dx, %ax
    cmp STORAGE_COMMAND_POST(%r12), %ax
    jne .Lquiesce_pci_restore
    and $~4, %ax
    out %ax, %dx
    in %dx, %ax
    mov %ax, QUIESCE_PCI_AFTER(%r11)
    test $4, %al
    jnz .Lquiesce_pci_restore
    movw $3, QUIESCE_STATUS(%r11)
.Lquiesce_pci_restore:
    sub $4, %dx
    mov %esi, %eax
    out %eax, %dx
.Lquiesce_done:
    ret

.Lquiesce_writable:
    movw $2, QUIESCE_STATUS(%r11)
    xor %ecx, %ecx
.Lquiesce_leaf:
    testb $1, 0x1e000(%rbp,%rcx,8)
    jz .Lquiesce_ready
    orb $2, 0x1e000(%rbp,%rcx,8)
    mov %ecx, %eax
    shl $12, %eax
    invlpg (%rbx,%rax)
    inc %ecx
    cmp $3, %ecx
    jb .Lquiesce_leaf
.Lquiesce_ready:
    ret

# Bound emulation polls. A timed out controller keeps its firmware buffers
# and PCI command. This iteration budget is not a metal time source.
.Lquiesce_wait:
    mov $0x100000, %ecx
.Lquiesce_poll:
    mov (%rdi), %eax
    cmp $-1, %eax
    je .Lquiesce_timeout
    mov %eax, %edx
    and %r8d, %edx
    cmp %r9d, %edx
    je .Lquiesce_ok
    pause
    dec %ecx
    jnz .Lquiesce_poll
.Lquiesce_timeout:
    stc
    ret
.Lquiesce_ok:
    clc
    ret
