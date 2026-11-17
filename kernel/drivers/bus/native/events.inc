# Startup commands are finite: at most 255 owned TRBs, never reused.
# RAX parameter, ECX command control without Cycle. ZF means CC=Success.
native_command:
    mov %gs:0x760, %edx
    cmp $255, %edx
    jae native_command_failed
    shl $4, %edx
    lea 0x1000(%r8,%rdx), %rdx
    mov %rax, (%rdx)
    movl $0, 8(%rdx)
    mov %rdx, %gs:0x7b0
    movb $33, %gs:0x7b8
    mov %ecx, %eax
    shr $24, %eax
    mov %al, %gs:0x7bc
    movb $0, %gs:0x7bd
    movb $0, %gs:0x7be
    cmp $0x2400, %ecx
    sete %gs:0x7be
    sfence
    or $1, %ecx
    mov %ecx, 12(%rdx)
    incl %gs:0x760
    sfence
    movl $0, (%r10)
    jmp native_event_wait
native_command_failed:
    or $1, %eax
    ret

native_event_wait:
    push %rdi
    mov $10000000, %edi
native_event_next:
    mov %gs:0x3d0, %rsi
    mov 12(%rsi), %eax
    and $1, %eax
    cmp %gs:0x3cb, %al
    jne native_event_pause
    mov 12(%rsi), %eax
    mov %eax, %ecx
    shr $10, %eax
    and $63, %eax
    cmp $34, %eax
    je native_event_port
    cmp %gs:0x7b8, %al
    jne native_event_fail
    test $4, %cl
    jnz native_event_fail
    mov %ecx, %eax
    shr $16, %eax
    and $255, %eax
    cmp %gs:0x7bd, %al
    jne native_event_fail
    shr $24, %ecx
    cmpb $1, %gs:0x7be
    jne native_event_slot
    lea -1(%rcx), %eax
    cmp $1, %eax
    ja native_event_fail
    jmp native_event_pointer
native_event_slot:
    cmp %gs:0x7bc, %cl
    jne native_event_fail
native_event_pointer:
    mov %cl, %gs:0x7bf
    mov %gs:0x7b0, %rax
    cmp %rax, (%rsi)
    jne native_event_fail
    mov 8(%rsi), %eax
    mov %eax, %ecx
    shr $24, %ecx
    mov %cl, %gs:0x7a0
    and $0xffffff, %eax
    mov %eax, %gs:0x7a4
    call native_event_advance
    cmpb $1, %gs:0x7a0
    jne native_event_fail
    cmpl $0, %gs:0x7a4
    jne native_event_fail
    xor %eax, %eax
    pop %rdi
    ret
native_event_port:
    call native_event_advance
native_event_pause:
    pause
    dec %edi
    jnz native_event_next
native_event_fail:
    or $1, %eax
    pop %rdi
    ret

native_event_advance:
    mov %gs:0x3d0, %rax
    add $16, %rax
    lea NATIVE_EVENT_END(%r8), %rdx
    cmp %rdx, %rax
    jb native_event_store
    lea NATIVE_EVENT_BEGIN(%r8), %rax
    xorb $1, %gs:0x3cb
native_event_store:
    mov %rax, %gs:0x3d0
    or $8, %rax
    mov %rax, 0x38(%r9)
    incq %gs:0x780
    ret

# RBX slot state, RAX setup packet, EDX exact IN length (zero for no data).
# The control ring is finite, zeroed and never reused during startup.
native_control:
    push %rax
    call native_state_valid
    pop %rax
    jne native_control_failed
    mov NS_CONTROL(%rbx), %rsi
    mov %rsi, %rcx
    and $0x7ff, %ecx
    cmp $0x700, %ecx
    ja native_control_failed
    mov %rax, (%rsi)
    movl $8, 8(%rsi)
    movl $0x840, 12(%rsi)
    test %edx, %edx
    jz native_control_no_data
    cmp $512, %edx
    ja native_control_failed
    mov %dx, 6(%rsi)
    movl $0x30840, 12(%rsi)
    lea 0x9500(%r8), %rax
    mov %rax, 16(%rsi)
    mov %edx, 24(%rsi)
    movl $0x10c01, 28(%rsi)
    lea 32(%rsi), %rax
    movl $0x1021, 12(%rax)
    jmp native_control_publish
native_control_no_data:
    lea 16(%rsi), %rax
    movl $0x11021, 12(%rax)
native_control_publish:
    lea 16(%rax), %rcx
    mov %rcx, NS_CONTROL(%rbx)
    mov %rax, %gs:0x7b0
    movb $32, %gs:0x7b8
    mov NS_SLOT(%rbx), %al
    mov %al, %gs:0x7bc
    movb $1, %gs:0x7bd
    movb $0, %gs:0x7be
    sfence
    orb $1, 12(%rsi)
    sfence
    movzbl NS_SLOT(%rbx), %eax
    movl $1, (%r10,%rax,4)
    jmp native_event_wait
native_control_failed:
    or $1, %eax
    ret
