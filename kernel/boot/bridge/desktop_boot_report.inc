# Snapshot before ExitBootServices. Failure leaves desktop boot available.
#ifdef BMO_NVIDIA_PCI_PROBE
#include "../../drivers/GPU/NVIDIA/pci_probe.inc"
#include "../../drivers/GPU/NVIDIA/mmio_probe.inc"
#endif
boot_report:
    push %rsi
    push %rdi
#ifdef BMO_NVIDIA_PCI_PROBE
    push %r12
    push %r13
    xor %r12d, %r12d
    xor %r13d, %r13d
#endif
    sub $56, %rsp
    lea report_template(%rip), %rsi
    lea 0x800(%rbp), %rdi
    mov $(report_end-report_template), %ecx
    cld
    rep movsb
    lea (0x800+report_sbef-report_template)(%rbp), %rdi
    mov 0xb0(%rbp), %eax
    call report_hex32
#ifdef RMLUI_MEDIA
    lea (0x800+report_width-report_template)(%rbp), %rdi
    mov 0x20(%rbp), %eax
    call report_hex32
    lea (0x800+report_height-report_template)(%rbp), %rdi
    mov 0x24(%rbp), %eax
    call report_hex32
#endif
    lea (0x800+report_l1-report_template)(%rbp), %rdi
    mov 0xd0(%rbp), %eax
    call report_hex32
    xor %eax, %eax
    in $0x64, %al
    lea (0x800+report_ps2-report_template)(%rbp), %rdi
    call report_hex32
    mov $0xcf8, %dx
    in %dx, %eax
    mov %eax, %r9d
    mov $0x80000008, %ecx
    xor %r8d, %r8d
#ifdef BMO_NVIDIA_PCI_PROBE
    xor %r10d, %r10d
    xor %r11d, %r11d
#endif
report_pci_next:
    mov %ecx, %eax
    out %eax, %dx
    add $4, %dx
    in %dx, %eax
    sub $4, %dx
    shr $8, %eax
#ifdef BMO_NVIDIA_PCI_PROBE
    cmp $0x030000, %eax
    jb report_pci_xhci
    cmp $0x040000, %eax
    jae report_pci_xhci
    call nvidia_pci_observe
    jmp report_pci_advance
report_pci_xhci:
#endif
    cmp $0x0c0330, %eax
    jne report_pci_advance
    cmp $2, %r8d
    jae report_pci_count
    push %rcx
    push %rdx
    lea (0x800+report_pci0-report_template)(%rbp), %rdi
    imul $(report_pci1-report_pci0), %r8d, %eax
    add %rax, %rdi
    mov %ecx, %eax
    shr $8, %eax
    and $0xffff, %eax
    call report_hex32
    inc %rdi
    mov (%rsp), %edx
    mov 8(%rsp), %eax
    sub $8, %eax
    out %eax, %dx
    add $4, %dx
    in %dx, %eax
    call report_hex32
    inc %rdi
    mov (%rsp), %edx
    mov 8(%rsp), %eax
    sub $4, %eax
    out %eax, %dx
    add $4, %dx
    xor %eax, %eax
    in %dx, %ax
    call report_hex32
    inc %rdi
    # Read BAR0 without sizing it or changing PCI Command.
    mov (%rsp), %edx
    mov 8(%rsp), %eax
    add $8, %eax
    out %eax, %dx
    add $4, %dx
    in %dx, %eax
    push %rax
    call report_hex32
    inc %rdi
    pop %rax
    and $7, %eax
    cmp $4, %eax
    jne report_bar_high
    mov (%rsp), %edx
    mov 8(%rsp), %eax
    add $12, %eax
    out %eax, %dx
    add $4, %dx
    in %dx, %eax
    jmp report_bar_store
report_bar_high:
    xor %eax, %eax
report_bar_store:
    call report_hex32
    pop %rdx
    pop %rcx
report_pci_count:
    inc %r8d
report_pci_advance:
    add $0x100, %ecx
    cmp $0x81000008, %ecx
    jne report_pci_next
    mov %r9d, %eax
    out %eax, %dx
    mov %r8d, %eax
    lea (0x800+report_xhci-report_template)(%rbp), %rdi
    call report_hex32
#ifdef BMO_NVIDIA_PCI_PROBE
    call nvidia_pci_summary
    call nvidia_mmio_probe
