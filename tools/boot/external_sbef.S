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
    cmp $4160, %rdx
    ja reject
    movabs $0x0001000146454253, %rax
    cmp %rax, (%rsi)
    jne reject
    cmpl $0x1003e, 8(%rsi)
    jne reject
    cmp %edx, 12(%rsi)
    jne reject
    cmpq $0, 24(%rsi)
    jne reject
    cmpq $0x40000000, 32(%rsi)
    jne reject
    cmpl $64, 40(%rsi)
    jne reject
    cmpl $5, 52(%rsi)
    jne reject
    cmpq $0, 56(%rsi)
    jne reject
    sub $64, %edx
    mov 44(%rsi), %ecx
    test %ecx, %ecx
    jz reject
    cmp %ecx, %edx
    jne reject
    mov 48(%rsi), %eax
    cmp %ecx, %eax
    jb reject
    cmp $4096, %eax
    ja reject
    mov 16(%rsi), %r12
    mov %r12, %rax
    sub $0x40000000, %rax
    cmp %rcx, %rax
    jae reject
    lea 0x5000(%r11), %rdi
    add $64, %rsi
    rep movsb
    jmp exit
reject:
    xor %r12d, %r12d
    mov %rbp, %rdi
    hlt
exit:
    # The packet builder appends the jump to the ABI fixture's GDT setup.
