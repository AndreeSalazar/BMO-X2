# Optional FAT32 staging for the exact 615.78.08 GSP container. The
# resident range is EfiLoaderData. This routine only calls EFI file
# and memory services, with no GPU register access or DMA grant.
# The stage profile's report uses 0xc00 until EBS. Its former region
# at 0x800 holds this handoff, away from storage and census rows.
#include "gsp_layout.inc"

nvidia_gsp_stage:
    push %rbx
    sub $64, %rsp
    movl $1, GSP_STAGE_STATUS(%rbp) # File missing or Open failed.
    mov 0x38(%rbp), %rcx
    lea 40(%rsp), %rdx             # EFI_FILE_PROTOCOL*.
    lea .Lgsp_stage_path(%rip), %r8
    mov $1, %r9d                   # EFI_FILE_MODE_READ.
    movq $0, 32(%rsp)
    call *8(%rcx)
    test %rax, %rax
    jnz .Lgsp_stage_done

    mov $2, %ebx                   # Allocation failure.
    movq $0x0fffffff, 48(%rsp)
    mov $1, %ecx                   # AllocateMaxAddress.
    mov $2, %edx                   # EfiLoaderData.
    mov $GSP_STAGE_PAGES, %r8d
    lea 48(%rsp), %r9
    call *0x28(%r14)
    test %rax, %rax
    jnz .Lgsp_stage_close
    mov 48(%rsp), %rax
    mov %rax, GSP_STAGE_BASE(%rbp)
    cmp $0x100000, %rax
    jb .Lgsp_stage_close
    cmp $(0x10000000-GSP_STAGE_PAGES*4096), %rax
    ja .Lgsp_stage_close
    test $4095, %eax
    jnz .Lgsp_stage_close

    mov $3, %ebx                   # Read failed or file length differs.
    movq $(BMO_GSP_FILE_BYTES+1), 56(%rsp)
    mov 40(%rsp), %rcx
    lea 56(%rsp), %rdx
    mov %rax, %r8
    call *0x20(%rcx)
    test %rax, %rax
    jnz .Lgsp_stage_close
    cmpq $BMO_GSP_FILE_BYTES, 56(%rsp)
    jne .Lgsp_stage_close

    mov $4, %ebx                   # Integrity failure.
    mov GSP_STAGE_BASE(%rbp), %rcx
    mov $BMO_GSP_FILE_BYTES, %edx
    lea 32(%rsp), %r8
    call *0x158(%r14)              # CalculateCrc32.
    test %rax, %rax
    jnz .Lgsp_stage_close
    cmpl $BMO_GSP_FILE_CRC, 32(%rsp)
    jne .Lgsp_stage_close
    # Clear the padding before exposing the reserved range in the handoff.
    mov GSP_STAGE_BASE(%rbp), %rcx
    add $BMO_GSP_FILE_BYTES, %rcx
    mov $(GSP_STAGE_PAGES*4096-BMO_GSP_FILE_BYTES), %edx
    xor %r8d, %r8d
    call *0x168(%r14)              # SetMem.
    mov $5, %ebx
.Lgsp_stage_close:
    mov 40(%rsp), %rcx
    call *0x10(%rcx)
    test %rax, %rax
    jz .Lgsp_stage_closed
    mov $3, %ebx
.Lgsp_stage_closed:
    mov %ebx, GSP_STAGE_STATUS(%rbp)
    cmp $5, %ebx
    jne .Lgsp_stage_discard
    movq $BMO_GSP_FILE_BYTES, GSP_STAGE_LENGTH(%rbp)
#ifdef BMO_NVIDIA_GSP_PREPARE
    push %rsi
    push %rdi
    lea .Lgsp_prepare_begin(%rip), %rsi
    lea GSP_POST_CODE(%rbp), %rdi
    mov $(.Lgsp_prepare_end-.Lgsp_prepare_begin), %ecx
    cld
    rep movsb
    pop %rdi
    pop %rsi
#endif
    jmp .Lgsp_stage_done
.Lgsp_stage_discard:
    call nvidia_gsp_release
.Lgsp_stage_done:
    add $64, %rsp
    pop %rbx
    ret

nvidia_gsp_release:
    sub $40, %rsp
    mov GSP_STAGE_BASE(%rbp), %rcx
    test %rcx, %rcx
    jz .Lgsp_stage_released
    mov $GSP_STAGE_PAGES, %edx
    call *0x30(%r14)
    movq $0, GSP_STAGE_BASE(%rbp)
    movq $0, GSP_STAGE_LENGTH(%rbp)
.Lgsp_stage_released:
    add $40, %rsp
    ret

    .p2align 1
.Lgsp_stage_path:
    # \BMO-X2\GPU\GSP.BIN
    .short 92,66,77,79,45,88,50,92,71,80,85,92,71,83,80,46,66,73,78,0

#ifdef BMO_NVIDIA_GSP_PREPARE
#include "gsp_prepare.inc"
#endif
