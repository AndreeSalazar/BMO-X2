# AMD-Vi lab payload for the inherited post-EBS handoff. QEMU TCG only.
.text
#if BMO_DMA_LAB_PAGES != 9
#error "The AMD-Vi lab needs nine contiguous EFI LoaderData pages"
#endif
.set EDU_PCI, 0x80002000
.set EDU_ID, 0x11e81234
.set AMDVI_ID, 0x14191022
.set AMDVI_BASE, 0xfed80000
.set L2, 0x1000
.set L1, 0x2000
.set COMMANDS, 0x3000
.set EVENTS, 0x4000
.set COMPLETION, 0x5000
.set PAYLOAD, 0x6000
.set IOVA, 0x7000
.set OUTSIDE, 0x8000
.set RW, 0x6000000000000000
.set WITNESS, 0xa5a5a5a5a5a5a5a5
.set SAMPLE, 0x3152454646554242
.set EDU_BUFFER, 0x40000

.globl edu_probe
edu_probe:
    cli
    cld
    mov %rdi, %rbp
    mov $0x40000000, %eax
    cpuid
    cmp $0x54474354, %ebx    # TCGTCGTCGTCG
    jne .Lhalt
    cmp $0x43544743, %ecx
    jne .Lhalt
    cmp $0x47435447, %edx
    jne .Lhalt
    lea .Lentry(%rip), %rsi
    call serial
    mov $1, %r13d
    mov %cs, %ax
    test $3, %al
    jne early_fail
    test %rbp, %rbp
    jz early_fail
    movabs $0x2134364c4154454d, %rax # METAL64!
    cmp %rax, 0(%rbp)
    jne early_fail
    cmpl $1, 0x78(%rbp)     # ExitBootServices succeeded.
    jne early_fail
    cmpq $BMO_DMA_LAB_PAGES, 0xc0(%rbp)
    jne early_fail
    mov 0xb8(%rbp), %r12
    cmp $0x100000, %r12
    jb early_fail
    cmp $(0x10000000-BMO_DMA_LAB_PAGES*4096), %r12
    ja early_fail
    test $0xfff, %r12d
    jne early_fail

    mov $0xcf8, %dx
    in %dx, %eax
    mov %eax, %r10d         # Restore config selector on every PCI exit.
    mov $2, %r13d
    mov $EDU_PCI, %eax
    call pci_read
    cmp $EDU_ID, %eax
    jne pci_fail
    mov $0x80000000, %ecx
.Lfind_amdvi:
    mov %ecx, %eax
    call pci_read
    cmp $AMDVI_ID, %eax
    je .Lamdvi_found
    add $0x800, %ecx
    cmp $0x80010000, %ecx
    jne .Lfind_amdvi
    jmp pci_fail
