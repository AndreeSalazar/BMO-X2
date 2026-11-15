# Validate each extra MMIO page against the firmware map before writing it.
# PCI apertures may be absent from that map. Any overlap with RAM, firmware
# code, reserved memory or another non-MMIO descriptor rejects the probe.
# EDX: validated register offset. ZF: admissible. Preserve PCI selector ECX.
xhci_transport_mmio:
    push %rcx
    push %rsi
    push %rbx
    mov %gs:0x364, %eax
    xor %ebx, %ebx
    test $4, %al
    jz transport_mmio_base
    mov %gs:0x368, %ebx
    shl $32, %rbx
transport_mmio_base:
    and $-16, %eax
    or %rbx, %rax
    and $-4096, %edx
    add %rdx, %rax
    lea 4096(%rax), %r11
    mov 0x50(%rbp), %rcx
    lea 0x1000(%rbp), %rsi
transport_mmio_descriptor:
    test %rcx, %rcx
    jz transport_mmio_done
    sub 0x60(%rbp), %rcx
    jb transport_mmio_invalid
    mov 8(%rsi), %rbx
    cmp %r11, %rbx
    jae transport_mmio_next
    mov 24(%rsi), %rdx
    shr $52, %rdx
    jnz transport_mmio_invalid
    mov 24(%rsi), %rdx
    shl $12, %rdx
    add %rbx, %rdx
    jc transport_mmio_invalid
    cmp %rax, %rdx
    jbe transport_mmio_next
    cmpl $11, (%rsi)
    jne transport_mmio_invalid
transport_mmio_next:
    add 0x60(%rbp), %rsi
    jmp transport_mmio_descriptor
transport_mmio_invalid:
    or $1, %eax
transport_mmio_done:
    pop %rbx
    pop %rsi
    pop %rcx
    ret