#ifdef BMO_AMDVI_EFI_OFFSET
    mov 56(%rsp), %rcx              # EFI SystemTable saved above.
    lea (0x800+report_amdvi-report_template)(%rbp), %rdx
    lea report_hex32(%rip), %r8
    .byte 0xe8
    .long BMO_AMDVI_EFI_OFFSET - DESKTOP_READER_OFFSET - (. - desktop_media_read) - 4
#endif
#endif

    mov 0x38(%rbp), %rcx
    lea 40(%rsp), %rdx
    lea report_path(%rip), %r8
    movabs $0x8000000000000003, %r9
    movq $0, 32(%rsp)
    call *8(%rcx)
    test %rax, %rax
    js report_done
    movq $(report_end-report_template), 48(%rsp)
    mov 40(%rsp), %rcx
    lea 48(%rsp), %rdx
    lea 0x800(%rbp), %r8
    call *0x28(%rcx)
    test %rax, %rax
    js report_close
    cmpq $(report_end-report_template), 48(%rsp)
    jne report_close
    mov 40(%rsp), %rcx
    call *0x50(%rcx)
    test %rax, %rax
    js report_close
    movb $1, 0xf0(%rbp)
report_close:
    mov 40(%rsp), %rcx
    call *0x10(%rcx)
report_done:
    add $56, %rsp
#ifdef BMO_NVIDIA_PCI_PROBE
    pop %r13
    pop %r12
#endif
    pop %rdi
    pop %rsi
    ret

report_hex32:
    mov $8, %ecx
report_hex_digit:
    rol $4, %eax
    mov %al, %dl
    and $15, %dl
    add $'0', %dl
    cmp $'9', %dl
    jbe report_hex_store
    add $7, %dl
report_hex_store:
    mov %dl, (%rdi)
    inc %rdi
    loop report_hex_digit
    ret

report_template:
#ifdef RMLUI_MEDIA
    .ascii "BMO-X2 DESKTOP UEFI PRE-EBS\r\nSBEF="
#else
    .ascii "BMO-X2 V3 UEFI\r\nSBEF="
#endif
report_sbef:
#ifdef RMLUI_MEDIA
    .ascii "00000000\r\nGOP_WIDTH="
report_width:
    .ascii "00000000\r\nGOP_HEIGHT="
report_height:
#endif
    .ascii "00000000\r\nCPUID="
report_l1:
    .ascii "00000000\r\nPS2="
report_ps2:
    .ascii "00000000\r\nXHCI="
report_xhci:
    .ascii "00000000\r\nBDF ID CMD BAR0_LO BAR0_HI\r\n"
report_pci0:
    .ascii "-------- -------- -------- -------- --------\r\n"
report_pci1:
    .ascii "-------- -------- -------- -------- --------\r\n"
#ifdef BMO_NVIDIA_PCI_PROBE
    nvidia_pci_report_fields
    nvidia_mmio_report_fields
#ifdef BMO_AMDVI_EFI_OFFSET
    # Packed words: status, IVRS bytes, requester, base register low/high.
    .ascii "AMDVI="
report_amdvi:
    .ascii "-------- -------- -------- -------- --------\r\n"
#endif
#endif
report_end:
#ifdef BMO_NVIDIA_PCI_PROBE
    # The NVIDIA profile owns 0x800..0xaff; native UI does not load ACTION.UJB.
#if defined(ULTRA_J_MEDIA) || !defined(RMLUI_MEDIA)
#error "NVIDIA report requires the dedicated native UI profile"
#endif
    .if (report_end-report_template) > 0x300
    .error "Boot report exceeds context buffer"
    .endif
#endif
    .p2align 1
report_path:
#if defined(BMO_NVIDIA_PCI_PROBE)
    # \BMO-X2\GPU\GPULOG.TXT
    .short 92,66,77,79,45,88,50,92,71,80,85,92,71,80,85,76,79,71,46,84,88,84,0
#elif defined(RMLUI_MEDIA)
    .short 92,66,77,79,45,88,50,92,68,69,83,75,84,79,80,92,66,79,79,84,76,79,71,46,84,88,84,0
#else
    # \\BMO-X2\\BOOTLOG.TXT
    .short 92,66,77,79,45,88,50,92,66,79,79,84,76,79,71,46,84,88,84,0
#endif