.Lamdvi_found:
    mov $AMDVI_BASE, %r14d
    # Snapshot inherited state in CPL0 before programming any register.
    mov 0x18(%r14), %rax
    or 0x00(%r14), %rax
    or 0x08(%r14), %rax
    or 0x10(%r14), %rax
    or 0x2020(%r14), %rax
    jne pci_fail
    lea .Lidle(%rip), %rsi
    call serial
    mov $(EDU_PCI+0x10), %eax
    call pci_read
    test $7, %eax
    jne pci_fail
    and $-16, %eax
    cmp $0x80000000, %eax
    jb pci_fail
    cmp $0xf0000000, %eax
    jae pci_fail
    test $0xfffff, %eax
    jne pci_fail
    mov %eax, %ebx
    mov $(EDU_PCI+4), %eax
    call pci_read
    movzwl %ax, %r15d
    and $~4, %r15d          # Preserve PCI Command with bus mastering closed.
    mov %r15d, %eax
    or $2, %eax
    call edu_command
    cmpl $0x010000ed, 0(%rbx)
    jne cleanup
    testl $1, 0x98(%rbx)
    jnz cleanup

    mov $3, %r13d
    # Device table entry for EDU only. IOVA is a private witness page.
    movabs $RW, %r8
    lea L2(%r12), %rax
    or %r8, %rax
    or $0x403, %rax         # Mode 2, Translation Valid, Valid.
    mov %rax, (0x20*32)(%r12)
    movq $1, (0x20*32+8)(%r12)
    lea IOVA(%r12), %r9
    mov %r9, %rcx
    shr $21, %rcx
    and $511, %ecx
    lea L1(%r12), %rax
    or %r8, %rax
    or $0x201, %rax         # Next level 1, Present.
    mov %rax, L2(%r12,%rcx,8)
    mov %r9, %rcx
    shr $12, %rcx
    and $511, %ecx
    lea L1(%r12,%rcx,8), %r11
    lea PAYLOAD(%r12), %rax
    or %r8, %rax
    or $1, %rax
    mov %rax, (%r11)

    mov %r12, 0(%r14)
    movabs $(8 << 56), %rcx
    lea COMMANDS(%r12), %rax
    or %rcx, %rax
    mov %rax, 0x08(%r14)
    lea EVENTS(%r12), %rax
    or %rcx, %rax
    mov %rax, 0x10(%r14)
    movq $0x1005, 0x18(%r14)
    # Verify readback of the control, table and queues before EDU can DMA.
    cmp %r12, 0x00(%r14)
    jne cleanup
    cmp %rax, 0x10(%r14)
    jne cleanup
    lea COMMANDS(%r12), %rax
    or %rcx, %rax
    cmp %rax, 0x08(%r14)
    jne cleanup
    mov 0x18(%r14), %eax
    and $0x1005, %eax
    cmp $0x1005, %eax
    jne cleanup
    lea .Lactive(%rip), %rsi
    call serial
    movabs $(2 << 60 | 0x20), %rax
    xor %edx, %edx
    xor %ecx, %ecx
    call publish
    jc cleanup
    mov %r15d, %eax
    or $6, %eax
    call edu_command

    mov $4, %r13d
    movabs $SAMPLE, %rax
    movabs $WITNESS, %rbp
    mov %rax, PAYLOAD(%r12)
    mov %rbp, IOVA(%r12)
    mov %rbp, IOVA+0x100(%r12)
    mov %rbp, OUTSIDE(%r12)
    mov %r9, %rdi
    mov $EDU_BUFFER, %esi
    mov $1, %eax
    call transfer
    jc cleanup
    mov $EDU_BUFFER, %edi
    lea 0x100(%r9), %rsi
    mov $3, %eax
    call transfer
    jc cleanup
    movabs $SAMPLE, %rax
    cmp %rax, PAYLOAD+0x100(%r12)
    jne cleanup
    cmp %rbp, IOVA+0x100(%r12)
    jne cleanup
    cmpq $0, 0x2018(%r14)
    jne cleanup
    lea .Lgrant(%rip), %rsi
    call serial

    mov $5, %r13d
    mov $EDU_BUFFER, %edi
    lea OUTSIDE(%r12), %rsi
    mov $3, %eax
    call transfer
    jc cleanup
    cmp %rbp, OUTSIDE(%r12)
    jne cleanup
    xor %edi, %edi
    lea OUTSIDE(%r12), %rsi
    call events
    jc cleanup
    push %rax               # Verified first event tail.
    lea .Loutside(%rip), %rsi
    call serial

    mov $6, %r13d
    movq $0, (%r11)
#ifndef BMO_DMA_OMIT_INVALIDATION
    movabs $(3 << 60 | 1 << 32), %rax
    mov %r9, %rdx
    mov $32, %ecx
    call publish
    jc cleanup
#endif
    mov %rbp, PAYLOAD(%r12)
    mov $EDU_BUFFER, %edi
    mov %r9, %rsi
    mov $3, %eax
    call transfer
    jc cleanup
    cmp %rbp, PAYLOAD(%r12)
    jne stale_write
    cmp %rbp, IOVA(%r12)
    jne cleanup
    pop %rdi
    mov %r9, %rsi
    call events
    jc cleanup
    lea .Lrevoked(%rip), %rsi
    call serial
    xor %r13d, %r13d
    jmp cleanup

stale_write:
    movabs $SAMPLE, %rax
    cmp %rax, PAYLOAD(%r12)
    jne cleanup
    cmp %rbp, IOVA(%r12)
    jne cleanup
    lea .Lstale(%rip), %rsi
    call serial

cleanup:
    mov %r15d, %eax
    call edu_command
    mov $(EDU_PCI+4), %eax
    call pci_read
    test $4, %eax
    jnz .Lmaster_failed
    movq $0, 0x18(%r14)
    testl $1, 0x18(%r14)
    jnz .Lmaster_failed
    lea .Lclosed(%rip), %rsi
    call serial
    jmp pci_fail
.Lmaster_failed:
    mov $7, %r13d
pci_fail:
    mov $0xcf8, %dx
    mov %r10d, %eax
    out %eax, %dx
early_fail:
    test %r13d, %r13d
    jne .Lprint_error
    lea .Lpass(%rip), %rsi
    call serial
    mov $0x10, %eax
    jmp .Lexit
.Lprint_error:
    lea .Lfail(%rip), %rsi
    call serial
    lea '0'(%r13), %eax
    call serial_char
    lea .Lnewline(%rip), %rsi
    call serial
    lea 0x20(%r13), %eax
