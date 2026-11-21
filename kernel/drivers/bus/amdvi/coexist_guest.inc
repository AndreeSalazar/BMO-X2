# QEMU TCG only. The lab mailbox requests a fixed operation.
# Ring 0 owns the IOMMU registers, tables and invalidation commands.
#ifdef BMO_AMDVI_GSP_DMA
#include "../../GPU/NVIDIA/gsp_layout.inc"
#endif
.set LAB_PAGES, AMDVI_LAB_PAGES
.set LAB_RW, 0x6000000000000000
.set LAB_VA, 0x10200000
.set LAB_PT, 0xd000
.set LAB_EDU_IOVA, 0xb000
.set LAB_EDU_PAYLOAD, 0xa000
#ifdef BMO_AMDVI_ROUTED
.set LAB_TABLE_OFFSET, 0x12000
.set LAB_TABLE_LENGTH, AMDVI_LAB_TABLE_PAGES-1
#else
.set LAB_TABLE_OFFSET, 0
.set LAB_TABLE_LENGTH, 1
#endif
#ifdef BMO_AMDVI_STORAGE
#ifdef BMO_AMDVI_NVME
.set LAB_EDU_REVOKE, 128
.set LAB_NVME_ROOT, 0x12000
.set LAB_NVME_LEAF, 0x13000
.set LAB_NVME_BACKING, 0x15000
.set LAB_NVME_IOVA, 0x1a000
#else
.set LAB_EDU_REVOKE, 96
#endif
.set LAB_AHCI_ROOT, 0xe000
.set LAB_AHCI_LEAF, 0xf000
.set LAB_AHCI_BUFFER, 0x10000
.set LAB_AHCI_IOVA, 0x11000
#else
.set LAB_EDU_REVOKE, 64
#endif

amdvi_lab_entry:
    push %rbx
    push %r12
    push %r13
    push %r14
    push %r15
    mov $0x40000000, %eax
    cpuid
    cmp $0x54474354, %ebx
    jne .Llab_reject
    cmp $0x43544743, %ecx
    jne .Llab_reject
    cmp $0x47435447, %edx
    jne .Llab_reject
    cmpq $4, AMDVI_POST_STATUS(%rbp)
    jne .Llab_reject
    mov $0xfed80000, %eax
    cmp %rax, AMDVI_POST_BASE(%rbp)
    jne .Llab_reject
    cmpq $0, 0x15408(%rbp)
    jne .Llab_reject
    cmpb $1, %gs:0x3c4
    jne .Llab_reject
    cmpb $1, %gs:0x3c8
    jne .Llab_reject
    cmpw $0x28, %gs:0x360
    jne .Llab_reject
    mov AMDVI_LAB_SCRATCH(%rbp), %r12
    mov 0xb8(%rbp), %r13
    cmpq $14, 0xc0(%rbp)
    jne .Llab_reject
    cmp $0x100000, %r12
    jb .Llab_reject
    cmp $(0x10000000-LAB_PAGES*4096), %r12
    ja .Llab_reject
    test $4095, %r12d
    jnz .Llab_reject
    lea (LAB_PAGES*4096)(%r12), %rsi
    cmp %rsi, %r13
    jae .Llab_check_reservation
    lea 0xe000(%r13), %rax
    cmp %rax, %r12
    jb .Llab_reject
.Llab_check_reservation:
    mov %r12, %rdi
    call .Llab_loader_data
    jc .Llab_reject
#ifdef BMO_AMDVI_GSP_DMA
    cmpl $3, GSP_POST_STATUS(%rbp)
    jne .Llab_reject
    mov GSP_STAGE_BASE(%rbp), %rdi
    lea (GSP_STAGE_PAGES*4096)(%rdi), %rsi
    lea GSP_DMA_TABLE_OFFSET(%rdi), %rax
    cmp GSP_POST_DMA_ROOT(%rbp), %rax
    jne .Llab_reject
    call .Llab_loader_data
    jc .Llab_reject
#endif
    mov AMDVI_LAB_REQUEST(%rbp), %r15
    cmp $1, %r15
    jb .Llab_reject
#ifdef BMO_AMDVI_GUEST_AHCI
    cmp $7, %r15
#elif defined(BMO_AMDVI_GUEST_NVME)
    cmp $4, %r15
#else
    cmp $3, %r15
#endif
    ja .Llab_reject
    cmp $1, %r15
    je .Llab_initial_phase
#ifdef BMO_AMDVI_GUEST_AHCI
    cmp $6, %r15
    jae .Llab_initial_phase
#endif
    jmp .Llab_running_phase
.Llab_initial_phase:
    cmpq $0, AMDVI_LAB_PHASE(%rbp)
    jne .Llab_reject
    jmp .Llab_check_pci
.Llab_running_phase:
    mov AMDVI_LAB_PHASE(%rbp), %rax
    dec %rax
    cmp $1, %rax
    ja .Llab_reject
    cmp $2, %r15
    jne .Llab_check_pci
    test %rax, %rax
    jne .Llab_reject
.Llab_check_pci:
    call .Llab_pci
    jc .Llab_pci_rejected

    # Use a second page-table slot. The live xHCI alias is in 0x15400.
    testq $1, AMDVI_LAB_PHASE(%rbp)
    jnz .Llab_map
    cmp $1, %r15
    jne .Llab_map
    mov %r12, %rdi
    xor %eax, %eax
    mov $(LAB_PAGES*4096/8), %ecx
    cld
    rep stosq
.Llab_map:
    movabs $0x80000000fed8001b, %rax
    mov %rax, LAB_PT(%r12)
    add $0x2000, %rax
    mov %rax, (LAB_PT+16)(%r12)
    lea (LAB_PT+3)(%r12), %rax
    mov %rax, 0x15408(%rbp)
    mov $LAB_VA, %r14d
    invlpg (%r14)
    invlpg 0x2000(%r14)
    mov $3, %ebx                 # IOMMU state or completion failed.
    cmp $1, %r15
    je .Llab_start
    cmp $2, %r15
    je .Llab_revoke
#ifdef BMO_AMDVI_GUEST_NVME
    cmp $4, %r15
    je .Llab_disk
#endif
#ifdef BMO_AMDVI_GUEST_AHCI
    cmp $5, %r15
    je .Llab_disk
    ja .Llab_start
#endif
    jmp .Llab_stop

#ifdef BMO_AMDVI_GUEST_NVME
.Llab_disk:
    mov 0x18(%r14), %eax
    and $0x1005, %eax
    cmp $0x1005, %eax
    jne .Llab_unmap
    lea 1(%r12), %rax
    cmp %rax, (%r14)
    jne .Llab_unmap
    movabs $LAB_RW, %r8
#ifdef BMO_AMDVI_GUEST_AHCI
    cmp $5, %r15
    jne .Llab_check_nvme_dte
    lea (LAB_AHCI_ROOT+0x403)(%r12), %rax
    or %r8, %rax
    cmp %rax, 0x600(%r12)
    jne .Llab_unmap
    cmpq $3, 0x608(%r12)
    jne .Llab_unmap
    jmp .Llab_call_disk
.Llab_check_nvme_dte:
#endif
    lea (LAB_NVME_ROOT+0x403)(%r12), %rax
    or %r8, %rax
    cmp %rax, 0x900(%r12)
    jne .Llab_unmap
    cmpq $4, 0x908(%r12)
    jne .Llab_unmap
#ifdef BMO_AMDVI_GUEST_AHCI
.Llab_call_disk:
#endif
    lea AMDVI_GUEST_NVME_CODE(%rbp), %rax
    call *%rax
    mov %eax, %ebx
    jmp .Llab_unmap
#endif

.Llab_start:
    mov 0x18(%r14), %rax
    or (%r14), %rax
    or 8(%r14), %rax
    or 16(%r14), %rax
    or 0x2020(%r14), %rax
    jnz .Llab_unmap
#ifdef BMO_AMDVI_GUEST_AHCI
    cmp $6, %r15
    jae .Llab_call_disk
#endif
    movabs $LAB_RW, %r8
    lea LAB_TABLE_OFFSET(%r12), %rdi
