.text
.globl _start
_start:
    call run_action
    lea view(%rip), %r12
    cmpl $0x49564a55, (%r12)
    jne invalid
    cmpw $0x0202, 4(%r12)
    jne invalid
    movzwl 6(%r12), %eax
    dec %eax
    cmp $63, %eax
    ja invalid
    lea 12(%r12,%rax,4), %r12
    lea view_end(%rip), %rbp
    lea 2(%r12), %rax
    cmp %rbp, %rax
    ja invalid
    movzwl (%r12), %eax
    imul $6, %eax, %eax
    lea 2(%r12,%rax), %r13
    lea 2(%r13), %rax
    cmp %rbp, %rax
    ja invalid
    movzwl (%r13), %eax
    imul $6, %eax, %eax
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
    # UJVI v2 packs x/y/w/h and a palette index into six bytes.
    mov (%r15), %eax
    movzwl 4(%r15), %ecx
    shl $32, %rcx
    or %rcx, %rax
    mov %eax, %edx
    and $0x3ff, %edx
    mov %eax, %ecx
    shr $10, %ecx
    and $0x1ff, %ecx
    shl $16, %ecx
    or %rcx, %rdx
    mov %eax, %ecx
    shr $19, %ecx
    and $0x3ff, %ecx
    shl $32, %rcx
    or %rcx, %rdx
    shr $29, %rax
    mov %eax, %ecx
    and $0x1ff, %ecx
    shl $48, %rcx
    or %rcx, %rdx
    shr $9, %eax
    movzwl view+6(%rip), %ecx
    cmp %ecx, %eax
    jae invalid
    lea view+8(%rip), %rcx
    mov (%rcx,%rax,4), %r10d
    xor %eax, %eax
    mov $1, %edi
    mov $1, %esi
    syscall
    add $6, %r15
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
    je activate
    cmp $1, %eax
    je reset
    cmp $256, %eax
    jb input
    mov $1, %eax
    mov $2, %edi
    xor %esi, %esi
    mov $100, %edx
    syscall
    jmp input
activate:
    cmp %r13, %r14
    je input
    call run_action
    mov %r12, %r14
    test %al, %al
    cmovne %r13, %r14
    jmp paint
reset:
    cmp %r12, %r14
    je input
    mov %r12, %r14
    jmp paint

#include "action_vm.inc"
invalid:
    ud2

.section .rodata
view:
    .incbin UJ_VIEW_FILE
view_end:

.data
    .long 0x49564a55
.bss
    .balign 8
arena:
    .zero 256
.section .note.GNU-stack,"",@progbits
