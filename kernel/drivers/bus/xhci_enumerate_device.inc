# First addressed USB2 device, finite diagnostic. No configured HID endpoints.
# Reuse the validated AMD/QEMU transport, dynamic MMIO and reserved DMA pages.
# R8 DMA, R9 interrupter, R10 doorbells, R11 operational, RDI capabilities.
# RSI next unconsumed event. Never reuse a TRB before its completion.
xhci_enumerate_device:
    movl $20, %gs:0x3e0
    movzbl 7(%rdi), %ecx
    lea 0x400(%r11), %rbx
    mov $1, %eax
enum_probe_port:
    testl $1, (%rbx)
    jz enum_probe_next_port
    mov (%rbx), %edx
    shr $10, %edx
    dec %edx
    cmp $2, %edx             # Only default USB2 speed IDs 1..3.
    jbe enum_probe_reset
enum_probe_next_port:
    add $16, %rbx
    inc %eax
    loop enum_probe_port
    ret
enum_probe_reset:
    mov %al, %gs:0x380
    mov (%rbx), %eax
    and $0x0e00c3e0, %eax    # No PED or RW1C echo.
    or $0x210, %eax
    mov %eax, (%rbx)
    mov $10000000, %ecx
enum_probe_reset_wait:
    mov (%rbx), %eax
    and $0x13, %eax
    cmp $3, %eax
    je enum_probe_reset_ready
    pause
    loop enum_probe_reset_wait
    ret
enum_probe_reset_ready:
    mov (%rbx), %eax
    shr $10, %eax
    and $15, %eax
    lea -1(%rax), %edx
    cmp $2, %edx
    ja enum_probe_done
    mov %al, %gs:0x381
    # Allow reset recovery using the already checked real-time sampler.
    push %rsi
    call xhci_transport_ports
    pop %rsi
    jne enum_probe_done
    movl $21, %gs:0x3e0
    lea 0x1010(%r8), %rdx
    movl $0x2401, 12(%rdx)   # Enable Slot.
    call enum_probe_command
    jne enum_probe_done
    movb $1, %gs:0x382
    lea XHCI_OUTPUT_CONTEXT(%r8), %rax
    mov %rax, 8(%r8)
    mov %gs:0x3c0, %ecx
    lea XHCI_INPUT_CONTEXT(%r8,%rcx), %rbx
    movl $3, XHCI_INPUT_CONTEXT+4(%r8)
    movzbl %gs:0x381, %eax
    shl $20, %eax
    or $0x08000000, %eax
    mov %eax, (%rbx)
    movzbl %gs:0x380, %eax
    shl $16, %eax
    mov %eax, 4(%rbx)
    add %rcx, %rbx
    mov $8, %eax
    cmpb $3, %gs:0x381
    jne enum_probe_packet
    mov $64, %eax
enum_probe_packet:
    shl $16, %eax
    or $0x26, %eax
    mov %eax, 4(%rbx)
    lea 0x4801(%r8), %rax
    mov %rax, 8(%rbx)
    movl $8, 16(%rbx)
    lea XHCI_INPUT_CONTEXT(%r8), %rax
    lea 0x1020(%r8), %rdx
    mov %rax, (%rdx)
    movl $0x01002c01, 12(%rdx) # Address Device.
    movl $22, %gs:0x3e0
    call enum_probe_command
    jne enum_probe_done
    movb $1, %gs:0x383
    movl $23, %gs:0x3e0
    lea 0x4800(%r8), %rbx
    mov $8, %ecx
    mov $0x01000680, %eax
    call enum_probe_descriptor
    jne enum_probe_done
    cmpw $0x0112, 0x4c00(%r8)
    jne enum_probe_done
    movzbl 0x4c07(%r8), %eax
    cmp $8, %eax
    je enum_probe_mps
    cmp $16, %eax
    je enum_probe_mps
    cmp $32, %eax
    je enum_probe_mps
    cmp $64, %eax
    jne enum_probe_done
enum_probe_mps:
    cmpb $2, %gs:0x381      # Low speed must use 8; high speed must use 64.
    jne enum_probe_high
    cmp $8, %eax
    jne enum_probe_done
enum_probe_high:
    cmpb $3, %gs:0x381
    jne enum_probe_evaluate
    cmp $64, %eax
    jne enum_probe_done
