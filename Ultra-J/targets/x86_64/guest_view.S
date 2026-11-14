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

# UJBC v1/v2. The only result visible to the panel is the Button event,
# returned after the complete program has passed validation.
run_action:
    lea action(%rip), %rsi
    lea action_end(%rip), %rdi
    lea 9(%rsi), %rax
    cmp %rdi, %rax
    ja invalid
    cmpl $0x43424a55, (%rsi)
    jne invalid
    movzbl 4(%rsi), %r11d
    lea -1(%r11), %eax
    cmp $1, %eax
    ja invalid
    cmpb $0, 5(%rsi)
    jne invalid
    movzwl 6(%rsi), %eax
    add $8, %rsi
    add %rsi, %rax
    cmp %rdi, %rax
    jne invalid
    xor %r8d, %r8d             # Active region ID.
    xor %r9d, %r9d             # Bytes used in the current region.
    xor %r10d, %r10d           # Button event result.
    lea arena(%rip), %rdx
action_next:
    cmp %rdi, %rsi
    jae invalid
    lodsb
    cmp $0xff, %al
    je action_return
    cmp %rdi, %rsi
    jae invalid
    movzbl (%rsi), %ecx
    inc %rsi
    cmp $0x10, %al
    je action_open
    test %r8d, %r8d
    jz invalid
    cmp $0x20, %al
    je action_new
    cmp $0x30, %al
    je action_close
    cmp $0x40, %al
    jne invalid
    cmp $2, %r11d
    jne invalid
    cmp %rdi, %rsi
    jae invalid
    xor %eax, %eax
action_find_receiver:
    cmp %r9d, %eax
    jae invalid
    test %ecx, %ecx
    jz action_call
    cmpb $1, (%rdx,%rax)
    lea 16(%rax), %rax
    jne action_skip_window
    add $16, %eax
action_skip_window:
    dec %ecx
    jmp action_find_receiver
action_call:
    movzbl (%rsi), %ecx
    inc %rsi
    cmp %cl, (%rdx,%rax)       # The v2 method ID matches its class.
    jne invalid
    movb $1, 1(%rdx,%rax)
    cmp $2, %ecx
    jne action_next
    movzbl 1(%rdx,%rax), %r10d
    jmp action_next
action_open:
    test %r8d, %r8d
    jnz invalid
    test %ecx, %ecx
    jz invalid
    mov %ecx, %r8d
    jmp action_next
action_new:
    lea -1(%rcx), %eax
    cmp $1, %eax
    ja invalid
    # Window uses 32 bytes and Button uses 16.
    cmp $1, %ecx
    mov $32, %eax
    je action_size_known
    mov $16, %eax
action_size_known:
    add %r9d, %eax
    cmp $256, %eax
    ja invalid
    mov %cl, (%rdx,%r9)
    mov %eax, %r9d
    jmp action_next
action_close:
    cmp %r8d, %ecx
    jne invalid
    push %rdi
    lea arena(%rip), %rdi
    mov %r9d, %ecx
    shr $3, %ecx
    xor %eax, %eax
    rep stosq
    pop %rdi
    xor %r8d, %r8d
    xor %r9d, %r9d
    jmp action_next
action_return:
    test %r8d, %r8d
    jnz invalid
    cmp %rdi, %rsi
    jne invalid
    mov %r10d, %eax
    ret
invalid:
    ud2

.section .rodata
view:
    .incbin UJ_VIEW_FILE
view_end:
action:
    .incbin UJ_ACTION_FILE
action_end:

.data
    .long 0x49564a55
.bss
    .balign 8
arena:
    .zero 256
.section .note.GNU-stack,"",@progbits
