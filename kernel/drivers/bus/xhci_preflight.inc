# Read-only baseline after ExitBootServices, before any reset or DMA setup.
# RDI is the validated one-page MMIO alias. EAX is the capability header.
xhci_preflight:
    movzbl %al, %eax
    lea (%rdi,%rax), %rsi
    mov 4(%rsi), %eax           # USBSTS
    mov 8(%rsi), %ecx           # PAGESIZE
    mov %eax, %gs:0x3d8
    mov %ecx, %gs:0x3dc
    test $0x800, %eax           # CNR
    jnz preflight_busy
    test $1, %ecx              # 4 KiB pages
    jz preflight_pages
    test $1, %al                # HCHalted
    jnz preflight_halted
    mov $4, %eax
    jmp preflight_store
preflight_busy:
    mov $1, %eax
    jmp preflight_store
preflight_pages:
    mov $2, %eax
    jmp preflight_store
preflight_halted:
    mov $3, %eax
preflight_store:
    mov %eax, %gs:0x3e0
    ret
