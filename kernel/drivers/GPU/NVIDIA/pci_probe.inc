# Runs during the boot report's segment-zero PCI inventory. CF8 is saved
# and restored by the caller. CFC is read only.
# Entry: ECX = class register selector. R10D and R11D count display and NVIDIA.
# R12D and R13D retain the selected class selector and raw BAR0.
nvidia_pci_observe:
    inc %r10d
    lea -8(%rcx), %eax
    out %eax, %dx
    add $4, %dx
    in %dx, %eax
    sub $4, %dx
    cmp $0x10de, %ax
    jne .Lother_display
    inc %r11d
    cmp $1, %r11d
    jne .Lnvidia_done

    # Keep the first match in BDF order. Preserve the inventory cursor.
    push %rcx
    lea (BMO_BOOT_REPORT_AREA+report_nvidia_id-report_template)(%rbp), %rdi
    call report_hex32
    mov (%rsp), %eax
    shr $8, %eax
    and $0xffff, %eax
    lea (BMO_BOOT_REPORT_AREA+report_nvidia_bdf-report_template)(%rbp), %rdi
    call report_hex32
    mov (%rsp), %eax
    sub $4, %eax
    mov $0xcf8, %dx
    out %eax, %dx
    add $4, %dx
    xor %eax, %eax
    in %dx, %ax
    lea (BMO_BOOT_REPORT_AREA+report_nvidia_cmd-report_template)(%rbp), %rdi
    call report_hex32
    mov $0xcf8, %dx
    pop %rcx
    jmp .Lread_resources

.Lother_display:
    cmp $1, %r10d
    jne .Lnvidia_done
.Lread_resources:
    # Prefer the first NVIDIA function over the first display. Only type 0
    # headers have six BAR dwords and a subsystem ID at these offsets.
    lea 4(%rcx), %eax
    call .Lread_config32
    test $0x007f0000, %eax
    jnz .Lnvidia_done

    push %rcx
    push %rsi
    mov %ecx, %esi
    mov %ecx, %r12d
    mov %esi, %eax
    shr $8, %eax
    and $0xffff, %eax
    lea (BMO_BOOT_REPORT_AREA+report_gpu_resource_bdf-report_template)(%rbp), %rdi
    call report_hex32

    lea (BMO_BOOT_REPORT_AREA+report_gpu_bars-report_template)(%rbp), %rdi
    add $8, %esi
.Lread_bar:
    mov %esi, %eax
    call .Lread_config32
    cmp $0x10, %sil
    jne .Lreport_bar
    mov %eax, %r13d
.Lreport_bar:
    call report_hex32
    inc %rdi
    add $4, %esi
    cmp $0x28, %sil
    jb .Lread_bar

    lea 4(%rsi), %eax
    call .Lread_config32
    lea (BMO_BOOT_REPORT_AREA+report_gpu_subsys-report_template)(%rbp), %rdi
    call report_hex32
    mov $0xcf8, %dx
    pop %rsi
    pop %rcx
.Lnvidia_done:
    ret

.Lread_config32:
    mov $0xcf8, %dx
    out %eax, %dx
    add $4, %dx
    in %dx, %eax
    sub $4, %dx
    ret

nvidia_pci_summary:
    lea (BMO_BOOT_REPORT_AREA+report_gpu_display-report_template)(%rbp), %rdi
    mov %r10d, %eax
    call report_hex32
    lea (BMO_BOOT_REPORT_AREA+report_nvidia_count-report_template)(%rbp), %rdi
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
    .ascii "--------\r\nGPU_RES_BDF="
report_gpu_resource_bdf:
    .ascii "--------\r\nGPU_BARS="
report_gpu_bars:
    .ascii "--------,--------,--------,--------,--------,--------\r\nGPU_SUBSYS="
report_gpu_subsys:
    .ascii "--------\r\n"
    .endm
