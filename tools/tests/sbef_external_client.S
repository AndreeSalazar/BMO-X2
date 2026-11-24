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
#ifdef BMO_EXTERNAL_FAULT
    movl $0, 0x40002000
#endif
    mov $0x53424546, %eax
    int $0x80
2:
    mov $0xbad, %eax
    int $0x80
    ud2
