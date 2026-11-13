.text
# QEMU staging: a qword length followed by the unchanged SBEF.
# R11 is the private page-table reservation, R10 its descriptor page.
.globl external_sbef
external_sbef:
    mov $0x2000000, %esi
    mov (%rsi), %rdx
    add $8, %rsi
    cmp $64, %rdx
    jb reject
    cmp $12384, %rdx
    ja reject
    movabs $0x0001000146454253, %rax
    cmp %rax, (%rsi)
    jne reject
    mov 8(%rsi), %eax
    cmp $0x1003e, %eax
    je one_region
    cmp $0x2003e, %eax
    jne reject
    mov $96, %r8d
    jmp header
one_region:
    mov $64, %r8d
header:
    cmp %r8d, %edx
    jb reject
    cmp %edx, 12(%rsi)
    jne reject
    cmpq $0, 24(%rsi)
    jne reject
    cmpq $0x40000000, 32(%rsi)
    jne reject
    cmp %r8d, 40(%rsi)
    jne reject
    cmpl $5, 52(%rsi)
    jne reject_permissions
    cmpq $0, 56(%rsi)
    jne reject
    sub %r8d, %edx
    mov 44(%rsi), %ecx
    test %ecx, %ecx
    jz reject
    sub %ecx, %edx
    jb reject
    mov 48(%rsi), %eax
    cmp %ecx, %eax
    jb reject
    cmp $8192, %eax
    ja reject
    mov 16(%rsi), %r12
    mov %r12, %rax
    sub $0x40000000, %rax
    cmp %rcx, %rax
    jae reject
    xor %r9d, %r9d
    cmp $64, %r8d
    je payload_checked
    cmpq $0x40003000, 64(%rsi)
    jne reject
    lea (%rcx,%r8), %rax
    cmp %eax, 72(%rsi)
    jne reject
    cmpl $4, 84(%rsi)
    jne reject_rodata_permissions
    cmpq $0, 88(%rsi)
    jne reject
    mov 76(%rsi), %r9d
    test %r9d, %r9d
    jz reject
    mov 80(%rsi), %eax
    cmp %r9d, %eax
    jb reject
    cmp $4096, %eax
    ja reject
    sub %r9d, %edx
payload_checked:
    test %edx, %edx
    jne reject
    lea 0x5000(%r11), %rdi
    add %r8, %rsi
    rep movsb
    lea 0x7000(%r11), %rcx
    sub %rdi, %rcx
    xor %eax, %eax
    rep stosb
    # The old stack page becomes the second immutable code page.
    lea 0x6005(%r11), %rax
    mov %rax, 0x4008(%r11)
    lea 0x8007(%r11), %rax
    bts $63, %rax
    mov %rax, 0x4010(%r11)
    lea 0x8000(%r11), %rdi
    xor %eax, %eax
    mov $512, %ecx
    rep stosq
    test %r9d, %r9d
    jz exit
    lea 0x9000(%r11), %rdi
    mov %r9d, %ecx
    rep movsb
    mov $4096, %ecx
    sub %r9d, %ecx
    rep stosb
    lea 0x9005(%r11), %rax
    bts $63, %rax
    mov %rax, 0x4018(%r11)
    jmp exit
reject_rodata_permissions:
    movl $84, 0x350(%r10)
    jmp reject
reject_permissions:
    movl $52, 0x350(%r10)
reject:
    xor %r12d, %r12d
    mov %rbp, %rdi
    hlt
exit:
    # The packet builder appends the jump to the ABI fixture's GDT setup.