.Lexit:
    mov $0xf4, %dx
    out %eax, %dx
.Lhalt:
    hlt
    jmp .Lhalt

pci_read:
    mov $0xcf8, %dx
    out %eax, %dx
    mov $0xcfc, %dx
    in %dx, %eax
    ret
edu_command:
    mov %eax, %r8d
    mov $(EDU_PCI+4), %eax
    mov $0xcf8, %dx
    out %eax, %dx
    mov %r8d, %eax
    mov $0xcfc, %dx
    out %ax, %dx
    ret

# RAX/RDX are command qwords; RCX is initial byte tail (0 or 32).
publish:
    mov %rax, COMMANDS(%r12,%rcx)
    mov %rdx, COMMANDS+8(%r12,%rcx)
    lea COMPLETION(%r12), %rax
    bts $60, %rax            # Completion Wait opcode.
    or $1, %rax             # Store completion to memory.
    mov %rax, COMMANDS+16(%r12,%rcx)
    lea 32(%rcx), %rsi
    mov %rsi, COMMANDS+24(%r12,%rcx)
    sfence
    mov %rsi, 0x2008(%r14)
    mov $1000000, %ecx
.Lwait_command:
    cmp %rsi, COMPLETION(%r12)
    jne .Lnext_command
    cmp %rsi, 0x2000(%r14)
    je .Lcommand_ok
.Lnext_command:
    pause
    loop .Lwait_command
    stc
    ret
.Lcommand_ok:
    clc
    ret

# EDU source RDI, destination RSI, direction/start EAX. Bound the wait by TSC.
transfer:
    mov %rdi, 0x80(%rbx)
    mov %rsi, 0x88(%rbx)
    movq $8, 0x90(%rbx)
    mov %rax, 0x98(%rbx)
    rdtsc
    shl $32, %rdx
    or %rdx, %rax
    movabs $6000000000, %r8
    add %rax, %r8
.Lwait_edu:
    testl $1, 0x98(%rbx)
    jz .Ledu_ok
    pause
    rdtsc
    shl $32, %rdx
    or %rdx, %rax
    cmp %r8, %rax
    jb .Lwait_edu
    stc
    ret
.Ledu_ok:
    clc
    ret

# RDI = previous tail, RSI = requested IOVA. Return new tail, CF on mismatch.
events:
    mov 0x2018(%r14), %rax
    cmp %rdi, %rax
    jbe .Lbad_event
    cmp $4096, %rax
    jae .Lbad_event
    test $15, %al
    jnz .Lbad_event
.Lnext_event:
    mov EVENTS(%r12,%rdi), %rcx
    cmp $0x20, %cx
    jne .Lbad_event
    shr $48, %rcx
    and $0xf002, %ecx
    cmp $0x2002, %ecx
    jne .Lbad_event
    mov EVENTS+8(%r12,%rdi), %rcx
    test %rcx, %rcx          # This QEMU build can report a zero event address.
    jz .Ladvance_event
    sub %rsi, %rcx
    cmp $8, %rcx
    jae .Lbad_event
.Ladvance_event:
    add $16, %rdi
    cmp %rax, %rdi
    jb .Lnext_event
    clc
    ret
.Lbad_event:
    stc
    ret

serial:
    lodsb
    test %al, %al
    jz .Lserial_done
    call serial_char
    jmp serial
.Lserial_done:
    ret
serial_char:
    mov %al, %ah
    mov $0x3fd, %dx
    mov $65536, %ecx
.Lwait_uart:
    in %dx, %al
    test $0x20, %al
    jnz .Luart_ready
    loop .Lwait_uart
    ret
.Luart_ready:
    mov $0x3f8, %dx
    mov %ah, %al
    out %al, %dx
    ret

.Lentry:   .asciz "BMO DMA ENTER\r\n"
.Lidle:    .asciz "BMO AMDVI POST-EBS IDLE\r\n"
.Lactive:  .asciz "BMO AMDVI POST-EBS ACTIVE\r\n"
.Lgrant:   .asciz "BMO DMA GRANT\r\n"
.Loutside: .asciz "BMO DMA OUTSIDE\r\n"
.Lrevoked: .asciz "BMO DMA REVOKED\r\n"
.Lstale:   .asciz "BMO DMA STALE\r\n"
.Lclosed:  .asciz "BMO DMA CLOSED\r\n"
.Lpass:    .asciz "BMO DMA PASS\r\n"
.Lfail:    .asciz "BMO DMA FAIL "
.Lnewline: .asciz "\r\n"
