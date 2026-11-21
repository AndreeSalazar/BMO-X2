# Microsoft x64. RDX points to the validated UEFI MMIO probe frame.
# Preserve a separate validity bit because fuse value zero selects v0.
nvidia_fwsec_read_fuse:
    push %rsi
    sub $48, %rsp
    mov %rdx, %rsi
    mov 64(%rsi), %rcx
    mov $2, %edx
    mov $0x2c, %r8d
    mov $1, %r9d
    lea 120(%rsi), %rax
    mov %rax, 32(%rsp)
    call *0x30(%rcx)                  # Subsystem ID of the measured VBIOS.
    test %rax, %rax
    jnz .Lfwsec_fuse_done
    cmpl $0x397d1462, 120(%rsi)
    jne .Lfwsec_fuse_done

    mov 64(%rsi), %rcx
    mov $2, %edx
    xor %r8d, %r8d
    mov $BMO_FWSEC_SIGNATURE_FUSE_MMIO, %r9d
    movq $1, 32(%rsp)
    lea 120(%rsi), %rax
    mov %rax, 40(%rsp)
    call *0x10(%rcx)
    test %rax, %rax
    jnz .Lfwsec_fuse_done

    mov 64(%rsi), %rcx
    mov $1, %edx
    mov $4, %r8d
    mov $1, %r9d
    lea 124(%rsi), %rax
    mov %rax, 32(%rsp)
    call *0x30(%rcx)
    test %rax, %rax
    jnz .Lfwsec_fuse_done
    mov 124(%rsi), %ax
    cmp 116(%rsi), %ax               # No bus master during the probe.
    jne .Lfwsec_fuse_done
    mov 120(%rsi), %eax
    cmp $-1, %eax
    je .Lfwsec_fuse_done
    mov %eax, %edx
    shr $20, %edx
    cmp $0xbad, %edx
    je .Lfwsec_fuse_done
    bts $32, %rax
    mov %rax, GSP_FWSEC_FUSE(%rbp)
.Lfwsec_fuse_done:
    add $48, %rsp
    pop %rsi
    ret
