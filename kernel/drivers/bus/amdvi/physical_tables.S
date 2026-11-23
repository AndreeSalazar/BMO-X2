# Win64 ABI. Scratch-only constructor for the measured AMD board.
# RCX = mapped 2 MiB DTE table; RDX = mapped four-page workspace.
# R8  = workspace physical base; R9 = {DTE physical base, RTX root, USB DMA base}.
# The caller owns both writable mappings and verifies the RTX tree and EFI
# reservations. Return 1 on success, 0 before any write on invalid geometry.
# Workspace pages: empty deny root, xHCI root, two possible xHCI leaves.
.text
.globl amdvi_build_physical_tables
amdvi_build_physical_tables:
    test %rcx, %rcx
    jz .Linvalid
    test %rdx, %rdx
    jz .Linvalid
    test %r9, %r9
    jz .Linvalid
    mov %rcx, %r10
    or %rdx, %r10
    test $4095, %r10
    jnz .Linvalid
    lea 0x200000(%rcx), %r10
    cmp %rcx, %r10
    jbe .Linvalid
    lea 0x4000(%rdx), %rax
    cmp %rdx, %rax
    jbe .Linvalid
    cmp %r10, %rdx
    jae .Lvirtual_ok
    cmp %rax, %rcx
    jb .Linvalid
.Lvirtual_ok:
    push %rbx
    push %rsi
    push %rdi
    push %r12
    mov %rcx, %rdi
    mov %rdx, %rsi
    mov (%r9), %r10
    mov 8(%r9), %r11
    mov 16(%r9), %r12
    mov %r8, %rax
    or %r10, %rax
    or %r11, %rax
    or %r12, %rax
    test $4095, %rax
    jnz .Lreject
    cmp $4096, %r8
    jb .Lreject
    cmp $4096, %r10
    jb .Lreject
    cmp $4096, %r11
    jb .Lreject
    cmp $4096, %r12
    jb .Lreject
    movabs $((1 << 52)-0x200000), %rax
    cmp %rax, %r10
    ja .Lreject
    add $0x1fc000, %rax
    cmp %rax, %r8
    ja .Lreject
    add $0x3000, %rax
    cmp %rax, %r11
    ja .Lreject
    cmp $(0x40000000-14*4096), %r12
    ja .Lreject
    # All pairs must be disjoint. Range ends are already bounded.
    .macro disjoint a, alen, b, blen
        lea \alen(\a), %rax
        cmp %rax, \b
        jae 9f
        lea \blen(\b), %rax
        cmp %rax, \a
        jb .Lreject
9:
    .endm
    disjoint %r10, 0x200000, %r8, 0x4000
    disjoint %r10, 0x200000, %r11, 0x1000
    disjoint %r10, 0x200000, %r12, 0xe000
    disjoint %r8, 0x4000, %r11, 0x1000
    disjoint %r8, 0x4000, %r12, 0xe000
    disjoint %r11, 0x1000, %r12, 0xe000
    mov %rdi, %r10
    xor %eax, %eax
    mov $0x40000, %ecx
    cld
    rep stosq
    mov %rsi, %rdi
    mov $0x800, %ecx
    rep stosq
    movabs $0x6000000000000403, %rbx
    mov %r8, %rax
    or %rbx, %rax
    mov %r10, %rdi
    mov $65536, %ecx
.Ldefault_deny:
    mov %rax, (%rdi)
    add $32, %rdi
    dec %ecx
    jnz .Ldefault_deny
    or %rbx, %r11
    mov %r11, (0x2900*32)(%r10)
    movq $5, (0x2900*32+8)(%r10)
    lea 0x1000(%r8), %rax
    or %rbx, %rax
    mov %rax, (0x2b03*32)(%r10)
    movq $2, (0x2b03*32+8)(%r10)
    movabs $0x6000000000000001, %rbx
    mov %r12, %r9
    shr $21, %r9
    mov $14, %ecx
.Lusb_identity:
    mov %r12, %r10
    shr $21, %r10
    mov %r10, %rdx
    sub %r9, %rdx
    shl $12, %rdx
    lea 0x2200(%r8,%rdx), %rax
    or %rbx, %rax
    mov %rax, 0x1000(%rsi,%r10,8)
    mov %r12, %rax
    or %rbx, %rax
    mov %r12, %r10
    shr $12, %r10
    and $511, %r10d
    lea 0x2000(%rsi,%rdx), %rdx
    mov %rax, (%rdx,%r10,8)
    add $4096, %r12
    dec %ecx
    jnz .Lusb_identity
    mov $1, %eax
    jmp .Ldone
.Lreject:
    xor %eax, %eax
.Ldone:
    pop %r12
    pop %rdi
    pop %rsi
    pop %rbx
    ret
.Linvalid:
    xor %eax, %eax
    ret