#if defined(BMO_AMDVI_ROUTED) || defined(BMO_AMDVI_GSP_DMA)
    # A zero DTE can pass DMA through. Point every unassigned requester
    # at an empty level-2 table in the reserved scratch range.
#ifdef BMO_AMDVI_GSP_DMA
    lea 0x2403(%r12), %rax
    mov $256, %ecx
#else
    lea 0x403(%r12), %rax
    mov $(AMDVI_LAB_TABLE_PAGES*128), %ecx
#endif
    or %r8, %rax
.Llab_deny_dte:
    mov %rax, (%rdi)
    add $32, %rdi
    loop .Llab_deny_dte
    lea LAB_TABLE_OFFSET(%r12), %rdi
#endif
#ifdef BMO_AMDVI_ROUTED
    mov AMDVI_LAB_EDU_RID(%rbp), %esi
    shl $5, %esi
#else
    mov $0x400, %esi
#endif
#ifdef BMO_AMDVI_GSP_DMA
    mov GSP_POST_DMA_ROOT(%rbp), %rax
    or $0x403, %rax
#else
    lea 0x2403(%r12), %rax
#endif
    or %r8, %rax
    mov %rax, (%rdi,%rsi)         # EDU, domain 1.
    movq $1, 8(%rdi,%rsi)
    lea 0x4403(%r12), %rax
    or %r8, %rax
    mov %rax, 0x500(%rdi)         # xHCI 00:05.0, domain 2.
    movq $2, 0x508(%rdi)
    call .Llab_edu_leaf
    lea 0x3201(%r12), %rax
    or %r8, %rax
#ifdef BMO_AMDVI_GSP_DMA
    # EDU needs a result page. Use an unused root slot outside the
    # firmware aperture and preserve every firmware mapping.
    mov GSP_POST_DMA_ROOT(%rbp), %rsi
    cmpq $0, (%rsi,%rdx,8)
    jne .Llab_unmap
    mov %rax, (%rsi,%rdx,8)
#else
    mov %rax, 0x2000(%r12,%rdx,8)
#endif
    lea (LAB_EDU_PAYLOAD+1)(%r12), %rax
    or %r8, %rax
    mov %rax, (%r11)
    mov %r13, %rdi
    mov %r13, %r9
    shr $21, %r9
    mov $14, %ecx
.Llab_usb_leaf:
    mov %rdi, %rdx
    shr $21, %rdx
    mov %rdx, %rax
    sub %r9, %rax
    shl $12, %rax
    lea 0x5000(%r12,%rax), %rsi
    lea 0x201(%rsi), %rax
    or %r8, %rax
    mov %rax, 0x4000(%r12,%rdx,8)
    mov %rdi, %rdx
    shr $12, %rdx
    and $511, %edx
    lea 1(%rdi), %rax
    or %r8, %rax
    mov %rax, (%rsi,%rdx,8)
    add $4096, %rdi
    loop .Llab_usb_leaf
#ifdef BMO_AMDVI_STORAGE
    # 00:06.0 gets its own domain and exactly one page. The IOVA
    # also has reserved backing, kept as an untranslated-write witness.
    lea (LAB_AHCI_ROOT+0x403)(%r12), %rax
    or %r8, %rax
    mov %rax, (LAB_TABLE_OFFSET+0x600)(%r12)
    movq $3, (LAB_TABLE_OFFSET+0x608)(%r12)
    lea LAB_AHCI_IOVA(%r12), %rdx
    mov %rdx, %rdi
    shr $21, %rdx
    shr $12, %rdi
    and $511, %edi
    lea (LAB_AHCI_LEAF+0x201)(%r12), %rax
    or %r8, %rax
    mov %rax, LAB_AHCI_ROOT(%r12,%rdx,8)
    lea (LAB_AHCI_BUFFER+1)(%r12), %rax
    or %r8, %rax
    mov %rax, LAB_AHCI_LEAF(%r12,%rdi,8)
#endif
#ifdef BMO_AMDVI_NVME
    # Five pages at distinct IOVAs for admin SQ/CQ, I/O SQ/CQ and data.
    lea (LAB_NVME_ROOT+0x403)(%r12), %rax
    or %r8, %rax
    mov %rax, 0x900(%r12)        # 00:09.0, domain 4.
    movq $4, 0x908(%r12)
    lea LAB_NVME_IOVA(%r12), %rdi
    lea LAB_NVME_BACKING(%r12), %r10
    mov %rdi, %rsi
    shr $21, %rsi
    mov $5, %ecx
.Llab_nvme_page:
    mov %rdi, %rdx
    shr $21, %rdx
    mov %rdx, %rax
    sub %rsi, %rax
    shl $12, %rax
    lea LAB_NVME_LEAF(%r12,%rax), %r9
    lea 0x201(%r9), %rax
    or %r8, %rax
    mov %rax, LAB_NVME_ROOT(%r12,%rdx,8)
    mov %rdi, %rdx
    shr $12, %rdx
    and $511, %edx
    lea 1(%r10), %rax
    or %r8, %rax
    mov %rax, (%r9,%rdx,8)
    add $4096, %rdi
    add $4096, %r10
    loop .Llab_nvme_page
#endif
    lea (LAB_TABLE_OFFSET+LAB_TABLE_LENGTH)(%r12), %rax
    mov %rax, (%r14)
    movabs $0x0800000000000000, %rcx
    lea 0x7000(%r12), %rax
    or %rcx, %rax
    mov %rax, 8(%r14)
    lea 0x8000(%r12), %rax
    or %rcx, %rax
    mov %rax, 16(%r14)
    movq $0x1005, 0x18(%r14)
    testb $1, 0x18(%r14)
    jz .Llab_clear
#ifdef BMO_AMDVI_ROUTED
    # QEMU uses passthrough until the device's DTE is invalidated.
    # Refresh every present function, including default-denied entries.
    mov AMDVI_LAB_PRESENT_COUNT(%rbp), %r9d
    xor %r10d, %r10d
    xor %ecx, %ecx
.Llab_invalidate_present:
    movzwl AMDVI_LAB_PRESENT_RIDS(%rbp,%r10,2), %eax
    movabs $0x2000000000000000, %rsi
    or %rsi, %rax
    xor %edx, %edx
    call .Llab_publish
    jc .Llab_clear
    inc %r10d
    cmp %r9d, %r10d
    jb .Llab_invalidate_present
#else
    movabs $0x2000000000000020, %rax
    xor %edx, %edx
    xor %ecx, %ecx
    call .Llab_publish
    jc .Llab_clear
    movabs $0x2000000000000028, %rax
    xor %edx, %edx
    mov $32, %ecx
    call .Llab_publish
    jc .Llab_clear
#ifdef BMO_AMDVI_STORAGE
    movabs $0x2000000000000030, %rax
    xor %edx, %edx
    mov $64, %ecx
    call .Llab_publish
    jc .Llab_clear
#endif
#ifdef BMO_AMDVI_NVME
    movabs $0x2000000000000048, %rax
    xor %edx, %edx
    mov $96, %ecx
    call .Llab_publish
    jc .Llab_clear
#endif
#endif
    jmp .Llab_success
.Llab_revoke:
    testb $1, 0x18(%r14)
    jz .Llab_unmap
    call .Llab_edu_leaf
    movq $0, (%r11)
#ifdef BMO_AMDVI_GSP_DMA
    mov GSP_POST_DMA_ROOT(%rbp), %rax
    movq $0, (%rax,%rdx,8)
    lea 0x2403(%r12), %rax
    movabs $LAB_RW, %r8
    or %r8, %rax
    mov %rax, 0x400(%r12)
    movq $0, 0x408(%r12)
    movabs $0x7ffffffffffff003, %rdx # All IOVAs, including cached page-table entries.
#else
    lea LAB_EDU_IOVA(%r12), %rdx
#endif
    movabs $0x3000000100000000, %rax
#ifdef BMO_AMDVI_ROUTED
    mov 0x9000(%r12), %ecx
#else
    mov $LAB_EDU_REVOKE, %ecx
#endif
    call .Llab_publish
    jc .Llab_unmap               # Keep the reservation pinned on failure.
#ifdef BMO_AMDVI_GSP_DMA
    movabs $0x2000000000000020, %rax
    xor %edx, %edx
    call .Llab_publish
    jc .Llab_unmap
