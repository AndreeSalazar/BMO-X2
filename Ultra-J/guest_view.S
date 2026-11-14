.text
.globl _start
_start:
    lea view(%rip), %r12
    cmpl $0x49564a55, (%r12)
    jne invalid
    cmpw $0x0201, 4(%r12)
    jne invalid
    add $6, %r12
    lea view_end(%rip), %rbp
    movzwl (%r12), %eax
    imul $12, %eax, %eax
    lea 2(%r12,%rax), %r13
    lea 2(%r13), %rax
    cmp %rbp, %rax
    ja invalid
    movzwl (%r13), %eax
    imul $12, %eax, %eax
    lea 2(%r13,%rax), %rax
    cmp %rbp, %rax
    jne invalid
    mov %r12, %r14
paint:
    movzwl (%r14), %ebx
    lea 2(%r14), %r15
rect:
    test %ebx, %ebx
    jz input
    xor %eax, %eax
    mov $1, %edi
    mov $1, %esi
    mov (%r15), %rdx
    mov 8(%r15), %r10d
    syscall
    add $12, %r15
    dec %ebx
    jmp rect
input:
    xor %eax, %eax
    mov $2, %edi
    mov $2, %esi
    xor %edx, %edx
    xor %r10d, %r10d
    syscall
    cmp $0x1c, %eax
    je toggle
    cmp $256, %eax
    jb input
    mov $1, %eax
    mov $2, %edi
    xor %esi, %esi
    mov $100, %edx
    syscall
    jmp input
toggle:
    cmp %r12, %r14
    mov %r12, %r14
    cmove %r13, %r14
    jmp paint
invalid:
    ud2

.section .rodata
view:
    .incbin "panel.ujv"
view_end:

.data
    .long 0x49564a55
.section .note.GNU-stack,"",@progbits
