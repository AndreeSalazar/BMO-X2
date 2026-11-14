.text
.globl _start
_start:
    call validate_action
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

# The panel accepts a single Button action with a local lifetime.
# Check the exact instruction shape before presenting or dispatching.
validate_action:
    cmpq $18, action_size(%rip)
    jne invalid
    lea action(%rip), %rax
    cmpl $0x43424a55, (%rax)
    jne invalid
    cmpl $0x000a0002, 4(%rax)
    jne invalid
    cmpb $0x10, 8(%rax)
    jne invalid
    mov 9(%rax), %cl
    test %cl, %cl
    jz invalid
    cmpl $0x00400220, 10(%rax)
    jne invalid
    cmpw $0x3002, 14(%rax)
    jne invalid
    cmp 16(%rax), %cl
    jne invalid
    cmpb $0xff, 17(%rax)
    jne invalid
    ret

run_action:
    # OPEN/NEW allocate a zeroed Button in the event arena.
    xor %eax, %eax
    mov %rax, button(%rip)
    mov %rax, button+8(%rip)
    movb action+11(%rip), %al
    mov %al, button(%rip)
    # CALL uses receiver zero and writes the instance state.
    cmpb $2, action+14(%rip)
    jne invalid
    movb $1, button+1(%rip)
    mov button+1(%rip), %al
    # CLOSE releases the entire local arena. Copy the event result by value.
    xor %edx, %edx
    mov %rdx, button(%rip)
    mov %rdx, button+8(%rip)
    ret
invalid:
    ud2

.section .rodata
view:
    .incbin UJ_VIEW_FILE
view_end:
action:
    .incbin UJ_ACTION_FILE
action_size:
    .quad action_size - action

.data
    .long 0x49564a55
.bss
    .balign 8
button:
    .zero 16
.section .note.GNU-stack,"",@progbits
