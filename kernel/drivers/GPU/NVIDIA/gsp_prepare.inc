# Post-EBS, opt-in NVIDIA profile. RBP holds the boot context.
# Publish page-aligned slices only after validating the complete
# LoaderData reservation. Preserve R10-R15 for the CASM continuation.
.Lgsp_prepare_begin:
    cmpl $0, GSP_POST_STATUS(%rbp)
    jne .Lgsp_prepare_done
    cmpl $5, GSP_STAGE_STATUS(%rbp)
    jne .Lgsp_prepare_done
    movl $1, GSP_POST_STATUS(%rbp) # Invalid handoff or memory map.
    cmpq $BMO_GSP_FILE_BYTES, GSP_STAGE_LENGTH(%rbp)
    jne .Lgsp_prepare_done
    mov GSP_STAGE_BASE(%rbp), %r9
    cmp $0x100000, %r9
    jb .Lgsp_prepare_done
    cmp $(0x10000000-GSP_STAGE_PAGES*4096), %r9
    ja .Lgsp_prepare_done
    test $4095, %r9d
    jnz .Lgsp_prepare_done

    mov 0x60(%rbp), %r8
    lea -40(%r8), %rax
    cmp $216, %rax
    ja .Lgsp_prepare_done
    mov 0x50(%rbp), %rcx
    cmp $65536, %rcx
    ja .Lgsp_prepare_done
    lea 0x1000(%rbp), %rdi
.Lgsp_prepare_descriptor:
    cmp %r8, %rcx
    jb .Lgsp_prepare_done
    cmpl $2, (%rdi)
    jne .Lgsp_prepare_next
    mov 8(%rdi), %rax
    cmp %r9, %rax
    ja .Lgsp_prepare_next
    mov %r9, %rdx
    sub %rax, %rdx
    test $4095, %edx
    jnz .Lgsp_prepare_done
    shr $12, %rdx
    add $GSP_STAGE_PAGES, %rdx
    cmp 24(%rdi), %rdx
    jbe .Lgsp_prepare_copy
.Lgsp_prepare_next:
    add %r8, %rdi
    sub %r8, %rcx
    jmp .Lgsp_prepare_descriptor
.Lgsp_prepare_done:
    ret

.Lgsp_prepare_copy:
    # Both slices move toward lower addresses. The signature source
    # follows the firmware source and stays intact during the first copy.
    cld
    mov %r9, %rdi
    lea BMO_GSP_IMAGE_OFFSET(%r9), %rsi
    mov $(BMO_GSP_IMAGE_BYTES/8), %ecx
    rep movsq
    mov %rdi, GSP_POST_SIGNATURE(%rbp)
    lea BMO_GSP_SIGNATURE_OFFSET(%r9), %rsi
    mov $512, %ecx
    rep movsq
    mov $((GSP_STAGE_PAGES*4096-BMO_GSP_IMAGE_BYTES-4096)/8), %ecx
    xor %eax, %eax
    rep stosq
    mov %r9, GSP_POST_IMAGE(%rbp)
    movl $2, GSP_POST_STATUS(%rbp)
    ret
.Lgsp_prepare_end:
