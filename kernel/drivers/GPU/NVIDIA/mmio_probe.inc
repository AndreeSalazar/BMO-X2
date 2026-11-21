# UEFI-only PCI I/O. R12D = inventory selector, R13D = raw BAR0.
# Stack has Microsoft x64 outgoing arguments followed by local EFI buffers.
nvidia_mmio_probe:
    push %rbx
    push %rsi
    push %rdi
#ifdef BMO_NVIDIA_GSP_SAMPLE
    sub $176, %rsp
#else
    sub $128, %rsp
#endif
    xor %ebx, %ebx
    movq $0, 56(%rsp)   # HandleBuffer
    movq $0, 104(%rsp)  # Resource descriptor
    test %r12d, %r12d
    jz .Lmmio_finish

    mov $1, %ebx
    mov $2, %ecx       # ByProtocol
    lea .Lpci_io_guid(%rip), %rdx
    xor %r8d, %r8d
    lea 48(%rsp), %r9  # HandleCount
    lea 56(%rsp), %rax
    mov %rax, 32(%rsp)
    call *0x138(%r14)  # LocateHandleBuffer
    test %rax, %rax
    js .Lmmio_finish
    mov 56(%rsp), %rsi
    test %rsi, %rsi
    jz .Lmmio_finish
    mov 48(%rsp), %rdi
    cmp $4096, %rdi
    ja .Lmmio_finish
.Lpci_handle_next:
    test %rdi, %rdi
    jz .Lmmio_finish
    mov (%rsi), %rcx
    add $8, %rsi
    dec %rdi
    lea .Lpci_io_guid(%rip), %rdx
    lea 64(%rsp), %r8
    call *0x98(%r14)   # HandleProtocol
    test %rax, %rax
    js .Lpci_handle_next
    mov 64(%rsp), %rcx
    test %rcx, %rcx
    jz .Lpci_handle_next
    lea 72(%rsp), %rdx
    lea 80(%rsp), %r8
    lea 88(%rsp), %r9
    lea 96(%rsp), %rax
    mov %rax, 32(%rsp)
    call *0x70(%rcx)   # GetLocation
    test %rax, %rax
    js .Lpci_handle_next
    cmpq $0, 72(%rsp)  # Inventory scans segment 0 only.
    jne .Lpci_handle_next
    mov 80(%rsp), %eax
    shl $8, %eax
    mov 88(%rsp), %edx
    lea (%rax,%rdx,8), %eax
    add 96(%rsp), %eax
    mov %r12d, %edx
    shr $8, %edx
    and $0xffff, %edx
    cmp %edx, %eax
    jne .Lpci_handle_next

    mov $2, %ebx
    test $7, %r13d     # Assigned 32-bit memory BAR0.
    jnz .Lmmio_finish
    mov %r13d, %esi
    and $-16, %esi
    jz .Lmmio_finish
    mov 64(%rsp), %rcx
    xor %edx, %edx
    xor %r8d, %r8d
    lea 104(%rsp), %r9
    call *0x80(%rcx)   # GetBarAttributes(0, NULL, &Resources)
    test %rax, %rax
    js .Lmmio_finish
    mov 104(%rsp), %rax
    test %rax, %rax
    jz .Lmmio_finish
    cmpb $0x8a, 0(%rax)
    jne .Lmmio_finish
    cmpw $43, 1(%rax)
    jne .Lmmio_finish
    cmpb $0, 3(%rax)   # Memory descriptor
    jne .Lmmio_finish
    cmp %rsi, 14(%rax)
    jne .Lmmio_finish
    cmpq $0, 30(%rax)  # Require matching host and PCI addresses.
    jne .Lmmio_finish
    mov 38(%rax), %rax
    cmp $4, %rax
    jb .Lmmio_finish
    # Check that the last byte fits the 32-bit aperture.
    lea -1(%rsi,%rax), %rdx
    cmp %rsi, %rdx
    jb .Lmmio_finish
    shr $32, %rdx
    jnz .Lmmio_finish
    lea (BMO_BOOT_REPORT_AREA+report_bar0_len-report_template)(%rbp), %rdi
    call report_hex32

    mov $4, %ebx
    mov 64(%rsp), %rcx
    mov $2, %edx       # Uint32
    xor %r8d, %r8d
    mov $2, %r9d
    lea 112(%rsp), %rax
    mov %rax, 32(%rsp)
    call *0x30(%rcx)   # Pci.Read ID and PCI Command/Status
    test %rax, %rax
    js .Lmmio_finish
    cmpl $0x250410de, 112(%rsp)
    jne .Lmmio_other_gpu
    movzwl 116(%rsp), %eax
    and $6, %eax
    cmp $2, %eax       # Memory decode on, bus mastering off.
    jne .Lmmio_finish

    mov $5, %ebx
    mov 64(%rsp), %rcx
    mov $2, %edx       # Uint32
    xor %r8d, %r8d     # BAR0
    xor %r9d, %r9d     # NV_PMC_BOOT_0 offset
    movq $1, 32(%rsp)
    lea 120(%rsp), %rax
    mov %rax, 40(%rsp)
    call *0x10(%rcx)   # Mem.Read
    test %rax, %rax
    js .Lmmio_finish

    mov $7, %ebx
    mov 64(%rsp), %rcx
    mov $1, %edx       # Uint16
    mov $4, %r8d
    mov $1, %r9d
    lea 124(%rsp), %rax
    mov %rax, 32(%rsp)
    call *0x30(%rcx)
    test %rax, %rax
    js .Lmmio_finish
    mov 124(%rsp), %ax
    cmp 116(%rsp), %ax
    jne .Lmmio_finish

    mov $6, %ebx
    mov 120(%rsp), %eax
    lea (BMO_BOOT_REPORT_AREA+report_pmc_boot0-report_template)(%rbp), %rdi
    call report_hex32
    shr $20, %eax
    and $0x1ff, %eax
    cmp $0x176, %eax   # GA106, excluding zero and PCI/PRIV error patterns.
    jne .Lmmio_finish
    mov $8, %ebx
