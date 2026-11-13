.text
# Position-independent extension of the inherited EFI reader.
# The original reader has closed its files and saved SimpleFileSystem in RBP+88h.
.globl desktop_media_read
desktop_media_read:
    # The original reader expects the EFI caller's original stack alignment.
    sub $8, %rsp
    .byte 0xe8
    .long 0x800 - 0x2800 - (. - desktop_media_read) - 4
    add $8, %rsp
    test %rax, %rax
    js done

    # Preserve the inherited INICIO.X86 length. Use separate context fields.
    sub $40, %rsp
    xor %ecx, %ecx
    mov $2, %edx
    mov $5, %r8d
    lea 0xa8(%rbp), %r9
    call *0x28(%r14)
    test %rax, %rax
    js failed
    mov 0x88(%rbp), %rcx
    lea 0x38(%rbp), %rdx
    call *8(%rcx)
    test %rax, %rax
    js release
    mov 0x38(%rbp), %rcx
    lea 0x40(%rbp), %rdx
    lea path(%rip), %r8
    mov $1, %r9d
    movq $0, 32(%rsp)
    call *8(%rcx)
    test %rax, %rax
    js release
    movq $16513, 0xb0(%rbp)
    mov 0x40(%rbp), %rcx
    lea 0xb0(%rbp), %rdx
    mov 0xa8(%rbp), %r8
    call *0x20(%rcx)
    test %rax, %rax
    js release
    cmpq $16512, 0xb0(%rbp)
    ja release
    cmpq $64, 0xb0(%rbp)
    jb release
    mov 0x40(%rbp), %rcx
    movq $0, 0x40(%rbp)
    call *0x10(%rcx)
    test %rax, %rax
    js release
    mov 0x38(%rbp), %rcx
    movq $0, 0x38(%rbp)
    call *0x10(%rcx)
    test %rax, %rax
    js release
#ifdef XHCI_COMMAND_PROBE
    # Copy the EFI stage to the page between the packet buffer and page tables.
    .byte 0x48, 0x8d, 0x35
    .long 0x3000 - 0x2800 - (. - desktop_media_read) - 4
    lea 0x12000(%rbp), %rdi
    mov $512, %ecx
    cld
    rep movsq
#endif
    xor %eax, %eax
    jmp finish
release:
    # The inherited error path closes any handles that are still open.
    mov 0xa8(%rbp), %rcx
    mov $5, %edx
    call *0x30(%r14)
failed:
    lea error(%rip), %rbx
    mov $-1, %rax
finish:
    add $40, %rsp
done:
    ret
    # UEFI accepts CHAR16 paths at aligned addresses.
    .p2align 1
path:
    # \BMO-X2\DESKTOP.SBF
    .short 92,66,77,79,45,88,50,92,68,69,83,75,84,79,80,46,83,66,70,0
error:
    .short 66,77,79,45,88,50,58,32,101,114,114,111,114,32,68,69,83,75,84,79,80,46,83,66,70,13,10,0
