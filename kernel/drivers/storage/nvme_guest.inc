# Fixed QEMU NVMe namespace. AMD-Vi lab verified TCG, phase, reservation
# and device table before calling. R12 is scratch, R14 its MMIO alias.
nvme_guest_begin:
    push %rbx
    push %r13
    push %r15
    movl $1, AMDVI_GUEST_NVME_STEP(%rbp)
    call .Lnvme_bar
    jc .Lnvme_refused
    lea 8192(%r8), %r9
    mov $0x80000008, %eax
    cpuid
    movzbl %al, %ecx
    cmp $32, %ecx
    jb .Lnvme_refused
    cmp $52, %ecx
    ja .Lnvme_refused
    mov $1, %eax
    shl %cl, %rax
    cmp %rax, %r9
    ja .Lnvme_refused
    call .Lmmio_map_range
    jc .Lnvme_refused

    # Replace the AMD-Vi scratch aliases with the two NVMe register pages.
    # PTEs remain supervisor, RW, UC and NX under the checked PAT.
    mov %r8, %rax
    or $0x1b, %rax
    bts $63, %rax
    mov %rax, LAB_PT(%r12)
    add $4096, %rax
    mov %rax, (LAB_PT+8)(%r12)
    movq $0, (LAB_PT+16)(%r12)
    invlpg (%r14)
    invlpg 0x1000(%r14)
    invlpg 0x2000(%r14)

    movl $2, AMDVI_GUEST_NVME_STEP(%rbp)
    cmpw $3, (%r14)                 # CAP.MQES for depth 4
    jb .Lnvme_refused
    mov 4(%r14), %eax
    and $0xf002f, %eax             # MPSMIN=0, NVM CSS, DSTRD=0
    cmp $0x20, %eax
    jne .Lnvme_refused
    testl $0xc001, 0x14(%r14)
    jnz .Lnvme_refused
    testl $0x43, 0x1c(%r14)
    jnz .Lnvme_refused

    lea LAB_NVME_BACKING(%r12), %rbx
    lea LAB_NVME_IOVA(%r12), %r13
    mov %rbx, %rdi
    mov $(5*4096/8), %ecx
    xor %eax, %eax
    cld
    rep stosq

    # Admin slots 0 and 1 create I/O CQ1 and SQ1. I/O slot 0 reads
    # LBA 8 from the virtual namespace 1 into the fifth DMA page.
    movl $0x10005, 0x00(%rbx)
    lea 0x3000(%r13), %rax
    mov %rax, 0x18(%rbx)
    movl $0x30001, 0x28(%rbx)
    movl $1, 0x2c(%rbx)
    movl $0x20001, 0x40(%rbx)
    lea 0x2000(%r13), %rax
    mov %rax, 0x58(%rbx)
    movl $0x30001, 0x68(%rbx)
    movl $0x10001, 0x6c(%rbx)
    movl $0x30002, 0x2000(%rbx)
    movl $1, 0x2004(%rbx)
    lea 0x4000(%r13), %rax
    mov %rax, 0x2018(%rbx)
    movl $8, 0x2028(%rbx)

    movl $-1, 0x0c(%r14)
    movl $0x30003, 0x24(%r14)
    mov %r13, 0x28(%r14)
    lea 0x1000(%r13), %rax
    mov %rax, 0x30(%r14)
    mov %r15d, %eax
    or $4, %eax
    call .Lnvme_pci_command
    jne .Lnvme_failed
    movl $0x00460001, 0x14(%r14)
    mov $0x43, %r8d
    mov $1, %r9d
    call .Lnvme_status
    jc .Lnvme_failed

    movl $3, AMDVI_GUEST_NVME_STEP(%rbp)
    mfence
    movl $1, 0x1000(%r14)
    lea 0x1008(%rbx), %r8
    movabs $0x0001000100000001, %r9
    call .Lnvme_completion
    jc .Lnvme_failed
    movl $1, 0x1004(%r14)

    movl $4, AMDVI_GUEST_NVME_STEP(%rbp)
    movl $2, 0x1000(%r14)
    lea 0x1018(%rbx), %r8
    movabs $0x0001000200000002, %r9
    call .Lnvme_completion
    jc .Lnvme_failed
    movl $2, 0x1004(%r14)

    movl $5, AMDVI_GUEST_NVME_STEP(%rbp)
    movl $1, 0x1008(%r14)
    lea 0x3008(%rbx), %r8
    movabs $0x0001000300010001, %r9
    call .Lnvme_completion
    jc .Lnvme_failed
    movl $1, 0x100c(%r14)

    movl $6, AMDVI_GUEST_NVME_STEP(%rbp)
    movl $0x00464001, 0x14(%r14)
    mov $0x4e, %r8d
    mov $8, %r9d
    call .Lnvme_status
    jc .Lnvme_failed
    mov %eax, AMDVI_GUEST_NVME_ACK(%rbp)
    movl $0x00460000, 0x14(%r14)
    mov $0x43, %r8d
    xor %r9d, %r9d
    call .Lnvme_status
    jc .Lnvme_failed
    mov %r15d, %eax
    call .Lnvme_pci_command
    jne .Lnvme_failed
    incl AMDVI_GUEST_NVME_READS(%rbp)
    movl $7, AMDVI_GUEST_NVME_STEP(%rbp)
    xor %eax, %eax
    jmp .Lnvme_done
