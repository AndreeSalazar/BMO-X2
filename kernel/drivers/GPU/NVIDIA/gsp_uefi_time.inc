# RCX = EFI_SYSTEM_TABLE, RBP = supervisor context.
# Save the clock while UEFI still owns the platform.
nvidia_gsp_read_uefi_time:
    movq $0, GSP_UEFI_TIME_NS(%rbp)
    movq $0, GSP_UEFI_TIME_TSC(%rbp)
    mov 0x58(%rcx), %rax            # EFI_SYSTEM_TABLE.RuntimeServices.
    test %rax, %rax
    jz .Lgsp_uefi_time_return
    mov 0x18(%rax), %rax            # EFI_RUNTIME_SERVICES.GetTime.
    test %rax, %rax
    jz .Lgsp_uefi_time_return
    sub $56, %rsp
    lea 32(%rsp), %rcx
    xor %edx, %edx
    call *%rax
    test %rax, %rax
    jnz .Lgsp_uefi_time_done
    lea 32(%rsp), %rcx
    call .Lgsp_efi_time_to_ns
    test %rax, %rax
    jz .Lgsp_uefi_time_done
    mov %rax, GSP_UEFI_TIME_NS(%rbp)
    lfence
    rdtsc
    shl $32, %rdx
    or %rdx, %rax
    mov %rax, GSP_UEFI_TIME_TSC(%rbp)
.Lgsp_uefi_time_done:
    add $56, %rsp
.Lgsp_uefi_time_return:
    ret

# RCX = EFI_TIME. RAX = epoch nanoseconds, or zero for an invalid sample.
.globl nvidia_gsp_efi_time_to_ns
nvidia_gsp_efi_time_to_ns:
.Lgsp_efi_time_to_ns:
    movzwl (%rcx), %r8d
    sub $2000, %r8d
    cmp $99, %r8d
    ja .Lgsp_efi_time_invalid
    movzbl 2(%rcx), %edx
    dec %edx
    cmp $11, %edx
    ja .Lgsp_efi_time_invalid
    lea .Lgsp_month_days(%rip), %r9
    movzwl (%r9,%rdx,2), %r10d
    movzwl 2(%r9,%rdx,2), %r11d
    sub %r10d, %r11d
    test $3, %r8d
    jnz .Lgsp_efi_time_day
    cmp $1, %edx
    jne .Lgsp_efi_time_after_feb
    inc %r11d
.Lgsp_efi_time_after_feb:
    cmp $2, %edx
    jb .Lgsp_efi_time_day
    inc %r10d
.Lgsp_efi_time_day:
    movzbl 3(%rcx), %edx
    dec %edx
    cmp %r11d, %edx
    jae .Lgsp_efi_time_invalid
    add %edx, %r10d
    imul $365, %r8d, %eax
    add %eax, %r10d
    lea 3(%r8), %eax
    shr $2, %eax
    add %eax, %r10d
    imul $86400, %r10, %rax
    add $946684800, %rax
    movzbl 4(%rcx), %edx
    cmp $23, %edx
    ja .Lgsp_efi_time_invalid
    imul $3600, %edx, %edx
    add %rdx, %rax
    movzbl 5(%rcx), %edx
    cmp $59, %edx
    ja .Lgsp_efi_time_invalid
    imul $60, %edx, %edx
    add %rdx, %rax
    movzbl 6(%rcx), %edx
    cmp $59, %edx
    ja .Lgsp_efi_time_invalid
    add %rdx, %rax
    # If UEFI reports no timezone, use the firmware clock as supplied.
    movswq 12(%rcx), %rdx
    cmp $2047, %edx
    je .Lgsp_efi_time_ns
    cmp $-1440, %edx
    jl .Lgsp_efi_time_invalid
    cmp $1440, %edx
    jg .Lgsp_efi_time_invalid
    imul $60, %rdx, %rdx
    add %rdx, %rax                  # UEFI defines local = UTC - TimeZone.
.Lgsp_efi_time_ns:
    imul $1000000000, %rax, %rax
    mov 8(%rcx), %edx
    cmp $1000000000, %edx
    jae .Lgsp_efi_time_invalid
    add %rdx, %rax
    ret
.Lgsp_efi_time_invalid:
    xor %eax, %eax
    ret
.balign 2
.Lgsp_month_days:
    .short 0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334, 365
