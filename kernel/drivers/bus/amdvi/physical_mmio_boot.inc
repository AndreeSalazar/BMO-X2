# Readback/restore rehearsal on the measured AMD board. The caller holds
# a live UC supervisor alias in RDI and the post-EBS probe status in EBX.
# This code gets its own page, separate from the GOP and xHCI stages.
#include "../../GPU/NVIDIA/gsp_layout.inc"
.globl amdvi_physical_mmio_begin
amdvi_physical_mmio_begin:
.Lphysical_mmio_begin:
#ifdef BMO_AMDVI_PHYSICAL_USB_TEST
    .byte 0xe9
    .long .Lmmio_boot_entry - . - 4
    .byte 0xe9
    .long .Lphysical_usb_entry - . - 4
    .byte 0xe9
    .long .Lfwsec_domain - . - 4
    .byte 0xe9
    .long .Lphysical_rtx_report - . - 4
.Lmmio_boot_entry:
#endif
    cmp $4, %ebx
    jne .Lmmio_boot_done
    mov $0xfd500000, %eax
    cmp %rax, AMDVI_POST_BASE(%rbp)
    jne .Lmmio_boot_done
    cmpq $1, GSP_PHYSICAL_DTE_STATUS(%rbp)
    jne .Lmmio_boot_done
    cmpl $GSP_POST_FWSEC_READY, GSP_POST_STATUS(%rbp)
    jne .Lmmio_boot_done
    movq $0x100, GSP_PHYSICAL_MMIO_RESULT(%rbp) # Attempted, rejected before publication.
    mov %rsp, %rax
    and $-16, %rsp
    sub $112, %rsp
    mov %rax, 104(%rsp)
    lea 32(%rsp), %rdx
    mov GSP_PHYSICAL_DTE_BASE(%rbp), %rax
    mov %rax, (%rdx)
    lea 0x204000(%rax), %rcx
    mov %rcx, 8(%rdx)
    add $4096, %rcx
    mov %rcx, 16(%rdx)
    movq $0, 48(%rdx)
    # The post-EBS probe has already validated these two MMIO pages.
    # Make the temporary leaves writable only for the transaction.
    orq $2, 0x1e000(%rbp)
    orq $2, 0x1e010(%rbp)
    invlpg (%rdi)
    invlpg 0x2000(%rdi)
    mov %rdi, %rcx
    call .Lstage_physical_registers
    cmp $1, %eax
    jne .Lmmio_boot_record
    mov %rdi, %rcx
    lea 32(%rsp), %rdx
    call .Lrestore_physical_registers
    cmp $1, %eax
    je .Lmmio_boot_record
    mov $3, %eax
.Lmmio_boot_record:
    or $0x100, %eax
    mov %rax, GSP_PHYSICAL_MMIO_RESULT(%rbp)
    cmp $0x103, %eax
    jne .Lmmio_boot_pack
    mov $5, %ebx                   # Do not authorize writes from a stale snapshot.
.Lmmio_boot_pack:
    # The caller returns its snapshot status to Ring 3. Pack the
    # receipt above the low 32-bit snapshot code.
    shl $32, %rax
    or %rax, %rbx
    andq $-3, 0x1e000(%rbp)
    andq $-3, 0x1e010(%rbp)
    invlpg (%rdi)
    invlpg 0x2000(%rdi)
    mov 104(%rsp), %rsp
.Lmmio_boot_done:
    ret
#include "physical_mmio.S"
#ifdef BMO_AMDVI_PHYSICAL_USB_TEST
.Lphysical_rtx_report:
    cmp $6, %r10
    je .Lphysical_rtx_summary
    cmp $8, %r10
    jne .Lphysical_rtx_sec2
    mov NVIDIA_FALCON_MODE_RECEIPT(%rbp), %rax
    ret
.Lphysical_rtx_sec2:
    cmp $9, %r10
    jne .Lphysical_rtx_exec
    mov NVIDIA_SEC2_STAGE_RECEIPT(%rbp), %rax
    ret
.Lphysical_rtx_exec:
    cmp $10, %r10
    jne .Lphysical_rtx_invalid
    mov NVIDIA_SEC2_EXEC_RECEIPT(%rbp), %rax
    ret
.Lphysical_rtx_invalid:
    mov $257, %eax               # Match the session gate denial receipt.
    ret
.Lphysical_rtx_summary:
    # Preserve stage and preparation. Other fields carry the low byte of
    # USB, LPC and FWSEC. The top bit identifies the experimental receipt.
    mov GSP_STAGE_STATUS(%rbp), %rax
    bts $63, %rax
    movzbl AMDVI_PHYSICAL_USB_RESULT(%rbp), %ecx
    shl $8, %rcx
    or %rcx, %rax
    movzwl (AMDVI_PHYSICAL_USB_RESULT+2)(%rbp), %ecx
    shl $40, %rcx
    or %rcx, %rax
    movzbl AMDVI_PHYSICAL_LPC_STATUS(%rbp), %ecx
    shl $16, %rcx
    or %rcx, %rax
    movzwl NVIDIA_FWSEC_LAUNCH_STATUS(%rbp), %ecx
    test %ecx, %ecx
    jz .Lphysical_rtx_report_done
    and $0xff, %ecx
    or $0x80, %ecx
    shl $24, %rcx
    or %rcx, %rax
.Lphysical_rtx_report_done:
    ret
#include "physical_usb.inc"
#include "fwsec_domain.S"
#define BMO_PHYSICAL_MMIO_IN_STAGE
#include "physical_translation.S"
#endif
.globl amdvi_physical_mmio_end
amdvi_physical_mmio_end:
