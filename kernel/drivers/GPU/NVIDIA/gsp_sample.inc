# Sample GA106 through EFI PCI I/O with BME off. GSP1 retains its three
# registers. WPR records the GFW and MMU permissions and the VRAM limits.
.Lgsp_sample:
    mov 104(%rsp), %rax             # Validated BAR0 descriptor.
    cmpq $0x840044, 38(%rax)
    jb .Lmmio_finish
    xor %esi, %esi
    lea .Lgsp_offsets(%rip), %rdi
.Lgsp_read_next:
    mov 64(%rsp), %rcx
    mov $2, %edx
    xor %r8d, %r8d
    mov (%rdi,%rsi,4), %r9d
    movq $1, 32(%rsp)
    lea 128(%rsp,%rsi,4), %rax
    mov %rax, 40(%rsp)
    call *0x10(%rcx)               # Mem.Read
    test %rax, %rax
    js .Lgsp_check_sample
    inc %esi
    cmp $11, %esi
    jne .Lgsp_read_next
.Lgsp_check_sample:
    cmp $3, %esi
    jb .Lmmio_finish
    mov %esi, 172(%rsp)
    mov 64(%rsp), %rcx
    mov $1, %edx
    mov $4, %r8d
    mov $1, %r9d
    lea 124(%rsp), %rax
    mov %rax, 32(%rsp)
    call *0x30(%rcx)               # Pci.Read Command
    test %rax, %rax
    js .Lgsp_command_unverified
    mov 124(%rsp), %ax
    cmp 116(%rsp), %ax
    jne .Lgsp_command_unverified
    lea (BMO_BOOT_REPORT_AREA+report_gsp_sample-report_template)(%rbp), %rdi
    xor %esi, %esi
.Lgsp_write_next:
    mov 128(%rsp,%rsi,4), %eax
    call report_hex32
    inc %rdi
    inc %esi
    cmp $3, %esi
    jne .Lgsp_write_next
    cmpl $11, 172(%rsp)
    jne .Lmmio_finish
    lea (BMO_BOOT_REPORT_AREA+report_wpr_sample-report_template)(%rbp), %rdi
.Lwpr_write_next:
    mov 128(%rsp,%rsi,4), %eax
    call report_hex32
    inc %rdi
    inc %esi
    cmp $11, %esi
    jne .Lwpr_write_next
    jmp .Lmmio_finish
.Lgsp_command_unverified:
    mov $7, %ebx
    jmp .Lmmio_finish

    .p2align 2
.Lgsp_offsets:
    .long 0x111388, 0x110040, 0x840040
    # GFW privilege/progress, usable FB in MiB, VGA workspace.
    .long 0x118128, 0x118234, 0x1183a4, 0x625f04
    # MMU lock privilege/low/high, then WPR2 high.
    .long 0x1fa7c8, 0x1fa82c, 0x1fa830, 0x1fa828
