# USB2 root ports only. RBX is always the selected 64-byte slot state.
native_enumerate_port:
    push %rdi
    movl $110, %gs:0x7ac
    mov %gs:0x778, %eax
    dec %eax
    shl $4, %eax
    lea 0x400(%r11,%rax), %rsi
    testl $1, (%rsi)
    jz native_port_return
    mov (%rsi), %eax
    shr $10, %eax
    and $15, %eax
    dec %eax
    cmp $2, %eax
    ja native_port_return
    mov (%rsi), %eax
    and $0x0e00c3e0, %eax
    or $0x210, %eax
    mov %eax, (%rsi)
    mov $10000000, %ecx
native_port_reset_wait:
    mov (%rsi), %eax
    and $0x13, %eax
    cmp $3, %eax
    je native_port_reset_ready
    pause
    loop native_port_reset_wait
    jmp native_port_return
native_port_reset_ready:
    mov (%rsi), %eax
    shr $10, %eax
    and $15, %eax
    lea -1(%rax), %edx
    cmp $2, %edx
    ja native_port_return
    mov %eax, %gs:0x7c8
    mov $0x10000000, %edi
    call native_settle
    jne native_port_fatal
    movl $111, %gs:0x7ac
    xor %eax, %eax
    mov $0x2400, %ecx
    call native_command
    jne native_port_fatal
    movzbl %gs:0x7bf, %eax
    mov %eax, %edx
    dec %eax
    shl $6, %eax
    lea NATIVE_STATE_BEGIN(%r8,%rax), %rbx
    cmpb $0, NS_SLOT(%rbx)
    jne native_port_fatal
    mov %dl, NS_SLOT(%rbx)
    mov %gs:0x778, %al
    mov %al, NS_PORT(%rbx)
    mov %gs:0x7c8, %al
    mov %al, NS_SPEED(%rbx)
    movzbl NS_SLOT(%rbx), %eax
    dec %eax
    mov %eax, %ecx
    shl $11, %eax
    lea 0x4000(%r8,%rax), %rax
    mov %rax, NS_CONTROL(%rbx)
    mov %ecx, %eax
    shl $13, %eax
    lea 0x6000(%r8,%rax), %rax
    movzbl NS_SLOT(%rbx), %edx
    mov %rax, (%r8,%rdx,8)
    sub $4096, %rax
    mov %rax, %rdi
    movl $3, 4(%rdi)
    mov %gs:0x3c0, %ecx
    add %rcx, %rdi
    movzbl NS_SPEED(%rbx), %eax
    shl $20, %eax
    or $0x08000000, %eax
    mov %eax, (%rdi)
    movzbl NS_PORT(%rbx), %eax
    shl $16, %eax
    mov %eax, 4(%rdi)
    add %rcx, %rdi
    mov $8, %eax
    cmpb $3, NS_SPEED(%rbx)
    jne native_ep0_default
    mov $64, %eax
native_ep0_default:
    shl $16, %eax
    or $0x26, %eax
    mov %eax, 4(%rdi)
    mov NS_CONTROL(%rbx), %rax
    or $1, %al
    mov %rax, 8(%rdi)
    movl $8, 16(%rdi)
    call native_input_address
    test %rax, %rax
    jz native_port_fatal
    movzbl NS_SLOT(%rbx), %ecx
    shl $24, %ecx
    or $0x2c00, %ecx
    movl $112, %gs:0x7ac
    call native_command
    jne native_port_fatal
    mov $0x10000000, %edi
    call native_settle
    jne native_port_fatal
    movl $113, %gs:0x7ac
    mov $0x01000680, %eax
    mov $8, %edx
    call native_control
    jne native_port_drop
    cmpw $0x0112, 0x9500(%r8)
    jne native_port_drop
    movzbl 0x9507(%r8), %eax
    lea -8(%rax), %edx
    cmp $56, %edx
    ja native_port_drop
    lea -1(%rax), %edx
    test %eax, %edx
    jnz native_port_drop
    cmpb $2, NS_SPEED(%rbx)
    jne native_ep0_high_check
    cmp $8, %eax
    jne native_port_drop
native_ep0_high_check:
    cmpb $3, NS_SPEED(%rbx)
    jne native_ep0_evaluate
    cmp $64, %eax
    jne native_port_drop
native_ep0_evaluate:
    mov %eax, %edx
    call native_input_address
    test %rax, %rax
    jz native_port_fatal
    mov %rax, %rdi
    movl $2, 4(%rdi)
    mov %gs:0x3c0, %ecx
    shl $16, %edx
    or $0x26, %edx
    mov %edx, 4(%rdi,%rcx,2)
    movzbl NS_SLOT(%rbx), %ecx
    shl $24, %ecx
    or $0x3400, %ecx
    movl $114, %gs:0x7ac
    call native_command
    jne native_port_drop
    movl $115, %gs:0x7ac
    mov $0x01000680, %eax
    mov $18, %edx
    call native_control
    jne native_port_drop
    cmpw $0x0112, 0x9500(%r8)
    jne native_port_drop
    cmpb $0, 0x9511(%r8)
    je native_port_drop
    movzbl NS_SLOT(%rbx), %eax
    dec %eax
    shl $5, %eax
    lea 0x9700(%r8,%rax), %rdi
    lea 0x9500(%r8), %rsi
    mov $18, %ecx
    rep movsb
    movl $116, %gs:0x7ac
    mov $0x02000680, %eax
    mov $9, %edx
    call native_control
    jne native_port_drop
    cmpw $0x0209, 0x9500(%r8)
    jne native_port_drop
    movzwl 0x9502(%r8), %edx
    lea -9(%rdx), %eax
    cmp $503, %eax
    ja native_port_drop
    mov %edx, %gs:0x7cc
    movl $117, %gs:0x7ac
    mov $0x02000680, %eax
    call native_control
    jne native_port_drop
    mov %gs:0x7cc, %eax
    cmp %ax, 0x9502(%r8)
    jne native_port_drop
    movzbl 0x9505(%r8), %eax
    test %eax, %eax
    jz native_port_drop
    mov %al, NS_CONFIG(%rbx)
    call native_find_hid
    jne native_port_drop
    movl $118, %gs:0x7ac
    movzbl NS_CONFIG(%rbx), %eax
    shl $16, %eax
    or $0x0900, %eax
    xor %edx, %edx
    call native_control
    jne native_port_drop
    movl $119, %gs:0x7ac
    movzbl NS_INTERFACE(%rbx), %eax
    shl $32, %rax
    or $0x0b21, %rax
    cmpb $2, NS_KIND(%rbx)
    jne native_set_protocol
    or $0x10000, %rax       # Mouse uses its declared Report protocol.
native_set_protocol:
    xor %edx, %edx
    call native_control
    jne native_port_drop
    cmpb $2, NS_KIND(%rbx)
    jne native_configure_hid
    movzwl NS_DESCRIPTOR_LEN(%rbx), %edx
    movzbl NS_INTERFACE(%rbx), %eax
    shl $32, %rax
    or $0x22000681, %rax
    call native_control
    jne native_port_drop
    lea 0x9500(%r8), %rsi
    lea 0x9a00(%r8), %rdi
    movzwl NS_DESCRIPTOR_LEN(%rbx), %ecx
    rep movsb
    movzwl NS_DESCRIPTOR_LEN(%rbx), %eax
    mov %eax, %gs:0x7e8
native_configure_hid:
    call native_configure_endpoint
    jne native_port_drop
    movb $1, NS_CONFIGURED(%rbx)
    mov NS_KIND(%rbx), %al
    orb %al, %gs:0x770
    jmp native_port_return
native_port_drop:
    call native_state_valid
    jne native_port_fatal
    movzbl NS_SLOT(%rbx), %ecx
    shl $24, %ecx
    or $0x2800, %ecx
    xor %eax, %eax
    call native_command
    jne native_port_fatal
    # Disable Slot completion is required before reusing its memory.
    call native_input_address
    test %rax, %rax
    jz native_port_fatal
    mov %rax, %rdi
    xor %eax, %eax
    mov $1024, %ecx
    rep stosq
    movzbl NS_SLOT(%rbx), %eax
    dec %eax
    shl $11, %eax
    lea 0x4000(%r8,%rax), %rdi
    xor %eax, %eax
    mov $256, %ecx
    rep stosq
    mov %rbx, %rdi
    mov $8, %ecx
    rep stosq
    jmp native_port_return
native_port_fatal:
    movl $1, %gs:0x7c0
native_port_return:
    pop %rdi
    ret

native_input_address:
    call native_state_valid
    jne native_input_invalid
    movzbl NS_SLOT(%rbx), %eax
    dec %eax
    cmp $1, %eax
    ja native_input_invalid
    shl $13, %eax
    lea 0x5000(%r8,%rax), %rax
    ret
native_input_invalid:
    xor %eax, %eax
    ret

# Bounded descriptor walk; alt 0, HID boot, one input endpoint per slot.
native_find_hid:
    lea 0x9509(%r8), %rsi
    mov %gs:0x7cc, %edx
    sub $9, %edx
    xor %edi, %edi
native_descriptor_next:
    cmp $2, %edx
    jb native_hid_missing
    movzbl (%rsi), %eax
    cmp $2, %eax
    jb native_hid_missing
    cmp %edx, %eax
    ja native_hid_missing
    cmpb $4, 1(%rsi)
    jne native_descriptor_hid
    xor %edi, %edi
    cmp $9, %eax
    jne native_hid_missing
    cmpb $0, 3(%rsi)
    jne native_descriptor_advance
    cmpb $3, 5(%rsi)
    jne native_descriptor_advance
    cmpb $1, 6(%rsi)
    jne native_descriptor_advance
    movzbl 7(%rsi), %ecx
    dec %ecx
    cmp $1, %ecx
    ja native_descriptor_advance
    mov $1, %edi
    shl %cl, %edi
    test %dil, %gs:0x770
    jnz native_hid_skip
    mov %dil, NS_KIND(%rbx)
    mov 2(%rsi), %cl
    mov %cl, NS_INTERFACE(%rbx)
    jmp native_descriptor_advance
native_hid_skip:
    xor %edi, %edi
    jmp native_descriptor_advance
native_descriptor_hid:
    test %edi, %edi
    jz native_descriptor_advance
    cmpb $0x21, 1(%rsi)
    jne native_descriptor_endpoint
    cmp $9, %eax
    jb native_hid_missing
    cmpb $1, 5(%rsi)
    jne native_hid_missing
    cmpb $0x22, 6(%rsi)
    jne native_hid_missing
    cmpw $0, 7(%rsi)
    je native_hid_missing
    movzwl 7(%rsi), %ecx
    cmp $512, %ecx
    ja native_hid_missing
    mov %cx, NS_DESCRIPTOR_LEN(%rbx)
    or $0x100, %edi
    jmp native_descriptor_advance
native_descriptor_endpoint:
    cmpb $5, 1(%rsi)
    jne native_descriptor_advance
    test $0x100, %edi
    jz native_hid_missing
    cmp $7, %eax
    jne native_hid_missing
    movzbl 2(%rsi), %ecx
    and $0xf0, %ecx
    cmp $0x80, %ecx
    jne native_descriptor_advance
    testb $15, 2(%rsi)
    jz native_hid_missing
    mov 3(%rsi), %cl
    and $3, %cl
    cmp $3, %cl
    jne native_descriptor_advance
    movzwl 4(%rsi), %ecx
    cmp $64, %ecx
    ja native_hid_missing
    cmpb $2, NS_SPEED(%rbx)
    jne native_packet_minimum
    cmp $8, %ecx
    ja native_hid_missing
native_packet_minimum:
    movw $8, NS_LENGTH(%rbx)
    cmpb $1, NS_KIND(%rbx)
    je native_packet_check
    movw $1, NS_LENGTH(%rbx)
native_packet_check:
    cmp NS_LENGTH(%rbx), %cx
    jb native_hid_missing
    mov %cx, NS_MPS(%rbx)
    mov 2(%rsi), %cl
    mov %cl, NS_ENDPOINT(%rbx)
    and $15, %ecx
    lea 1(%rcx,%rcx), %ecx
    mov %cl, NS_DCI(%rbx)
    movzbl 6(%rsi), %ecx
    test %ecx, %ecx
    jz native_hid_missing
    cmpb $3, NS_SPEED(%rbx)
    jne native_interval_frames
    dec %ecx
    cmp $15, %ecx
    ja native_hid_missing
    jmp native_interval_done
native_interval_frames:
    bsr %ecx, %ecx
    add $3, %ecx
native_interval_done:
    mov %cl, NS_INTERVAL(%rbx)
    xor %eax, %eax
    ret
native_descriptor_advance:
    add %rax, %rsi
    sub %eax, %edx
    jmp native_descriptor_next
native_hid_missing:
    or $1, %eax
    ret

native_configure_endpoint:
    movl $120, %gs:0x7ac
    call native_input_address
    test %rax, %rax
    jz native_configure_failed
    mov %rax, %rdi
    movzbl NS_DCI(%rbx), %ecx
    mov $1, %edx
    shl %cl, %edx
    or $1, %edx
    mov %edx, 4(%rdi)
    mov %ecx, %edx
    shl $27, %edx
    mov %gs:0x3c0, %ecx
    andl $0x07ffffff, (%rdi,%rcx)
    or %edx, (%rdi,%rcx)
    movzbl NS_DCI(%rbx), %edx
    inc %edx
    imul %ecx, %edx
    add %rdx, %rdi
    movzbl NS_INTERVAL(%rbx), %edx
    shl $16, %edx
    mov %edx, (%rdi)
    movzwl NS_MPS(%rbx), %edx
    shl $16, %edx
    or $0x3e, %edx
    mov %edx, 4(%rdi)
    and $0xffff0000, %edx
    movzwl NS_LENGTH(%rbx), %ecx
    or %ecx, %edx
    mov %edx, 16(%rdi)
    movzbl NS_SLOT(%rbx), %edx
    dec %edx
    mov %edx, %ecx
    shl $9, %edx
    lea 0x9000(%r8,%rdx), %rdx
    mov %rdx, NS_RING(%rbx)
    or $1, %dl
    mov %rdx, 8(%rdi)
    shl $6, %ecx
    lea 0x9400(%r8,%rcx), %rdx
    mov %rdx, NS_BUFFER(%rbx)
    movb $1, NS_CYCLE(%rbx)
    movzbl NS_SLOT(%rbx), %ecx
    shl $24, %ecx
    or $0x3000, %ecx
    call native_command
    ret
native_configure_failed:
    or $1, %eax
    ret
