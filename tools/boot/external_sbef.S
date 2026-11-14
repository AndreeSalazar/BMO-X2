.text
# QEMU staging: a qword length followed by the unchanged SBEF.
# R11 is the private page-table reservation, R10 its descriptor page.
.globl external_sbef
external_sbef:
#ifdef DESKTOP_REUSE
.Lreload_entry:
    lea .Lreload_entry(%rip), %rax
    mov %rax, 0x3a0(%r10)
#endif
#ifdef DESKTOP_MEDIA
    mov 0xa8(%rbp), %rsi
    mov 0xb0(%rbp), %rdx
    test %rsi, %rsi
    jz reject
#else
    mov $0x2000000, %esi
    mov (%rsi), %rdx
    add $8, %rsi
#endif
    cmp $64, %rdx
    jb reject
    cmp $16512, %rdx
    ja reject
    movabs $0x0001000146454253, %rax
    cmp %rax, (%rsi)
    jne reject
    mov 8(%rsi), %eax
    cmp $0x1003e, %eax
    je one_region
    cmp $0x2003e, %eax
    je two_regions
    cmp $0x3003e, %eax
    jne reject
    mov $128, %r8d
    jmp header
two_regions:
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
    xor %r14d, %r14d
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
    jb reject
    cmp $128, %r8d
    jne payload_checked
    cmpq $0x40004000, 96(%rsi)
    jne reject
    lea (%rcx,%r8), %rax
    add %r9d, %eax
    cmp %eax, 104(%rsi)
    jne reject
    cmpl $6, 116(%rsi)
    jne reject_data_permissions
    cmpq $0, 120(%rsi)
    jne reject
    mov 108(%rsi), %r14d
    mov 112(%rsi), %eax
    test %eax, %eax
    jz reject
    cmp %r14d, %eax
    jb reject
    cmp $4096, %eax
    ja reject
    sub %r14d, %edx
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
#ifdef DESKTOP_REUSE
    lea 0x5005(%r11), %rax
    mov %rax, 0x4000(%r11)
#endif
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
    cmp $128, %r8d
    jne exit
    lea 0xa000(%r11), %rdi
    mov %r14d, %ecx
    rep movsb
    mov $4096, %ecx
    sub %r14d, %ecx
    xor %eax, %eax
    rep stosb
    lea 0xa007(%r11), %rax
    bts $63, %rax
    mov %rax, 0x4020(%r11)
    jmp exit
reject_data_permissions:
    movl $116, 0x350(%r10)
    jmp reject
reject_rodata_permissions:
    movl $84, 0x350(%r10)
    jmp reject
reject_permissions:
    movl $52, 0x350(%r10)
reject:
    xor %r12d, %r12d
    mov %rbp, %rdi
#ifdef DESKTOP_MEDIA
    lea rejected_message(%rip), %rsi
    call *0x100(%rbp)
stop:
    hlt
    jmp stop
rejected_message:
    .asciz "BMO-X2: SBEF rechazado."
#else
    hlt
#endif
exit:
#ifdef DESKTOP_REUSE
    # First load follows the fixture's GDT setup. The next uses the live GDT.
    cmpb $1, 0x3a8(%r10)
    jne first_entry
    movb $2, 0x3a8(%r10)
    mov $0xc0000080, %ecx
    rdmsr
    or $1, %al
    wrmsr
    mov %r11, %cr3
    pushq $0x1b
    pushq $0x40003000
    pushq $2
    pushq $0x23
    push %r12
    xor %eax, %eax
    xor %ebx, %ebx
    xor %ecx, %ecx
    xor %edx, %edx
    xor %esi, %esi
    xor %edi, %edi
    xor %ebp, %ebp
    xor %r8d, %r8d
    xor %r9d, %r9d
    xor %r10d, %r10d
    xor %r11d, %r11d
    xor %r12d, %r12d
    xor %r13d, %r13d
    xor %r14d, %r14d
    xor %r15d, %r15d
    swapgs
    iretq
first_entry:
#endif
    # The packet builder appends the jump to the ABI fixture's GDT setup.