enum_probe_evaluate:
    movl $24, %gs:0x3e0
    shl $16, %eax
    or $0x26, %eax
    mov %gs:0x3c0, %ecx
    lea XHCI_INPUT_CONTEXT(%r8,%rcx,2), %rbx
    mov %eax, 4(%rbx)
    movl $2, XHCI_INPUT_CONTEXT+4(%r8) # Only EP0 may be evaluated.
    lea XHCI_INPUT_CONTEXT(%r8), %rax
    lea 0x1030(%r8), %rdx
    mov %rax, (%rdx)
    movl $0x01003401, 12(%rdx)
    call enum_probe_command
    jne enum_probe_done
    movl $25, %gs:0x3e0
    lea 0x4830(%r8), %rbx
    mov $18, %ecx
    mov $0x01000680, %eax
    call enum_probe_descriptor
    jne enum_probe_done
    cmpw $0x0112, 0x4c00(%r8)
    jne enum_probe_done
    cmpb $0, 0x4c11(%r8)
    je enum_probe_done
    movb $1, %gs:0x384
    movl $26, %gs:0x3e0
    mov 0x4c00(%r8), %rax
    mov %rax, 0x4e20(%r8)
    mov 0x4c08(%r8), %rax
    mov %rax, 0x4e28(%r8)
    mov 0x4c10(%r8), %ax
    mov %ax, 0x4e30(%r8)
    lea 0x4860(%r8), %rbx
    mov $9, %ecx
    mov $0x02000680, %eax
    call enum_probe_descriptor
    jne enum_probe_done
    cmpw $0x0209, 0x4c00(%r8)
    jne enum_probe_done
    movzwl 0x4c02(%r8), %ecx
    lea -9(%rcx), %eax
    cmp $503, %eax
    ja enum_probe_done
    mov %ecx, %gs:0x38c
    movl $27, %gs:0x3e0
    lea 0x4890(%r8), %rbx
    mov $0x02000680, %eax
    call enum_probe_descriptor
    jne enum_probe_done
    mov %gs:0x38c, %eax
    cmp %ax, 0x4c02(%r8)
    jne enum_probe_done
    movl $28, %gs:0x3e0
enum_probe_done:
    ret

# RBX free control TRBs, EAX request, ECX requested bytes. Exact completion only.
enum_probe_descriptor:
    mov %eax, (%rbx)
    mov %ecx, %eax
    shl $16, %eax
    mov %eax, 4(%rbx)
    movl $8, 8(%rbx)
    movl $0x30841, 12(%rbx)
    lea 0x4c00(%r8), %rax
    mov %rax, 16(%rbx)
    mov %ecx, 24(%rbx)
    movl $0x10c01, 28(%rbx)
    movl $0x1021, 44(%rbx)
    lea 32(%rbx), %rdx
    movl $1, 4(%r10)
    mov $0x01018000, %ebx
    jmp enum_probe_event
enum_probe_command:
    movl $0, (%r10)
    mov $0x8400, %ebx
enum_probe_event:
    mov $10000000, %ecx
enum_probe_wait:
    lea 0x2100(%r8), %rax
    cmp %rax, %rsi
    jae enum_probe_fail
    testb $1, 12(%rsi)
    jz enum_probe_pause
    mov 12(%rsi), %eax
    and $0xfc00, %eax
    cmp $0x8800, %eax
    je enum_probe_port_change
    mov 12(%rsi), %eax
    and $0xfffffc00, %eax
    # Command completions carry slot ID in the upper byte.
    cmp $0x8400, %ebx
    jne enum_probe_compare
    and $0xfc00, %eax
enum_probe_compare:
    cmp %ebx, %eax
    jne enum_probe_fail
    cmpb $1, 11(%rsi)
    jne enum_probe_fail
    cmpb $1, 15(%rsi)      # This profile enables exactly slot 1.
    jne enum_probe_fail
    cmpl $0x8400, %ebx
    je enum_probe_pointer
    cmpl $0x01000000, 8(%rsi) # Exact transfer: no residual length.
    jne enum_probe_fail
enum_probe_pointer:
    cmp %rdx, (%rsi)
    jne enum_probe_fail
    call enum_probe_advance
    xor %eax, %eax
    ret
enum_probe_port_change:
    call enum_probe_advance
enum_probe_pause:
    pause
    loop enum_probe_wait
enum_probe_fail:
    or $1, %eax
    ret
enum_probe_advance:
    add $16, %rsi
    lea 8(%rsi), %rax
    mov %rax, 0x38(%r9)
    ret
