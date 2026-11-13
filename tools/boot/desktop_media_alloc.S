.text
# Reserve the context and payload inside the CASM fixture's identity map.
.globl desktop_media_alloc
desktop_media_alloc:
    sub $40, %rsp
    movq $0x0fffffff, 32(%rsp)
    mov $1, %ecx                 # AllocateMaxAddress
    mov $2, %edx                 # EfiLoaderData
    mov $32, %r8d
    lea 32(%rsp), %r9
    call *0x28(%r14)
    test %rax, %rax
    js finish
    mov 32(%rsp), %rbp
    mov %rbp, %rdi
    xor %eax, %eax
    mov $0x4000, %ecx
    rep stosq
    movq $0x0fffffff, 32(%rsp)
    mov $1, %ecx
    mov $1, %edx                 # EfiLoaderCode
    mov $1, %r8d
    lea 32(%rsp), %r9
    call *0x28(%r14)
    test %rax, %rax
    js finish
    mov 32(%rsp), %rax
    mov %rax, 8(%rbp)
    movabs $0x2134364c4154454d, %rax
    mov %rax, (%rbp)
    xor %eax, %eax
finish:
    add $40, %rsp
    ret
