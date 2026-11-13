# QEMU qemu-xhci only. Interrupt delivery remains disabled.
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
    testb $4, 0x10(%rdi)         # 32-byte contexts only
    jnz command_unmap
    movl $1, 0x38(%r11)         # one device slot

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
    call enumerate_keyboard
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

enumerate_keyboard:
    movzbl 7(%rdi), %ecx        # MaxPorts
    cmp $32, %ecx
    ja enum_done
    lea 0x400(%r11), %rsi
    mov $1, %eax
port_next:
    testl $1, (%rsi)
    jnz port_connected
    add $16, %rsi
    inc %eax
    loop port_next
    ret
port_connected:
    mov %al, %gs:0x380
    movl $0x210, (%rsi)        # preserve PP and request port reset
    mov $100000, %ecx
port_wait:
    mov (%rsi), %edx
    and $0x13, %edx
    cmp $3, %edx
    je port_ready
    pause
    loop port_wait
    ret
port_ready:
    mov (%rsi), %edx
    shr $10, %edx
    and $15, %edx
    cmp $3, %edx              # full, low or high speed only
    ja enum_done
    test %edx, %edx
    jz enum_done
    mov %dl, %gs:0x381
    movl $0x2401, 0x101c(%r8)  # Enable Slot
    movl $0, (%r10)
    lea 0x2010(%r8), %rsi
    lea 0x1010(%r8), %rdx
    call enum_event
    jne enum_done
    cmpb $1, 15(%rsi)
    jne enum_done
    movb $1, %gs:0x382
    lea 16(%rsi), %rax
    mov %rax, %gs:0x388

    # Input and device contexts and EP0 transfer ring share page 4.
    lea 0x4400(%r8), %rax
    mov %rax, 8(%r8)
    movl $3, 0x4004(%r8)
    movzbl %gs:0x381, %eax
    shl $20, %eax
    or $0x08000000, %eax
    mov %eax, 0x4020(%r8)
    movzbl %gs:0x380, %eax
    shl $16, %eax
    mov %eax, 0x4024(%r8)
    mov $0x00080026, %eax      # control EP, CErr 3, MPS 8
    cmpb $3, %gs:0x381
    jne ep0_packet
    mov $0x00400026, %eax
ep0_packet:
    mov %eax, 0x4044(%r8)
    lea 0x4801(%r8), %rax
    mov %rax, 0x4048(%r8)
    movl $8, 0x4050(%r8)
    lea 0x4000(%r8), %rax
    mov %rax, 0x1020(%r8)
    movl $0x01002c01, 0x102c(%r8) # Address Device, slot 1
    movl $0, (%r10)
    mov %gs:0x388, %rsi
    lea 0x1020(%r8), %rdx
    call enum_event
    jne enum_done
    cmpb $1, 15(%rsi)
    jne enum_done
    movb $1, %gs:0x383
    call read_device_descriptor
enum_done:
    ret

read_device_descriptor:
    # GET_DESCRIPTOR(Device, 18) via Setup, Data IN and Status OUT.
    movl $0x01000680, 0x4800(%r8)
    movl $0x00120000, 0x4804(%r8)
    movl $8, 0x4808(%r8)
    movl $0x30841, 0x480c(%r8)
    lea 0x4c00(%r8), %rax
    mov %rax, 0x4810(%r8)
    movl $18, 0x4818(%r8)
    movl $0x10c01, 0x481c(%r8)
    movl $0x1021, 0x482c(%r8)
    lea 16(%rsi), %rsi
    lea 0x2100(%r8), %rax
    cmp %rax, %rsi
    jae descriptor_done
    movl $1, 4(%r10)
    mov $100000, %ecx
descriptor_wait:
    testb $1, 12(%rsi)
    jnz descriptor_event
    pause
    loop descriptor_wait
    ret
descriptor_event:
    mov 12(%rsi), %eax
    and $0xfffffc00, %eax
    cmp $0x01018000, %eax    # transfer event, slot 1, endpoint 1
    jne descriptor_done
    cmpl $0x01000000, 8(%rsi)
    jne descriptor_done
    lea 0x4820(%r8), %rax
    cmp %rax, (%rsi)
    jne descriptor_done
    cmpw $0x0112, 0x4c00(%r8)
    jne descriptor_done
    lea 24(%rsi), %rax
    mov %rax, 0x38(%r9)
    movb $1, %gs:0x384
descriptor_done:
    ret

# Find a command completion, allowing intervening port-change events.
enum_event:
    lea 0x2100(%r8), %rax
    mov $100000, %ecx
enum_wait:
    testb $1, 12(%rsi)
    jz enum_pause
    mov 12(%rsi), %eax
    and $0xfc00, %eax
    cmp $0x8800, %eax
    je enum_port_event
    cmp $0x8400, %eax
    jne enum_failed
    cmp %rdx, (%rsi)
    jne enum_failed
    cmpb $1, 11(%rsi)
    jne enum_failed
    lea 24(%rsi), %rax
    mov %rax, 0x38(%r9)
    ret
enum_port_event:
    add $16, %rsi
    lea 0x2100(%r8), %rax
    cmp %rax, %rsi
    jae enum_failed
    lea 8(%rsi), %rax
    mov %rax, 0x38(%r9)
enum_pause:
    pause
    loop enum_wait
enum_failed:
    or $1, %eax
    ret
