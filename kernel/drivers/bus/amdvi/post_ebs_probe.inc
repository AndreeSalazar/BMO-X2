// Copied by the pre-EBS stage. RBP is the supervisor-owned handoff.
// The native desktop takes the snapshot before starting xHCI, which
// later uses this same temporary page-table slot.
amdvi_post_begin:
#ifdef BMO_AMDVI_GUEST_DMA
    .byte 0xe9
    .long .Lpost_read_entry - . - 4
    .byte 0xe9
    .long amdvi_lab_entry - . - 4
.Lpost_read_entry:
#endif
#ifdef BMO_DMA_CENSUS
    .byte 0xe9
    .long .Lpost_census_entry - . - 4
    .byte 0xe9
    .long dma_census - . - 4
.Lpost_census_entry:
#endif
    push %rbx
    push %r12
    mov $1, %ebx                   # No usable pre-EBS capture.
#ifdef BMO_AMDVI_DTE_RESERVE
    movq $0, AMDVI_DTE_POST_STATUS(%rbp)
    movq $0, AMDVI_DTE_POST_ZERO_QWORDS(%rbp)
    movq $0, AMDVI_DTE_POST_PTE_FIRST(%rbp)
    movq $0, AMDVI_DTE_POST_PTE_LAST(%rbp)
#endif
    mov AMDVI_POST_BASE(%rbp), %r8
    test %r8, %r8
    jz .Lpost_done

    mov $2, %ebx                   # Active mapping, PAT, or memory map refused.
    mov %cr3, %rax
    lea 0x13000(%rbp), %rcx
    cmp %rcx, %rax
    jne .Lpost_done
    cmpq $0, 0x15400(%rbp)
    jne .Lpost_done
    mov $1, %eax
    push %rbx
    cpuid
    pop %rbx
    test $0x10000, %edx            # IA32_PAT implemented.
    jz .Lpost_done
    mov $0x277, %ecx
    rdmsr
    test $0xff000000, %eax         # PAT index 3 must be UC.
    jnz .Lpost_done
    mov 0x60(%rbp), %r9
    cmp $40, %r9
    jb .Lpost_done
    cmp $256, %r9
    ja .Lpost_done
    mov 0x50(%rbp), %rcx
    test %rcx, %rcx
    jz .Lpost_done
    cmp $65536, %rcx
    ja .Lpost_done
    lea 0x1000(%rbp), %rsi
.Lpost_descriptor:
    cmp %r9, %rcx
    jb .Lpost_done
    cmpl $11, (%rsi)               # EFI MMIO may cover either page.
    je .Lpost_next
    mov 8(%rsi), %rdx
    cmp %rdx, %r8
    jb .Lpost_page2
    mov %r8, %rax
    sub %rdx, %rax
    shr $12, %rax
    cmp 24(%rsi), %rax
    jb .Lpost_done
.Lpost_page2:
    lea 0x2000(%r8), %rax
    cmp %rdx, %rax
    jb .Lpost_next
    sub %rdx, %rax
    shr $12, %rax
    cmp 24(%rsi), %rax
    jb .Lpost_done
.Lpost_next:
    add %r9, %rsi
    sub %r9, %rcx
    jnz .Lpost_descriptor

#ifdef BMO_AMDVI_DTE_RESERVE
    # Revalidate the firmware reservation from the final EFI memory map.
    # The descriptor must still own every page as EfiLoaderData (type 2).
    mov $2, %ebx                   # Reservation absent or not retained by EBS.
    cmpq $1, AMDVI_DTE_RESERVE_STATUS(%rbp)
    jne .Ldte_post_done
    cmpq $AMDVI_DTE_TABLE_PAGES, AMDVI_DTE_RESERVE_PAGES(%rbp)
    jne .Ldte_post_done
    mov AMDVI_DTE_RESERVE_BASE(%rbp), %r12
    test %r12, %r12
    jz .Ldte_post_done
    test $0xfff, %r12
    jnz .Ldte_post_done
    mov %r12, %rax
    add $AMDVI_DTE_TABLE_BYTES, %rax
    jc .Ldte_post_done
    mov 0x50(%rbp), %rcx
    mov 0x60(%rbp), %r9
    cmp $40, %r9
    jb .Ldte_post_done
    cmp $256, %r9
    ja .Ldte_post_done
    cmp $65536, %rcx
    ja .Ldte_post_done
    lea 0x1000(%rbp), %rsi
    mov $3, %ebx                   # Reservation does not fit an EFI loader descriptor.
.Ldte_post_memory:
    cmp %r9, %rcx
    jb .Ldte_post_done
    cmpl $2, (%rsi)
    jne .Ldte_post_memory_next
    mov 8(%rsi), %rax
    mov 24(%rsi), %rdx
    shl $12, %rdx
    add %rax, %rdx
    jc .Ldte_post_memory_next
    cmp %rax, %r12
    jb .Ldte_post_memory_next
    mov %r12, %r11
    add $AMDVI_DTE_TABLE_BYTES, %r11
    jc .Ldte_post_memory_next
    cmp %rdx, %r11
    jbe .Ldte_post_memory_found
.Ldte_post_memory_next:
    add %r9, %rsi
    sub %r9, %rcx
    jnz .Ldte_post_memory
    jmp .Ldte_post_done
.Ldte_post_memory_found:
    # Alias exactly one 2 MiB region through the scratch PT. Leaf PTEs are
    # supervisor, read-only, NX, and write-back; no device sees this mapping.
    lea 0x1e000(%rbp), %rdi
    mov %r12, %r10
    mov $AMDVI_DTE_TABLE_PAGES, %ecx
.Ldte_post_map:
    mov %r10, %rax
    or $1, %rax
    bts $63, %rax
    mov %rax, (%rdi)
    add $4096, %r10
    add $8, %rdi
    loop .Ldte_post_map
    mov 0x1e000(%rbp), %rax
    mov %rax, AMDVI_DTE_POST_PTE_FIRST(%rbp)
    mov 0x1eff8(%rbp), %rax
    mov %rax, AMDVI_DTE_POST_PTE_LAST(%rbp)
    lea 0x1e003(%rbp), %rax
    mov %rax, 0x15400(%rbp)
    mov $0x10000000, %edi
    mov $AMDVI_DTE_TABLE_PAGES, %ecx
.Ldte_post_invalidate:
    invlpg (%rdi)
    add $4096, %rdi
    loop .Ldte_post_invalidate
    mov $4, %ebx                   # Readback failed; still revoke the alias.
    xor %eax, %eax
    mov $0x10000000, %edi
    mov $AMDVI_DTE_TABLE_QWORDS, %ecx
    cld
    repe scasq
    jne .Ldte_post_revoke
    mov $1, %ebx
    movq $AMDVI_DTE_TABLE_QWORDS, AMDVI_DTE_POST_ZERO_QWORDS(%rbp)
.Ldte_post_revoke:
    # Remove the PDE first, invalidate every address, then clear the PT.
    movq $0, 0x15400(%rbp)
    mov $0x10000000, %rdi
    lea 0x1e000(%rbp), %rsi
    mov $AMDVI_DTE_TABLE_PAGES, %ecx
.Ldte_post_unmap:
    invlpg (%rdi)
    movq $0, (%rsi)
    add $4096, %rdi
    add $8, %rsi
    loop .Ldte_post_unmap
    cmpq $0, 0x15400(%rbp)
    jne .Ldte_post_revoke_failed
    lea 0x1e000(%rbp), %rdi
    xor %eax, %eax
    mov $512, %ecx
    cld
    repe scasq
    jne .Ldte_post_revoke_failed
    mov %rbx, AMDVI_DTE_POST_STATUS(%rbp)
    jmp .Ldte_post_done
.Ldte_post_revoke_failed:
    movq $5, AMDVI_DTE_POST_STATUS(%rbp)
    jmp .Ldte_post_continue
.Ldte_post_done:
    mov %rbx, AMDVI_DTE_POST_STATUS(%rbp)
.Ldte_post_continue:
#endif

    mov $3, %ebx                   # PCI base or decode changed since pre-EBS.
    mov $0xcf8, %dx
    in %dx, %eax
    mov %eax, %edi
    mov AMDVI_POST_PCI(%rbp), %ecx
    mov %ecx, %eax
    out %eax, %dx
    add $4, %dx
    in %dx, %eax
    mov %eax, %r9d
    sub $4, %dx
    lea 4(%rcx), %eax
    out %eax, %dx
    add $4, %dx
    in %dx, %eax
    mov %eax, %r10d
    sub $4, %dx
    mov %edi, %eax
    out %eax, %dx
    test %r10d, %r10d
    jnz .Lpost_done
    cmp AMDVI_POST_PCI_LOW(%rbp), %r9d
    jne .Lpost_done

    # The two leaf entries are present, read-only, supervisor, UC and NX.
    # This is the same scratch PT later used by xHCI; publish the PDE last.
    lea 0x1e000(%rbp), %rdi
    xor %eax, %eax
    mov $512, %ecx
    cld
    rep stosq
    mov %r8, %rax
    or $0x19, %rax
    bts $63, %rax
    mov %rax, 0x1e000(%rbp)
    mov %rax, AMDVI_POST_PTE0(%rbp)
    add $0x2000, %rax
    mov %rax, 0x1e010(%rbp)
    mov %rax, AMDVI_POST_PTE2(%rbp)
    lea 0x1e003(%rbp), %rax
    mov %rax, 0x15400(%rbp)
    mov $0x10000000, %edi
    invlpg (%rdi)
    invlpg 0x2000(%rdi)

    lea AMDVI_POST_REGISTERS(%rbp), %rsi
    lea .Lpost_offsets(%rip), %r9
    mov $5, %ebx                   # MMIO returned all ones.
    xor %ecx, %ecx
.Lpost_read:
    movzwl (%r9,%rcx,2), %edx
    mov (%rdi,%rdx), %eax
    mov 4(%rdi,%rdx), %edx
    shl $32, %rdx
    or %rdx, %rax
    cmp $-1, %rax
    je .Lpost_revoke
    mov %rax, (%rsi,%rcx,8)
    inc %ecx
    cmp $5, %ecx
    jb .Lpost_read
    mov $4, %ebx
.Lpost_revoke:
#ifdef BMO_AMDVI_PHYSICAL_MMIO_TEST
    lea AMDVI_PHYSICAL_MMIO_CODE(%rbp), %rax
    call *%rax
#endif
    movq $0, 0x15400(%rbp)
    movq $0, 0x1e000(%rbp)
    movq $0, 0x1e010(%rbp)
    invlpg (%rdi)
    invlpg 0x2000(%rdi)
.Lpost_done:
    mov %rbx, AMDVI_POST_STATUS(%rbp)
#ifdef BMO_STORAGE_STATE
    call storage_snapshot
#endif
    pop %r12
    pop %rbx
    ret

.p2align 1
.Lpost_offsets:
    .short 0x0018, 0x0000, 0x0008, 0x0010, 0x2020
#ifdef BMO_AMDVI_GUEST_DMA
#include "coexist_guest.inc"
#endif
#ifdef BMO_DMA_CENSUS
#include "dma_census.inc"
#endif
#ifdef BMO_STORAGE_STATE
#include "../../storage/handoff_post.inc"
#endif
amdvi_post_end:
