# Runs during the boot report's segment-zero PCI inventory. CF8 is saved
# and restored by the caller. CFC is read only.
# Entry: ECX = class register selector. R10D and R11D count display and NVIDIA.
nvidia_pci_observe:
    inc %r10d
    lea -8(%rcx), %eax
    out %eax, %dx
    add $4, %dx
    in %dx, %eax
    sub $4, %dx
    cmp $0x10de, %ax
    jne .Lnvidia_done
    inc %r11d
    cmp $1, %r11d
    jne .Lnvidia_done

    # Keep the first match in BDF order. Preserve the inventory cursor.
    push %rcx
    lea (0x800+report_nvidia_id-report_template)(%rbp), %rdi
    call report_hex32
    mov (%rsp), %eax
    shr $8, %eax
    and $0xffff, %eax
    lea (0x800+report_nvidia_bdf-report_template)(%rbp), %rdi
    call report_hex32
    mov (%rsp), %eax
    sub $4, %eax
    mov $0xcf8, %dx
    out %eax, %dx
    add $4, %dx
    xor %eax, %eax
    in %dx, %ax
    lea (0x800+report_nvidia_cmd-report_template)(%rbp), %rdi
    call report_hex32
    mov $0xcf8, %dx
    pop %rcx
.Lnvidia_done:
    ret

nvidia_pci_summary:
    lea (0x800+report_gpu_display-report_template)(%rbp), %rdi
    mov %r10d, %eax
    call report_hex32
    lea (0x800+report_nvidia_count-report_template)(%rbp), %rdi
    mov %r11d, %eax
    jmp report_hex32

    .macro nvidia_pci_report_fields
    .ascii "GPU_PROBE=PCI_RO\r\nGPU_DISPLAY_COUNT="
report_gpu_display:
    .ascii "00000000\r\nGPU_NVIDIA_COUNT="
report_nvidia_count:
    .ascii "00000000\r\nGPU_NVIDIA_BDF="
report_nvidia_bdf:
    .ascii "--------\r\nGPU_NVIDIA_ID="
report_nvidia_id:
    .ascii "--------\r\nGPU_NVIDIA_CMD="
report_nvidia_cmd:
    .ascii "--------\r\n"
    .endm
