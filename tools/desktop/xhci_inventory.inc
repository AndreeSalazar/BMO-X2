# Read PCI class codes only. Preserve the PCI configuration selector.
# One scan per boot, including bridges and multifunction devices.
usb_controllers:
    cmpb $0, %gs:0x35c
    jne inventory_cached
    mov $0xcf8, %edx
    in %dx, %eax
    mov %eax, %r9d
    mov $0x80000008, %ecx
    xor %r8d, %r8d
inventory_next:
    mov %ecx, %eax
    out %eax, %dx
    add $4, %edx
    in %dx, %eax
    sub $4, %edx
    shr $8, %eax
    cmp $0x0c0330, %eax
    jne inventory_advance
    inc %r8d
inventory_advance:
    add $0x100, %ecx
    cmp $0x81000008, %ecx
    jne inventory_next
    mov %r9d, %eax
    out %eax, %dx
    mov %r8d, %gs:0x358
    movb $1, %gs:0x35c
inventory_cached:
    mov %gs:0x358, %eax
    jmp finish