.Lnvme_failed:
    # Retain the DMA reservation. A failed lab run does not reuse queues.
    mov %r15d, %eax
    call .Lnvme_pci_command
    mov $4, %eax
    jmp .Lnvme_done
.Lnvme_refused:
    mov $4, %eax
.Lnvme_done:
    pop %r15
    pop %r13
    pop %rbx
    ret

.Lnvme_bar:
    mov $0xcf8, %dx
    in %dx, %eax
    mov %eax, %r11d
    mov $0x80004804, %eax
    call .Lnvme_pci_read
    movzwl %ax, %r15d
    and $6, %eax
    cmp $2, %eax
    jne .Lnvme_pci_bad
    mov $0x80004808, %eax
    call .Lnvme_pci_read
    shr $8, %eax
    cmp $0x010802, %eax
    jne .Lnvme_pci_bad
    mov $0x80004810, %eax
    call .Lnvme_pci_read
    mov %eax, %r8d
    and $0xfff, %eax
    cmp $4, %eax
    jne .Lnvme_pci_bad
    and $-4096, %r8d
    mov $0x80004814, %eax
    call .Lnvme_pci_read
    shl $32, %rax
    or %rax, %r8
    mov $0x80000000, %eax
    cmp %rax, %r8
    jb .Lnvme_pci_bad
    mov %r8, %rax
    shr $52, %rax
    jnz .Lnvme_pci_bad
    mov %r11d, %eax
    out %eax, %dx
    clc
    ret
.Lnvme_pci_bad:
    mov %r11d, %eax
    out %eax, %dx
    stc
    ret
.Lnvme_pci_read:
    out %eax, %dx
    add $4, %dx
    in %dx, %eax
    sub $4, %dx
    ret

.Lnvme_pci_command:
    mov %eax, %ecx
    mov $0xcf8, %dx
    in %dx, %eax
    mov %eax, %r11d
    mov $0x80004804, %eax
    out %eax, %dx
    add $4, %dx
    mov %cx, %ax
    out %ax, %dx
    in %dx, %ax
    movzwl %ax, %edi
    sub $4, %dx
    mov %r11d, %eax
    out %eax, %dx
    cmp %ecx, %edi
    ret

# Polling budgets are for the fixed QEMU model. Retain buffers on failure.
.Lnvme_status:
    mov $0x100000, %ecx
.Lnvme_status_poll:
    mov 0x1c(%r14), %eax
    test $2, %eax
    jnz .Lnvme_poll_failed
    mov %eax, %edx
    and %r8d, %edx
    cmp %r9d, %edx
    je .Lnvme_poll_ok
    pause
    loop .Lnvme_status_poll
    jmp .Lnvme_poll_failed

.Lnvme_completion:
    mov $0x100000, %ecx
.Lnvme_cq_poll:
    mov (%r8), %rax
    bt $48, %rax
    jc .Lnvme_cq_present
    pause
    loop .Lnvme_cq_poll
    jmp .Lnvme_poll_failed
.Lnvme_cq_present:
    cmp %r9, %rax
    jne .Lnvme_poll_failed
.Lnvme_poll_ok:
    clc
    ret
.Lnvme_poll_failed:
    stc
    ret

#include "../bus/mmio_range.inc"
nvme_guest_end:
