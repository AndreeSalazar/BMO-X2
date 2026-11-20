# One read of LBA 8 on the fixed QEMU ICH9 device. Enter from the
# protected storage stage after Ring 0 has validated AMD-Vi domain 3.
.Lahci_guest:
    push %rbx
    push %r13
    push %r15
    movq AMDVI_GUEST_AHCI_STEP(%rbp), %rax
    test %rax, %rax
    je .Lahci_preflight
    cmp $7, %rax
    jne .Lahci_refused              # Retain the reservation on failure.
.Lahci_preflight:
    movq $1, AMDVI_GUEST_AHCI_STEP(%rbp)
    mov $0xcf8, %dx
    in %dx, %eax
    mov %eax, %r11d
    mov $0x80003004, %eax
    call .Lnvme_pci_read
    movzwl %ax, %r15d
    mov $0x80003008, %eax
    call .Lnvme_pci_read
    shr $8, %eax
    mov %eax, %ebx
    mov $0x80003024, %eax
    call .Lnvme_pci_read
    mov %eax, %r8d
    mov %r11d, %eax
    out %eax, %dx
    mov %r15d, %eax
    cmpq $7, AMDVI_LAB_REQUEST(%rbp)
    jne .Lahci_dma_off
    and $~4, %eax
.Lahci_dma_off:
    and $6, %eax
    cmp $2, %eax
    jne .Lahci_refused
    cmp $0x010601, %ebx
    jne .Lahci_refused
    cmp $0x80000000, %r8d
    jb .Lahci_refused
    test $4095, %r8d
    jnz .Lahci_refused
    lea 4096(%r8), %r9
    call .Lmmio_map_range
    jc .Lahci_refused
    mov %r8, %rax
    or $0x1b, %rax
    bts $63, %rax
    mov %rax, LAB_PT(%r12)
    movq $0, (LAB_PT+16)(%r12)
    invlpg (%r14)
    invlpg 0x2000(%r14)

    # This fixture has six ports, a single SATA disk on port zero
    # and no firmware ownership handshake in progress.
    cmpl $0x3f, 0x0c(%r14)
    jne .Lahci_refused
    testl $1, 0x24(%r14)
    jz .Lahci_check_ports
    testl $0x11, 0x28(%r14)
    jnz .Lahci_refused
.Lahci_check_ports:
    lea 0x100(%r14), %r13
    mov 0x28(%r13), %eax
    and $15, %eax
    cmp $3, %eax
    jne .Lahci_refused
    cmpl $0x00000101, 0x24(%r13)
    jne .Lahci_refused
    mov %r13, %rdi
.Lahci_check_idle:
    mov 0x34(%rdi), %eax
    or 0x38(%rdi), %eax
    jnz .Lahci_refused
    add $0x80, %rdi
    lea 0x400(%r14), %rax
    cmp %rax, %rdi
    jb .Lahci_check_idle
    movq $2, AMDVI_GUEST_AHCI_STEP(%rbp)
    mov %r13, %rdi
.Lahci_stop_ports:
    call .Lahci_stop
    jc .Lahci_refused
    add $0x80, %rdi
    lea 0x400(%r14), %rax
    cmp %rax, %rdi
    jb .Lahci_stop_ports
    cmpq $7, AMDVI_LAB_REQUEST(%rbp)
    je .Lahci_firmware_stopped

    movq $3, AMDVI_GUEST_AHCI_STEP(%rbp)
    andl $~2, 4(%r14)
    orl $0x80000000, 4(%r14)
    movl $0, 0x14(%r13)
    movl $-1, 0x10(%r13)
    movl $-1, 0x30(%r13)
    lea LAB_AHCI_BUFFER(%r12), %rbx
    lea LAB_AHCI_IOVA(%r12), %r10
    mov %rbx, %rdi
    xor %eax, %eax
    mov $512, %ecx
    cld
    rep stosq
    movl $0x10005, (%rbx)          # Five FIS dwords, one PRDT entry.
    lea 0x500(%r10), %rax
    mov %rax, 8(%rbx)
    movl $0x00258027, 0x500(%rbx)  # Register H2D, READ DMA EXT.
    movl $0x40000008, 0x504(%rbx)  # LBA 8.
    movl $1, 0x50c(%rbx)          # One 512 B sector.
    lea 0x800(%r10), %rax
    mov %rax, 0x580(%rbx)
    movl $511, 0x58c(%rbx)
    mov %r10d, (%r13)
    movl $0, 4(%r13)
    lea 0x400(%r10), %eax
    mov %eax, 8(%r13)
    movl $0, 12(%r13)
    mov %r15d, %eax
    or $4, %eax
    call .Lahci_pci_command
    jne .Lahci_failed
    movq $4, AMDVI_GUEST_AHCI_STEP(%rbp)
    orl $0x10, 0x18(%r13)
    testl $0x89, 0x20(%r13)
    jnz .Lahci_failed
    orl $1, 0x18(%r13)
    mfence
    movl $1, 0x38(%r13)
    lea 0x38(%r13), %r8
    mov $1, %r9d
    call .Lahci_wait_clear
    jc .Lahci_failed
    movq $5, AMDVI_GUEST_AHCI_STEP(%rbp)
    testl $0x7d800000, 0x10(%r13)
    jnz .Lahci_failed
    testl $0x89, 0x20(%r13)
    jnz .Lahci_failed
    cmpl $512, 4(%rbx)
    jne .Lahci_failed
    movq $6, AMDVI_GUEST_AHCI_STEP(%rbp)
    mov %r13, %rdi
    call .Lahci_stop
    jc .Lahci_failed
    xor %eax, %eax
    mov %rax, (%r13)
    mov %rax, 8(%r13)
    mov %r15d, %eax
    call .Lahci_pci_command
    jne .Lahci_failed
    incq AMDVI_GUEST_AHCI_READS(%rbp)
    movq $7, AMDVI_GUEST_AHCI_STEP(%rbp)
    xor %eax, %eax
    jmp .Lahci_done
.Lahci_firmware_stopped:
    mov %r15d, %eax
    and $~4, %eax
    call .Lahci_pci_command
    jne .Lahci_refused
    movq $1, AMDVI_GUEST_AHCI_HANDOFF(%rbp)
    movq $0, AMDVI_GUEST_AHCI_STEP(%rbp)
    xor %eax, %eax
    jmp .Lahci_done
.Lahci_failed:
    mov %r15d, %eax
    call .Lahci_pci_command
.Lahci_refused:
    mov $4, %eax
.Lahci_done:
    pop %r15
    pop %r13
    pop %rbx
    ret

.Lahci_stop:
    lea 0x18(%rdi), %r8
    andl $~1, (%r8)
    mov $0x8001, %r9d
    call .Lahci_wait_clear
    jc .Lahci_stop_done
    andl $~0x10, (%r8)
    mov $0x4010, %r9d
    call .Lahci_wait_clear
.Lahci_stop_done:
    ret

.Lahci_wait_clear:
    mov $0x100000, %ecx
.Lahci_poll:
    test %r9d, (%r8)
    jz .Lahci_poll_ok
    pause
    loop .Lahci_poll
    stc
    ret
.Lahci_poll_ok:
    clc
    ret

.Lahci_pci_command:
    mov $0x80003004, %r10d
    jmp .Lstorage_pci_command
