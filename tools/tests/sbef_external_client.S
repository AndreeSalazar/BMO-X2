# This guest uses an isolated test gate to demonstrate entry and teardown.
.text
.globl sbef_external_client
sbef_external_client:
    # Verify every region and its first zero-filled dword.
    mov $0x40002000, %ecx
    mov $1, %edx
1:
    cmp %edx, (%rcx)
    jne 2f
    cmpl $0, 4(%rcx)
    jne 2f
    add $8192, %ecx
    inc %edx
    cmp $8, %edx
    jb 1b
    cmpl $0x25121800, 0x4000f000
    jne 2f
    cmpl $0, 0x4000f004
    jne 2f
    # Touch both the mapped stack and a writable data page.
    pushq $7
    pop %rax
    cmp $7, %rax
    jne 2f
    movl $0x11, 0x40004004
    cmpl $0x11, 0x40004004
    jne 2f
    # Use the normal SysV portal for ECHO, invalid capability and WAIT.
    mov $1, %edi
    mov $1, %esi
    movabs $0x89abcdef01234567, %r12
    mov %r12, %rdx
    xor %ecx, %ecx
    xor %r8d, %r8d
    call .Lbmo_invoke
    test %rax, %rax
    jne 2f
    cmp %r12, %rdx
    jne 2f
    xor %edi, %edi
    xor %ecx, %ecx
    call .Lbmo_invoke
    cmp $-2, %rax
    jne 2f
    test %rdx, %rdx
    jne 2f
    mov $1, %edi
    xor %esi, %esi
    mov $37, %edx
    call .Lbmo_wait
    cmp $-4, %rax
    jne 2f
    test %rdx, %rdx
    jne 2f

    mov $2, %eax
    syscall
    cmp $-1, %rax
    jne 2f
    test %rdx, %rdx
    jne 2f
    mov $2, %esi
    xor %ecx, %ecx
    call .Lbmo_invoke
    cmp $-5, %rax
    jne 2f
    test %rdx, %rdx
    jne 2f
    mov $1, %esi
    mov $1, %ecx
    call .Lbmo_invoke
    cmp $-3, %rax
    jne 2f
    test %rdx, %rdx
    jne 2f
    xor %eax, %eax
    xor %r10d, %r10d
    mov $1, %r9d
    syscall
    cmp $-3, %rax
    jne 2f
    test %rdx, %rdx
    jne 2f
#ifdef BMO_EXTERNAL_BAD_STACK
    xor %eax, %eax
    xor %esp, %esp
    syscall
    jmp 2f
#endif
#ifdef BMO_EXTERNAL_FAULT
    movl $0, 0x40002000
#endif
    mov $0x53424546, %eax
    int $0x80
2:
    mov $0xbad, %eax
    int $0x80
    ud2

#define BMO_ABI_PORTAL_ONLY
#include "../../userspace/runtime/abi/sysv/portal.S"
