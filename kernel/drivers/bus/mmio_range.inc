# R8/R9 is the page-aligned physical range. Reject any overlap with
# a non-MMIO EFI descriptor in the final map.
.Lmmio_map_range:
    mov 0x60(%rbp), %rsi
    cmp $40, %rsi
    jb .Lmmio_map_bad
    cmp $256, %rsi
    ja .Lmmio_map_bad
    mov 0x50(%rbp), %rcx
    test %rcx, %rcx
    jz .Lmmio_map_bad
    cmp $65536, %rcx
    ja .Lmmio_map_bad
    lea 0x1000(%rbp), %rdi
.Lmmio_map_next:
    cmp %rsi, %rcx
    jb .Lmmio_map_bad
    cmpl $11, (%rdi)
    je .Lmmio_map_advance
    mov 8(%rdi), %rax
    cmp %r9, %rax
    jae .Lmmio_map_advance
    mov 24(%rdi), %rdx
    mov %rdx, %r10
    shr $40, %r10
    jnz .Lmmio_map_bad
    shl $12, %rdx
    add %rax, %rdx
    jc .Lmmio_map_bad
    cmp %r8, %rdx
    ja .Lmmio_map_bad
.Lmmio_map_advance:
    add %rsi, %rdi
    sub %rsi, %rcx
    jnz .Lmmio_map_next
    clc
    ret
.Lmmio_map_bad:
    stc
    ret
