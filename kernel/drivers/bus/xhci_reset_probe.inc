# Experimental controller reset. This path does not program slots or DMA.
xhci_reset_probe:
    movzbl %gs:0x378, %eax
    dec %eax
    cmp $1, %eax
    ja reset_probe_handoff
    movq %rdi, %r11
    movzbl %gs:0x370, %eax
    add %rax, %r11
    orq $2, 0x1e000(%rbp)
    invlpg (%rdi)
    call xhci_reset
    setz %gs:0x3e4
    mov %gs:0x370, %eax
    call xhci_preflight
    mov $6, %eax
    mov $7, %ecx
    cmpb $1, %gs:0x3e4
    cmove %ecx, %eax
    jmp reset_probe_status
reset_probe_handoff:
    mov $5, %eax
reset_probe_status:
    mov %eax, %gs:0x3e0
    ret
