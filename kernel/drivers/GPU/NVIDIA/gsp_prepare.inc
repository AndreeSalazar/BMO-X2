# Post-EBS, opt-in NVIDIA profile. RBP holds the boot context.
# Publish page-aligned slices only after validating the complete
# LoaderData reservation. Preserve R10-R15 for the CASM continuation.
#include "gsp_layout.inc"

.text
.globl gsp_prepare_begin
gsp_prepare_begin:
#ifdef BMO_NVIDIA_FWSEC
    .byte 0xe9
    .long .Lgsp_prepare_begin - . - 4
    .byte 0xe9
    .long nvidia_fwsec_read_fuse - . - 4
#endif
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
    cmp $(0x10000000-GSP_STAGE_ALLOC_PAGES*4096), %r9
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
    add $GSP_STAGE_ALLOC_PAGES, %rdx
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
    lea BMO_GSP_SIGNATURE_OFFSET(%r9), %rsi
    mov $512, %ecx
    rep movsq
#ifdef BMO_NVIDIA_GSP_BOOT_CHAIN
    # Preserve the signed trailer before recycling the original file space.
    mov %rdi, %r8
#ifdef BMO_NVIDIA_FWSEC
    lea BMO_FWSEC_FILE_OFFSET(%r9), %rsi
    lea GSP_FWSEC_AREA_OFFSET(%r9), %rdi
    mov $(BMO_FWSEC_PAGES*512), %ecx
    rep movsq
#endif
    lea BMO_GSP_BOOT_FILE_OFFSET(%r9), %rsi
    lea GSP_BOOT_AREA_OFFSET(%r9), %rdi
    mov $(BMO_GSP_BOOT_PAGES*512), %ecx
    rep movsq
    xor %eax, %eax
    mov $512, %ecx
    rep stosq                         # WPR page follows the signed chain.
    mov %r8, %rdi
    mov $((GSP_BOOT_AREA_OFFSET-BMO_GSP_IMAGE_BYTES-4096)/8), %ecx
#else
    mov $((GSP_STAGE_PAGES*4096-BMO_GSP_IMAGE_BYTES-4096)/8), %ecx
#endif
    xor %eax, %eax
    rep stosq

    # Pending IOVAs for the detached DMA tree. Neither DTE nor PCI
    # bus mastering is installed here.
    push %r10
    push %r11
    lea GSP_RADIX_OFFSET(%r9), %rdi
    mov $GSP_DMA_FIRST_IOVA, %esi
    mov $(GSP_DMA_FIRST_IOVA+GSP_RADIX_OFFSET), %edx
    mov $GSP_IMAGE_PAGES, %ecx
    mov $(GSP_RADIX_PAGES*4096), %r8d
    call nvidia_gsp_radix3
    pop %r11
    pop %r10
    test %rax, %rax
    jz .Lgsp_prepare_done
    mov %rax, GSP_POST_RADIX3(%rbp)

    mov GSP_STAGE_BASE(%rbp), %r9
    lea GSP_DMA_TABLE_OFFSET(%r9), %rdi
    mov %rdi, GSP_POST_DMA_ROOT(%rbp)
    mov %r9, %rsi
    mov $GSP_DMA_READ_PAGES, %edx
    mov $(GSP_DMA_FIRST_IOVA >> 21), %ecx
    call amdvi_stage_read_only

    mov %r9, GSP_POST_IMAGE(%rbp)
    lea BMO_GSP_IMAGE_BYTES(%r9), %rax
    mov %rax, GSP_POST_SIGNATURE(%rbp)
#ifdef BMO_NVIDIA_GSP_QUEUES
    call nvidia_gsp_init_queues
#endif
#ifdef BMO_NVIDIA_GSP_LIBOS
    call nvidia_gsp_init_libos
#endif
    movl $GSP_POST_READY, GSP_POST_STATUS(%rbp)
#ifdef BMO_NVIDIA_GSP_BOOT_CHAIN
    call nvidia_gsp_map_boot_chain
    call nvidia_gsp_prepare_wpr
#ifdef BMO_NVIDIA_FWSEC
    call nvidia_fwsec_finalize
#endif
#endif
#ifdef BMO_AMDVI_PHYSICAL_PREPARE
    # In this profile the extra 516 pages are at the end of LoaderData.
    # The detached RTX tree is already built above. Leave AMD-Vi disabled.
    cmpq $14, 0xc0(%rbp)
    jne .Lphysical_dte_done
    push %r10
    push %r11
    sub $88, %rsp
    mov GSP_STAGE_BASE(%rbp), %rax
    lea (GSP_STAGE_PAGES*4096)(%rax), %rdx
    mov %rdx, 32(%rsp)
    add $0x200000, %rdx
    mov %rdx, 40(%rsp)
    mov %rax, 48(%rsp)
    movq $(GSP_STAGE_PAGES*4096), 56(%rsp)
    mov GSP_POST_DMA_ROOT(%rbp), %rax
    mov %rax, 64(%rsp)
    mov 0xb8(%rbp), %rax
    mov %rax, 72(%rsp)
    lea 32(%rsp), %rcx
    lea 0x1000(%rbp), %rdx
    mov 0x50(%rbp), %r8
    mov 0x60(%rbp), %r9
    call .Lprepare_from_efi_map
    mov %eax, GSP_PHYSICAL_DTE_STATUS(%rbp)
#ifdef BMO_AMDVI_PHYSICAL_MMIO_TEST
    test %eax, %eax
    jz .Lphysical_dte_discard
    mov 32(%rsp), %rax
    mov %rax, GSP_PHYSICAL_DTE_BASE(%rbp)
.Lphysical_dte_discard:
#endif
    add $88, %rsp
    pop %r11
    pop %r10
.Lphysical_dte_done:
#endif
    ret

#include "gsp_radix3.inc"
#include "../../bus/amdvi/stage_read_only.inc"
#ifdef BMO_NVIDIA_GSP_QUEUES
#include "gsp_queues.inc"
#endif
#ifdef BMO_NVIDIA_GSP_LIBOS
#include "gsp_libos.inc"
#endif
#ifdef BMO_NVIDIA_GSP_BOOT_CHAIN
#include "gsp_boot_chain.inc"
#include "gsp_wpr_prepare.inc"
#ifdef BMO_NVIDIA_FWSEC
#include "gsp_fwsec_fuse.inc"
#include "gsp_fwsec_dma.inc"
#endif
#endif
#ifdef BMO_AMDVI_PHYSICAL_PREPARE
#include "../../bus/amdvi/physical_tables.S"
#endif
.globl gsp_prepare_end
gsp_prepare_end:
