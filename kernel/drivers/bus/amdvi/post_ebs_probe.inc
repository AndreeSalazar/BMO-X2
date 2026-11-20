// Copied by the pre-EBS stage. RBP is the supervisor-owned handoff.
// The native desktop takes the snapshot before starting xHCI, which
// later uses this same temporary page-table slot.
amdvi_post_begin:
    push %rbx
    mov $1, %ebx                   # No usable pre-EBS capture.
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
    movq $0, 0x15400(%rbp)
    movq $0, 0x1e000(%rbp)
    movq $0, 0x1e010(%rbp)
    invlpg (%rdi)
    invlpg 0x2000(%rdi)
.Lpost_done:
    mov %rbx, AMDVI_POST_STATUS(%rbp)
    pop %rbx
    ret

.p2align 1
.Lpost_offsets:
    .short 0x0018, 0x0000, 0x0008, 0x0010, 0x2020
amdvi_post_end:
