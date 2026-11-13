# QEMU qemu-xhci only. No device slots, transfers or interrupts are enabled.
.text
xhci_test_command:
    cmpb $1, %gs:0x378
    jne command_skip
    mov %gs:0x360, %ecx
    shl $8, %ecx
    or $0x80000000, %ecx
    mov $0xcf8, %edx
    in %dx, %eax
    push %rax
    mov %ecx, %eax
    out %eax, %dx
    add $4, %edx
    in %dx, %eax
    cmp $0x000d1b36, %eax
    jne command_restore
    mov 0xb8(%rbp), %r8
    cmpq $5, 0xc0(%rbp)
    jne command_restore
    cmp $0x100000, %r8
    jb command_restore
    cmp $0x0fffb000, %r8
    ja command_restore
    test $0xfff, %r8d
    jnz command_restore
    cmpl $0x1000, 0x18(%rdi)
    jne command_restore
    cmpl $0x2000, 0x14(%rdi)
    jne command_restore
    mov 8(%rdi), %eax
    test $0xffe00000, %eax
    jnz command_restore
    push %rcx
    mov 0x1e000(%rbp), %rax
    or $2, %rax
    mov %rax, 0x1e000(%rbp)
    add $4096, %rax
    mov %rax, 0x1e008(%rbp)
    add $4096, %rax
    mov %rax, 0x1e010(%rbp)
    invlpg (%rdi)
    lea 0x1000(%rdi), %r9
    invlpg (%r9)
    lea 0x2000(%rdi), %r10
    invlpg (%r10)
    movzbl (%rdi), %eax
    lea (%rdi,%rax), %r11
    movl $0, (%r11)
    mov $1, %eax
    mov $1, %esi
    call command_poll
    jne command_unmap
    movl $2, (%r11)
    mov $2, %eax
    xor %esi, %esi
    call command_poll
    jne command_unmap
    mov $0x800, %eax
    call command_poll
    jne command_unmap
    testl $1, 8(%r11)
    jz command_unmap

    # First TRB: No Op Command, cycle 1. Single 16-TRB event segment.
    lea 0x1000(%r8), %rax
    movl $0x5c01, 12(%rax)
    lea 0x2000(%r8), %rcx
    lea 0x3000(%r8), %rdx
    mov %rcx, (%rdx)
    movl $16, 8(%rdx)
    mov %r8, 0x30(%r11)
    or $1, %rax
    mov %rax, 0x18(%r11)
    movl $1, 0x28(%r9)
    mov %rcx, 0x38(%r9)
    mov %rdx, 0x30(%r9)

    # Set PCI Bus Master while preserving its prior command word.
    mov (%rsp), %eax
    or $4, %eax
    mov $0xcf8, %edx
    out %eax, %dx
    add $4, %edx
    in %dx, %ax
    mov %ax, %gs:0x37c
    push %rax
    or $4, %ax
    out %ax, %dx
    movl $1, (%r11)
    mov $1, %eax
    xor %esi, %esi
    call command_poll
    jne command_stop
    movl $0, (%r10)
    mov $100000, %ecx
command_event:
    testb $1, 0x200c(%r8)
    jnz command_received
    pause
    loop command_event
    jmp command_stop
command_received:
    mov 0x200c(%r8), %eax
    and $0xfc00, %eax
    cmp $0x8400, %eax
    jne command_stop
    cmpb $1, 0x200b(%r8)
    jne command_stop
    lea 0x1000(%r8), %rax
    cmp %rax, 0x2000(%r8)
    jne command_stop
    movb $1, %gs:0x379
    lea 0x2018(%r8), %rax
    mov %rax, 0x38(%r9)
command_stop:
    movl $0, (%r11)
    mov $1, %eax
    mov $1, %esi
    call command_poll
    setz %gs:0x37a
    pop %rax
    mov $0xcfc, %edx
    out %ax, %dx
    in %dx, %ax
    mov %ax, %gs:0x37e
command_unmap:
    movq $0, 0x1e008(%rbp)
    movq $0, 0x1e010(%rbp)
    invlpg (%r9)
    invlpg (%r10)
    pop %rcx
command_restore:
    pop %rax
    mov $0xcf8, %edx
    out %eax, %dx
command_skip:
    ret

# Compare the requested mask with zero or the mask itself. ZF reports success.
command_poll:
    neg %esi
    and %eax, %esi
    mov $100000, %ecx
command_poll_next:
    mov 4(%r11), %edx
    test $2, %al
    jz command_poll_compare
    mov (%r11), %edx
command_poll_compare:
    and %eax, %edx
    cmp %esi, %edx
    je command_poll_done
    pause
    loop command_poll_next
command_poll_done:
    ret
