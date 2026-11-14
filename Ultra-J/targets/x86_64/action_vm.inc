# UJBC v1/v2. The only result visible to the panel is the Button event,
# returned after the complete program has passed validation.
run_action:
    mov $0x40003df8, %esi
    mov (%rsi), %rdi
    lea -9(%rdi), %rax
    cmp $503, %rax
    ja invalid
    add $8, %rsi
    add %rsi, %rdi
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
