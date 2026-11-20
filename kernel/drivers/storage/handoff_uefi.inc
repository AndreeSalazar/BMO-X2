# Discover AHCI and NVMe via EFI PCI I/O. Only accept assigned memory
# resources whose host and PCI addresses agree. No device register writes.
storage_discover:
    push %rbx
    push %rsi
    push %rdi
    push %r12
    push %r13
    push %r14
    push %r15
    sub $128, %rsp
    mov 0x60(%rcx), %r14
    movl $-1, (STORAGE_HEADER+4)(%rbp)
    movq $0, 56(%rsp)
    mov $2, %ecx
    lea .Lstorage_pci_io(%rip), %rdx
    xor %r8d, %r8d
    lea 48(%rsp), %r9
    lea 56(%rsp), %rax
    mov %rax, 32(%rsp)
    call *0x138(%r14)            # LocateHandleBuffer
    test %rax, %rax
    js .Lstorage_handles_done
    mov 56(%rsp), %rsi
    test %rsi, %rsi
    jz .Lstorage_handles_done
    mov 48(%rsp), %rdi
    cmp $4096, %rdi
    ja .Lstorage_handles_done
    movl $0, (STORAGE_HEADER+4)(%rbp)
.Lstorage_handle:
    test %rdi, %rdi
    jz .Lstorage_handles_done
    mov (%rsi), %rcx
    add $8, %rsi
    dec %rdi
    lea .Lstorage_pci_io(%rip), %rdx
    lea 64(%rsp), %r8
    call *0x98(%r14)             # HandleProtocol
    test %rax, %rax
    js .Lstorage_handle
    mov 64(%rsp), %r15
    test %r15, %r15
    jz .Lstorage_handle
    mov %r15, %rcx
    mov $2, %edx
    xor %r8d, %r8d
    mov $3, %r9d
    lea 104(%rsp), %rax
    mov %rax, 32(%rsp)
    call *0x30(%r15)             # Pci.Read ID, command and class
    test %rax, %rax
    js .Lstorage_handle
    mov 112(%rsp), %ebx
    shr $8, %ebx
    xor %r13d, %r13d
    cmp $0x010802, %ebx
    je .Lstorage_location
    cmp $0x010601, %ebx
    jne .Lstorage_handle
    mov $5, %r13d
.Lstorage_location:
    mov %r15, %rcx
    lea 72(%rsp), %rdx
    lea 80(%rsp), %r8
    lea 88(%rsp), %r9
    lea 96(%rsp), %rax
    mov %rax, 32(%rsp)
    call *0x70(%r15)             # GetLocation
    test %rax, %rax
    js .Lstorage_handle
    cmpq $0, 72(%rsp)
    jne .Lstorage_handle
    cmpq $255, 80(%rsp)
    ja .Lstorage_handle
    cmpq $31, 88(%rsp)
    ja .Lstorage_handle
    cmpq $7, 96(%rsp)
    ja .Lstorage_handle
    incl (STORAGE_HEADER+4)(%rbp)
    mov STORAGE_HEADER(%rbp), %eax
    cmp $STORAGE_LIMIT, %eax
    jae .Lstorage_handle
    imul $STORAGE_ROW_BYTES, %eax, %eax
    lea STORAGE_ROWS(%rbp,%rax), %r12
    incl STORAGE_HEADER(%rbp)
    mov 80(%rsp), %eax
    shl $8, %eax
    mov 88(%rsp), %edx
    lea (%rax,%rdx,8), %eax
    add 96(%rsp), %eax
    mov %ax, STORAGE_BDF(%r12)
    mov 108(%rsp), %ax
    mov %ax, STORAGE_COMMAND_PRE(%r12)
    mov %ebx, STORAGE_CLASS(%r12)
    mov 104(%rsp), %eax
    mov %eax, STORAGE_ID(%r12)
    movq $0, 120(%rsp)
    mov %r15, %rcx
    mov %r13d, %edx
    xor %r8d, %r8d
    lea 120(%rsp), %r9
    call *0x80(%r15)             # GetBarAttributes
    test %rax, %rax
    js .Lstorage_free_bar
    mov 120(%rsp), %rax
    test %rax, %rax
    jz .Lstorage_handle
    cmpb $0x8a, (%rax)
    jne .Lstorage_free_bar
    cmpw $43, 1(%rax)
    jne .Lstorage_free_bar
    cmpb $0, 3(%rax)
    jne .Lstorage_free_bar
    cmpq $0, 30(%rax)
    jne .Lstorage_free_bar
    mov 14(%rax), %rdx
    mov 38(%rax), %rcx
    cmp $0x10000000, %rdx
    jb .Lstorage_free_bar
    test $15, %edx
    jnz .Lstorage_free_bar
    cmp $0x20, %rcx
    jb .Lstorage_free_bar
    lea -1(%rdx,%rcx), %rax
    cmp %rdx, %rax
    jb .Lstorage_free_bar
    shr $52, %rax
    jnz .Lstorage_free_bar
    mov %rdx, STORAGE_BAR(%r12)
    mov %rcx, STORAGE_BAR_BYTES(%r12)
    movw $1, STORAGE_STATUS(%r12)
.Lstorage_free_bar:
    mov 120(%rsp), %rcx
    test %rcx, %rcx
    jz .Lstorage_handle
    call *0x48(%r14)
    jmp .Lstorage_handle
.Lstorage_handles_done:
    mov 56(%rsp), %rcx
    test %rcx, %rcx
    jz .Lstorage_discovered
    call *0x48(%r14)
.Lstorage_discovered:
    add $128, %rsp
    pop %r15
    pop %r14
    pop %r13
    pop %r12
    pop %rdi
    pop %rsi
    pop %rbx
    ret

.p2align 2
.Lstorage_pci_io:
    .long 0x4cf5b200
    .short 0x68b8, 0x4ca5
    .byte 0x9e, 0xec, 0xb2, 0x3e, 0x3f, 0x50, 0x02, 0x9a
