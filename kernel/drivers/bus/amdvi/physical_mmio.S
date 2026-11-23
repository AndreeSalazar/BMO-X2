# Measured board, opt-in. Win64 ABI, no external calls.
# RCX: writable supervisor MMIO alias covering offsets 0..2027h.
# RDX: {DTE base, command page, event page, original[3], installed[3]}.
# Caller validates the EFI reservations, empties both queue pages and
# owns this IOMMU exclusively. This entry only stages disabled registers.
# Returns 0 rejected, 1 staged/restored, 2 mismatch with verified rollback,
# 3 unverified rollback (caller must retain all allocations).
.text
.globl amdvi_stage_physical_registers
amdvi_stage_physical_registers:
.Lstage_physical_registers:
    test %rcx, %rcx
    jz .Lreject
    test %rdx, %rdx
    jz .Lreject
    cmpq $0, 48(%rdx)
    jne .Lreject
    mov (%rdx), %r8
    mov 8(%rdx), %r9
    mov 16(%rdx), %r10
    mov %r8, %rax
    or %r9, %rax
    or %r10, %rax
    test $4095, %eax
    jnz .Lreject
    cmp $0x100000, %r8
    jb .Lreject
    cmp $0xfe00000, %r8
    ja .Lreject
    cmp $0x100000, %r9
    jb .Lreject
    cmp $0xffff000, %r9
    ja .Lreject
    cmp $0x100000, %r10
    jb .Lreject
    cmp $0xffff000, %r10
    ja .Lreject
    cmp %r9, %r10
    je .Lreject
    lea 0x200000(%r8), %rax
    cmp %rax, %r9
    jae .Lcommand_disjoint
    cmp %r8, %r9
    jae .Lreject
.Lcommand_disjoint:
    cmp %rax, %r10
    jae .Levent_disjoint
    cmp %r8, %r10
    jae .Lreject
.Levent_disjoint:
    call .Lidle
    jne .Lreject
    cmpq $0, (%rcx)                 # The tested firmware left no DTE installed.
    jne .Lreject
    call .Lempty
    jne .Lreject
    mov (%rcx), %rax
    mov %rax, 24(%rdx)
    mov 8(%rcx), %rax
    cmp $-1, %rax
    je .Lreject
    mov %rax, 32(%rdx)
    mov 16(%rcx), %rax
    cmp $-1, %rax
    je .Lreject
    mov %rax, 40(%rdx)
    or $511, %r8
    movabs $0x0800000000000000, %rax
    or %rax, %r9
    or %rax, %r10
    mov %r8, 48(%rdx)
    mov %r9, 56(%rdx)
    mov %r10, 64(%rdx)
    sfence
    mov %r8, (%rcx)
    mov %r9, 8(%rcx)
    mov %r10, 16(%rcx)
    call .Lidle
    jne .Lunverified
    call .Lempty
    jne .Lunverified
    cmp (%rcx), %r8
    jne .Lrollback
    cmp 8(%rcx), %r9
    jne .Lrollback
    cmp 16(%rcx), %r10
    jne .Lrollback
    mov $1, %eax
    ret
.Lrollback:
    call .Lrestore
    jc .Lunverified
    mov $2, %eax
    ret

.globl amdvi_restore_physical_registers
amdvi_restore_physical_registers:
.Lrestore_physical_registers:
    test %rcx, %rcx
    jz .Lreject
    test %rdx, %rdx
    jz .Lreject
    cmpq $0, 48(%rdx)            # No staged receipt.
    je .Lreject
    call .Lidle
    jne .Lunverified
    call .Lempty
    jne .Lunverified
    mov 48(%rdx), %rax
    cmp %rax, (%rcx)
    jne .Lunverified
    mov 56(%rdx), %rax
    cmp %rax, 8(%rcx)
    jne .Lunverified
    mov 64(%rdx), %rax
    cmp %rax, 16(%rcx)
    jne .Lunverified
    call .Lrestore
    jc .Lunverified
    mov $1, %eax
    ret
.Lreject:
    xor %eax, %eax
    ret
.Lunverified:
    mov $3, %eax
    ret
.Lidle:
    # Accept the exact observed disabled Control value, only.
    movabs $0x0000220000000400, %rax
    cmp %rax, 0x18(%rcx)
    jne .Lidle_done
    cmpq $0, 0x2020(%rcx)
.Lidle_done:
    ret
.Lempty:
    mov 0x2000(%rcx), %rax
    or 0x2008(%rcx), %rax
    or 0x2010(%rcx), %rax
    or 0x2018(%rcx), %rax
    ret
.Lrestore:
    mov 40(%rdx), %r10
    mov 32(%rdx), %r9
    mov 24(%rdx), %r8
    mov %r10, 16(%rcx)
    mov %r9, 8(%rcx)
    mov %r8, (%rcx)
    call .Lidle
    jne .Lrestore_failed
    cmp (%rcx), %r8
    jne .Lrestore_failed
    cmp 8(%rcx), %r9
    jne .Lrestore_failed
    cmp 16(%rcx), %r10
    jne .Lrestore_failed
    movq $0, 48(%rdx)
    movq $0, 56(%rdx)
    movq $0, 64(%rdx)
    clc
    ret
.Lrestore_failed:
    stc
    ret
