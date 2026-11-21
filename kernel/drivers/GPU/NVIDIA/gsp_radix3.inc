# RDI: writable page-aligned supervisor mapping.
# RSI: first firmware IOVA. RDX: first directory IOVA.
# RCX: firmware pages (1..262144). R8: writable capacity in bytes.
# Both IOVA ranges are contiguous and reserved by the caller.
# RAX: root IOVA, or zero with the output untouched on rejection.
nvidia_gsp_radix3:
    lea -1(%rcx), %rax
    cmp $262143, %rax
    ja .Lgsp_radix_reject
    test %rdi, %rdi
    jz .Lgsp_radix_reject
    cmp $4096, %rsi
    jb .Lgsp_radix_reject
    cmp $4096, %rdx
    jb .Lgsp_radix_reject
    mov %edi, %eax
    or %esi, %eax
    or %edx, %eax
    test $4095, %eax
    jnz .Lgsp_radix_reject

    lea 511(%rcx), %r9
    shr $9, %r9
    lea 2(%r9), %r10
    shl $12, %r10
    cmp %r10, %r8
    jb .Lgsp_radix_reject
    mov %rdi, %r8
    add %r10, %r8
    jc .Lgsp_radix_reject

    mov %rcx, %r11
    shl $12, %r11
    add %rsi, %r11
    jc .Lgsp_radix_reject
    mov %rdx, %r8
    add %r10, %r8
    jc .Lgsp_radix_reject
    movabs $0x10000000000000, %rax
    cmp %rax, %r11
    ja .Lgsp_radix_reject
    cmp %rax, %r8
    ja .Lgsp_radix_reject
    cmp %r11, %rdx
    jae .Lgsp_radix_write
    cmp %r8, %rsi
    jb .Lgsp_radix_reject

.Lgsp_radix_write:
    mov %rcx, %r11
    mov %rdi, %r8
    mov %r10, %rcx
    shr $3, %rcx
    xor %eax, %eax
    cld
    rep stosq

    lea 4096(%rdx), %rax
    mov %rax, (%r8)
    lea 4096(%r8), %rdi
    add $4096, %rax
.Lgsp_radix_middle:
    stosq
    add $4096, %rax
    dec %r9
    jnz .Lgsp_radix_middle

    lea 8192(%r8), %rdi
    mov %rsi, %rax
.Lgsp_radix_leaf:
    stosq
    add $4096, %rax
    dec %r11
    jnz .Lgsp_radix_leaf
    mov %rdx, %rax
    ret

.Lgsp_radix_reject:
    xor %eax, %eax
    ret
