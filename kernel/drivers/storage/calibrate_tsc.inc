# RCX is EFI BootServices. Publish a measured interval only on invariant TSC.
storage_calibrate_tsc:
    push %rbx
    push %rsi
    push %rdi
    sub $32, %rsp
    mov %rcx, %rsi
    mov $0x80000000, %eax
    cpuid
    cmp $0x80000007, %eax
    jb .Lcalibration_done
    mov $0x80000007, %eax
    cpuid
    test $0x100, %edx
    jz .Lcalibration_done
    lfence
    rdtsc
    shl $32, %rdx
    or %rdx, %rax
    mov %rax, %rdi
    lfence
    mov $10000, %ecx
    call *0xf8(%rsi)                 # EFI_BOOT_SERVICES.Stall, microseconds.
    test %rax, %rax
    jnz .Lcalibration_done
    lfence
    rdtsc
    shl $32, %rdx
    or %rdx, %rax
    sub %rdi, %rax
    lea -1000000(%rax), %rdx
    cmp $99000000, %rdx              # 100 MHz to 10 GHz, including oversleep.
    ja .Lcalibration_done
    mov %rax, STORAGE_TSC_10MS(%rbp)
.Lcalibration_done:
    add $32, %rsp
    pop %rdi
    pop %rsi
    pop %rbx
    ret