#endif
    jmp .Llab_success
.Llab_stop:
    xor %ebx, %ebx
.Llab_clear:
    movq $0, 0x18(%r14)
    mov 0x18(%r14), %rax
    mov %rax, AMDVI_LAB_CONTROL_AFTER_STOP(%rbp)
    test $1, %al
    jnz .Llab_stop_failed
    movq $0, (%r14)
    movq $0, 8(%r14)
    movq $0, 16(%r14)
    movq $0, 0x2000(%r14)
    movq $0, 0x2008(%r14)
    movq $0, 0x2010(%r14)
    movq $0, 0x2018(%r14)
    test %ebx, %ebx
    jnz .Llab_unmap
    jmp .Llab_success
.Llab_stop_failed:
    mov $3, %ebx
    jmp .Llab_unmap
.Llab_success:
    mov %r15, AMDVI_LAB_PHASE(%rbp)
    xor %ebx, %ebx
.Llab_unmap:
    movq $0, 0x15408(%rbp)
    movq $0, LAB_PT(%r12)
#ifdef BMO_AMDVI_GUEST_NVME
    movq $0, (LAB_PT+8)(%r12)
    invlpg 0x1000(%r14)
#endif
    movq $0, (LAB_PT+16)(%r12)
    invlpg (%r14)
    invlpg 0x2000(%r14)
    jmp .Llab_done
.Llab_reject:
    mov $1, %ebx
    jmp .Llab_done
.Llab_pci_rejected:
    mov $2, %ebx
.Llab_done:
    mov %rbx, AMDVI_LAB_RESULT(%rbp)
    movq $0, AMDVI_LAB_REQUEST(%rbp)
    pop %r15
    pop %r14
    pop %r13
    pop %r12
    pop %rbx
    ret

.Llab_edu_leaf:
    lea LAB_EDU_IOVA(%r12), %rax
    mov %rax, %rdx
    shr $21, %rdx
    shr $12, %rax
    and $511, %eax
    lea 0x3000(%r12,%rax,8), %r11
    ret

.Llab_publish:
    lea 0x7000(%r12,%rcx), %rdi
    mov %rax, (%rdi)
    mov %rdx, 8(%rdi)
    movabs $0x1000000000000001, %rax
    lea 0x9000(%r12), %rsi
    or %rsi, %rax
    mov %rax, 16(%rdi)
    add $32, %ecx
    mov %rcx, 24(%rdi)
    mfence
    mov %rcx, 0x2008(%r14)
    mov $100000, %eax
.Llab_wait:
    cmp %rcx, (%rsi)
    je .Llab_completed
    pause
    dec %eax
    jnz .Llab_wait
    stc
    ret
.Llab_completed:
    cmp %rcx, 0x2000(%r14)
    jne .Llab_completion_failed
    clc
    ret
.Llab_completion_failed:
    stc
    ret

.Llab_pci:
    mov $0xcf8, %dx
    in %dx, %eax
    mov %eax, %r9d
#ifdef BMO_AMDVI_ROUTED
    xor %r11d, %r11d
    xor %r8d, %r8d
#else
    mov $0x80002000, %eax
    call .Llab_read_pci
    cmp $0x11e81234, %eax
    jne .Llab_pci_bad
#endif
    mov $0x80002800, %eax
    call .Llab_read_pci
    cmp $0x000d1b36, %eax
    jne .Llab_pci_bad
#ifdef BMO_AMDVI_STORAGE
    mov $0x80003000, %eax
    call .Llab_read_pci
    cmp $0x29228086, %eax
    jne .Llab_pci_bad
#endif
#ifdef BMO_AMDVI_NVME
    mov $0x80004800, %eax
    call .Llab_read_pci
    cmp $0x00101b36, %eax
    jne .Llab_pci_bad
#endif
    mov $0x80000000, %r10d
.Llab_scan:
    mov %r10d, %eax
    call .Llab_read_pci
    cmp $0xffff, %ax
    je .Llab_advance