#ifdef BMO_NVIDIA_GSP_SAMPLE
    # Reuse the PCI I/O handle and preserve the current stack frame.
    jmp .Lgsp_sample
#else
    jmp .Lmmio_finish
#endif
.Lmmio_other_gpu:
    mov $3, %ebx       # BAR validated, register access reserved for 10DE:2504.
.Lmmio_finish:
    mov 104(%rsp), %rcx
    test %rcx, %rcx
    jz .Lmmio_free_handles
    call *0x48(%r14)   # FreePool
.Lmmio_free_handles:
    mov 56(%rsp), %rcx
    test %rcx, %rcx
    jz .Lmmio_report
    call *0x48(%r14)
.Lmmio_report:
    mov %ebx, %eax
    lea (BMO_BOOT_REPORT_AREA+report_mmio_status-report_template)(%rbp), %rdi
    call report_hex32
#ifdef BMO_NVIDIA_GSP_SAMPLE
    add $176, %rsp
#else
    add $128, %rsp
#endif
    pop %rdi
    pop %rsi
    pop %rbx
    ret

#ifdef BMO_NVIDIA_GSP_SAMPLE
#include "gsp_sample.inc"
#endif

    .p2align 2
.Lpci_io_guid:
    .long 0x4cf5b200
    .short 0x68b8, 0x4ca5
    .byte 0x9e, 0xec, 0xb2, 0x3e, 0x3f, 0x50, 0x02, 0x9a

    .macro nvidia_mmio_report_fields
    .ascii "GPU_BAR0_LEN="
report_bar0_len:
    .ascii "--------\r\nGPU_MMIO_STATUS="
report_mmio_status:
    .ascii "00000000\r\nGPU_PMC_BOOT0="
report_pmc_boot0:
    .ascii "--------\r\n"
#ifdef BMO_NVIDIA_GSP_SAMPLE
    .ascii "GSP1="
report_gsp_sample:
    .ascii "--------,--------,--------\r\n"
    .ascii "WPR="
report_wpr_sample:
    .ascii "--------,--------,--------,--------,--------,--------,--------,--------\r\n"
#endif
    .endm
