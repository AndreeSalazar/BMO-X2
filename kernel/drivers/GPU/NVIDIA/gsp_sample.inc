# Read the Ampere GSP RISC-V CPUCTL and the GSP/SEC2 Falcon mailbox 0
# through EFI PCI I/O. Entry requires a validated GA106 and BME off.
# GSP1 is printed only after all three reads and the PCI command recheck.
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
    lea 72(%rsp,%rsi,4), %rax
    mov %rax, 40(%rsp)
    call *0x10(%rcx)               # Mem.Read
    test %rax, %rax
    js .Lmmio_finish
    inc %esi
    cmp $3, %esi
    jne .Lgsp_read_next
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
    mov 72(%rsp,%rsi,4), %eax
    call report_hex32
    inc %rdi
    inc %esi
    cmp $3, %esi
    jne .Lgsp_write_next
    jmp .Lmmio_finish
.Lgsp_command_unverified:
    mov $7, %ebx
    jmp .Lmmio_finish

    .p2align 2
.Lgsp_offsets:
    .long 0x111388, 0x110040, 0x840040