#ifdef BMO_AMDVI_ROUTED
    cmp $AMDVI_LAB_MAX_PRESENT, %r8d
    jae .Llab_pci_bad
    mov %r10d, %esi
    shr $8, %esi
    movzwl %si, %esi
    cmp $(AMDVI_LAB_TABLE_PAGES*128), %esi
    jae .Llab_pci_bad
    mov %si, AMDVI_LAB_PRESENT_RIDS(%rbp,%r8,2)
    inc %r8d
    cmp $0x11e81234, %eax
    jne .Llab_class
    cmp $0x80002000, %r10d        # Unassigned EDU witness at 00:04.0.
    je .Llab_class
    # Obtain the BDF from PCI enumeration, never from the test mailbox.
    mov %r10d, %eax
    shr $8, %eax
    movzwl %ax, %eax
    cmp $0x2900, %eax
    jb .Llab_pci_bad
    test %r11d, %r11d
    jnz .Llab_pci_bad
    mov %eax, %r11d
.Llab_class:
#endif
    lea 8(%r10), %eax
    call .Llab_read_pci
    shr $16, %eax
    cmp $0x0604, %eax
#ifdef BMO_AMDVI_ROUTED
    jne .Llab_command
    # The two fixture root ports route downstream traffic; scan every
    # bus including their children and admit only known DMA requesters.
    cmp $0x80003800, %r10d
    je .Llab_advance
    cmp $0x80004000, %r10d
    je .Llab_advance
    jmp .Llab_pci_bad
.Llab_command:
#else
    je .Llab_pci_bad
#endif
    lea 4(%r10), %eax
    call .Llab_read_pci
    test $4, %eax
    jz .Llab_advance
#ifdef BMO_AMDVI_STORAGE
    cmp $0x80003000, %r10d
    jne .Llab_xhci_master
#ifdef BMO_AMDVI_GUEST_AHCI
    cmp $6, %r15
    jae .Llab_advance
#endif
    cmp $2, %r15                 # Start and stop require AHCI quiesced.
    jne .Llab_pci_bad
    jmp .Llab_advance
.Llab_xhci_master:
#endif
#ifdef BMO_AMDVI_GUEST_AHCI
    cmp $0x80004800, %r10d
    jne .Llab_usb_master
    cmp $6, %r15
    jae .Llab_advance
    jmp .Llab_pci_bad
.Llab_usb_master:
#endif
    cmp $0x80002800, %r10d
    jne .Llab_pci_bad
.Llab_advance:
    add $256, %r10d
#ifdef BMO_AMDVI_ROUTED
    cmp $0x81000000, %r10d
    jne .Llab_scan
    test %r11d, %r11d
    jz .Llab_pci_bad
    mov %r11, AMDVI_LAB_EDU_RID(%rbp)
    mov %r8d, AMDVI_LAB_PRESENT_COUNT(%rbp)
#else
    cmp $0x80010000, %r10d
    jne .Llab_scan
#endif
    mov %r9d, %eax
    out %eax, %dx
    clc
    ret
.Llab_pci_bad:
    mov %r9d, %eax
    out %eax, %dx
    stc
    ret
.Llab_read_pci:
    out %eax, %dx
    add $4, %dx
    in %dx, %eax
    sub $4, %dx
    ret

.Llab_loader_data:
    mov 0x60(%rbp), %r8
    mov 0x50(%rbp), %rcx
    cmp $40, %r8
    jb .Llab_bad_map
    cmp $256, %r8
    ja .Llab_bad_map
    cmp $65536, %rcx
    ja .Llab_bad_map
    lea 0x1000(%rbp), %r9
.Llab_record:
    cmp %r8, %rcx
    jb .Llab_bad_map
    cmpl $2, (%r9)
    jne .Llab_record_next
    mov 8(%r9), %rax
    cmp %rax, %rdi
    jb .Llab_record_next
    mov %rsi, %rdx
    sub %rax, %rdx
    shr $12, %rdx
    cmp 24(%r9), %rdx
    jbe .Llab_map_ok
.Llab_record_next:
    add %r8, %r9
    sub %r8, %rcx
    jmp .Llab_record
.Llab_bad_map:
    stc
    ret
.Llab_map_ok:
    clc
    ret
