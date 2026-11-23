.text
#if defined(BMO_AMDVI_POST) || defined(BMO_AMDVI_DTE_RESERVE)
#include "post_layout.inc"
#endif
#if defined(BMO_FULL_HD) || defined(BMO_AMDVI_GSP_DMA)
#include "../../display/GOP/gop_layout.inc"
#endif
# Read-only AMD-Vi inventory while UEFI still owns the platform.
# RCX = EFI_SYSTEM_TABLE, RDX = inventory fields, R8 = report_hex32.
# R9 = MMIO snapshot fields.
# The firmware tables are trusted pointers. Bound all walks before use.
.globl amdvi_firmware_probe
amdvi_firmware_probe:
    push %rbx
    push %rsi
    push %rdi
    push %r12
    push %r13
    push %r14
    push %r15
#ifdef BMO_AMDVI_POST
    lea amdvi_post_begin(%rip), %rsi
    lea AMDVI_POST_CODE(%rbp), %rdi
    mov $(amdvi_post_end-amdvi_post_begin), %eax
    # Preserve the four incoming parameters across the copy.
    push %rcx
    mov %eax, %ecx
    cld
    rep movsb
    pop %rcx
#endif
#ifdef BMO_AMDVI_GUEST_NVME
    push %rcx
    lea nvme_guest_begin(%rip), %rsi
    lea AMDVI_GUEST_NVME_CODE(%rbp), %rdi
    mov $(nvme_guest_end-nvme_guest_begin), %ecx
    cld
    rep movsb
    pop %rcx
#endif
#ifdef BMO_AMDVI_PHYSICAL_MMIO_TEST
    push %rcx
    lea .Lphysical_mmio_begin(%rip), %rsi
    lea AMDVI_PHYSICAL_MMIO_CODE(%rbp), %rdi
    mov $(amdvi_physical_mmio_end-amdvi_physical_mmio_begin), %ecx
    cld
    rep movsb
    pop %rcx
#endif
#if defined(BMO_FULL_HD) || defined(BMO_AMDVI_GSP_DMA)
    push %rcx
    lea .Lgop_stage(%rip), %rsi
    lea GOP_CODE_OFFSET(%rbp), %rdi
    mov $(.Lgop_stage_end-.Lgop_stage), %ecx
    cld
    rep movsb
    pop %rcx
#endif
    sub $16, %rsp
    mov %r9, (%rsp)
    mov 0x60(%rcx), %rax
    mov %rax, 8(%rsp)
#ifdef BMO_AMDVI_PHYSICAL_USB_TEST
    push %rcx
    push %rdx
    push %r8
    push %r9
    sub $32, %rsp
    movq $0x0fffffff, NVIDIA_PHYSICAL_CODE_BASE(%rbp)
    mov $1, %ecx                   # AllocateMaxAddress in supervisor identity memory.
    mov $1, %edx                   # EfiLoaderCode.
    mov $2, %r8d
    lea NVIDIA_PHYSICAL_CODE_BASE(%rbp), %r9
    call *0x28(%rax)
    test %rax, %rax
    jnz .Lnvidia_stage_unavailable
    mov NVIDIA_PHYSICAL_CODE_BASE(%rbp), %rdi
    cmp $0x100000, %rdi
    jb .Lnvidia_stage_unavailable
    cmp $0xfffe000, %rdi
    ja .Lnvidia_stage_unavailable
    test $4095, %edi
    jnz .Lnvidia_stage_unavailable
    mov %rdi, %rsi
    xor %eax, %eax
    mov $1024, %ecx
    cld
    rep stosq
    mov %rsi, %rdi
    lea .Lnvidia_physical_begin(%rip), %rsi
    mov $(nvidia_physical_end-nvidia_physical_begin), %ecx
    rep movsb
    jmp .Lnvidia_stage_done
.Lnvidia_stage_unavailable:
    movq $0, NVIDIA_PHYSICAL_CODE_BASE(%rbp)
.Lnvidia_stage_done:
    add $32, %rsp
    pop %r9
    pop %r8
    pop %rdx
    pop %rcx
    mov 8(%rsp), %rax
#endif
#ifdef BMO_AMDVI_DTE_RESERVE
    # QEMU-only preparation: reserve and verify the complete 2 MiB DTE
    # array as EfiLoaderData. No AMD-Vi register or PCI command is touched.
    movq $0, AMDVI_DTE_RESERVE_BASE(%rbp)
    movq $AMDVI_DTE_TABLE_PAGES, AMDVI_DTE_RESERVE_PAGES(%rbp)
    movq $0, AMDVI_DTE_RESERVE_STATUS(%rbp)
    movq $0, AMDVI_DTE_RESERVE_ZERO_QWORDS(%rbp)
    push %rcx
    push %rdx
    push %r8
    push %r9
    sub $32, %rsp
    xor %ecx, %ecx                  # AllocateAnyPages
    mov $2, %edx                    # EfiLoaderData
    mov $AMDVI_DTE_TABLE_PAGES, %r8d
    lea AMDVI_DTE_RESERVE_BASE(%rbp), %r9
    call *0x28(%rax)                # EFI_BOOT_SERVICES.AllocatePages
    add $32, %rsp
    pop %r9
    pop %r8
    pop %rdx
    pop %rcx
    mov %rcx, %r10                  # Preserve SystemTable across REP scans.
    test %rax, %rax
    jnz .Ldte_allocate_failed
    mov AMDVI_DTE_RESERVE_BASE(%rbp), %rdi
    test %rdi, %rdi
    jz .Ldte_verify_failed
    test $0xfff, %edi
    jnz .Ldte_verify_failed
    mov %rdi, %rsi
    xor %eax, %eax
    mov $AMDVI_DTE_TABLE_QWORDS, %ecx
    cld
    rep stosq
    mov %rsi, %rdi
    xor %eax, %eax
    mov $AMDVI_DTE_TABLE_QWORDS, %ecx
    repe scasq
    jne .Ldte_verify_failed
    movq $AMDVI_DTE_TABLE_QWORDS, AMDVI_DTE_RESERVE_ZERO_QWORDS(%rbp)
    movq $1, AMDVI_DTE_RESERVE_STATUS(%rbp)
    jmp .Ldte_done
.Ldte_allocate_failed:
    movq $2, AMDVI_DTE_RESERVE_STATUS(%rbp)
    jmp .Ldte_done
.Ldte_verify_failed:
    movq $3, AMDVI_DTE_RESERVE_STATUS(%rbp)
.Ldte_done:
    mov %r10, %rcx
#endif
#ifdef BMO_STORAGE_QUIESCE_METAL
    push %rcx
    push %rdx
    push %r8
    push %r9
    mov %rax, %rcx
    call storage_calibrate_tsc
    pop %r9
    pop %r8
    pop %rdx
    pop %rcx
#endif
#ifdef BMO_STORAGE_STATE
    push %rcx
    push %rdx
    push %r8
    push %r9
    call storage_discover
    pop %r9
    pop %r8
    pop %rdx
    pop %rcx
#endif
#ifdef BMO_AMDVI_COEXIST
    # Only the virtual coexistence profile reserves Host test memory.
    push %rcx
    push %rdx
    push %r8
    push %r9
    sub $32, %rsp
    movq $0x0fffffff, AMDVI_LAB_SCRATCH(%rbp)
    mov $1, %ecx
    mov $2, %edx
#ifdef BMO_AMDVI_GUEST_DMA
    mov $AMDVI_LAB_PAGES, %r8d
#else
    mov $13, %r8d
#endif
    lea AMDVI_LAB_SCRATCH(%rbp), %r9
    call *0x28(%rax)
    test %rax, %rax
    jns .Lcoexist_reserved
    movq $0, AMDVI_LAB_SCRATCH(%rbp)
.Lcoexist_reserved:
    add $32, %rsp
    pop %r9
    pop %r8
    pop %rdx
    pop %rcx
#endif
    mov %rdx, %r14
    mov %r8, %r15
    mov 0x68(%rcx), %r9
    mov 0x70(%rcx), %rsi
    xor %ebx, %ebx                   # 0: IVRS absent
    test %rsi, %rsi
    jz finish
    cmp $256, %r9
    ja bad_root
    movabs $0x11d3e4f18868e871, %r10
    movabs $0x81883cc7800022bc, %r11
find_rsdp:
    test %r9, %r9
    jz finish
    dec %r9
    add $24, %rsi
    cmp %r10, -24(%rsi)
    jne find_rsdp
    cmp %r11, -16(%rsi)
    jne find_rsdp
    mov -8(%rsi), %rsi
    test %rsi, %rsi
    jz bad_root
    movabs $0x2052545020445352, %rax  # RSD PTR
    cmp %rax, (%rsi)
    jne bad_root
    cmpb $2, 15(%rsi)
    jb bad_root
    mov $20, %ecx
    call checksum
    jnz bad_root
    mov 20(%rsi), %ecx
    cmp $36, %ecx
    jb bad_root
    cmp $4096, %ecx
    ja bad_root
    call checksum
    jnz bad_root
    mov 24(%rsi), %rsi
    test %rsi, %rsi
    jz bad_root
    cmpl $0x54445358, (%rsi)         # XSDT
    jne bad_root
    mov 4(%rsi), %ecx
    cmp $36, %ecx
    jb bad_root
    cmp $65536, %ecx
    ja bad_root
    lea -36(%rcx), %eax
    test $7, %eax
    jnz bad_root
    lea (%rsi,%rcx), %r12
    call checksum
    jnz bad_root
    add $36, %rsi
find_ivrs:
    cmp %r12, %rsi
    je finish
    mov (%rsi), %rax
    add $8, %rsi
    test %rax, %rax
    jz find_ivrs
    cmpl $0x53525649, (%rax)         # IVRS
    jne find_ivrs
    mov %rax, %rsi
    mov 4(%rsi), %ecx
    cmp $48, %ecx
    jb bad_ivrs
    cmp $65536, %ecx
    ja bad_ivrs
    lea (%rsi,%rcx), %r12
    mov %ecx, %r13d
    call checksum
    jnz bad_ivrs
#ifdef BMO_AMDVI_PHYSICAL_USB_TEST
    mov %rsi, %rcx
    mov %r13d, %edx
    call .Lmatches_board_ivrs
    mov %eax, AMDVI_BOARD_IVRS_MATCH(%rbp)
#endif
    mov %r13d, %eax
    lea 9(%r14), %rdi
    call *%r15
    add $48, %rsi
    xor %r13d, %r13d                 # Selected IVHD header.
next_block:
    cmp %r12, %rsi
    je check_unit
    mov %r12, %rax
    sub %rsi, %rax
    cmp $6, %rax
    jb bad_ivrs
    movzwl 2(%rsi), %ecx
    cmp $6, %ecx
    jb bad_ivrs
    cmp %rax, %rcx
    ja bad_ivrs
    movzbl (%rsi), %eax
    mov $24, %edx
    cmp $0x10, %eax
    je check_header
    mov $40, %edx
    cmp $0x11, %eax
    je check_header
    cmp $0x40, %eax
    jne advance
check_header:
    cmp %edx, %ecx
    jb bad_ivrs
    cmpw $0, 16(%rsi)
    jne advance
    test %r13, %r13
    jz select_unit
    mov 4(%r13), %eax
    cmp %eax, 4(%rsi)                # Same requester and capability offset.
    jne ambiguous
    mov 8(%r13), %rax
    cmp %rax, 8(%rsi)
    jne ambiguous
select_unit:
    mov %rsi, %r13
advance:
    add %rcx, %rsi
    jmp next_block

check_unit:
    mov $3, %ebx                    # No unique segment-zero unit.
    test %r13, %r13
    jz finish
    movzwl 4(%r13), %eax
    lea 18(%r14), %rdi
    call *%r15
    movzwl 6(%r13), %r12d
    cmp $0x40, %r12d
    jb bad_cap
    cmp $0xf4, %r12d
    ja bad_cap
    test $3, %r12d
    jnz bad_cap
    movzwl 4(%r13), %r9d
    shl $8, %r9d
    or $0x80000000, %r9d
    mov $0xcf8, %dx
    in %dx, %eax
    mov %eax, %r10d
    xor %ecx, %ecx
    call pci_read
    cmp $0x1022, %ax
    jne restore_bad_cap
    mov %eax, %r11d
    mov %r12d, %ecx
    call pci_read
    cmp $0x0f, %al
    jne restore_bad_cap
    add $4, %ecx
    call pci_read
    mov %eax, %esi
    add $4, %ecx
    call pci_read
    mov %eax, %r12d
    mov %r10d, %eax
    out %eax, %dx
    mov %esi, %eax
    lea 27(%r14), %rdi
    call *%r15
    mov %r12d, %eax
    lea 36(%r14), %rdi
    call *%r15
    mov %esi, %eax
    and $0xffffc000, %eax
    shl $32, %r12
    or %r12, %rax
    mov $5, %ebx                    # PCI and IVRS disagree about MMIO base.
    cmp 8(%r13), %rax
    jne finish
    mov %rax, %r12
    mov $6, %ebx                    # MMIO decode disabled in PCI.
    test $1, %esi
    jz check_tcg
    mov $7, %ebx                    # PCI decode and firmware base agree.
    jmp snapshot
check_tcg:
    # QEMU maps the emulated IOMMU via SysBus with the PCI enable bit clear.
    # Limit this exception to the TCG model and its fixed address.
    cmp $0x14191022, %r11d
    jne finish
    mov $0xfed80000, %eax
    cmp %rax, %r12
    jne finish
    mov $0x40000000, %eax
    cpuid
    cmp $0x54474354, %ebx
    mov $6, %ebx
    jne finish
    cmp $0x43544743, %ecx
    jne finish
    cmp $0x47435447, %edx
    jne finish
snapshot:
    mov 8(%rsp), %rcx
    mov %r12, %rdx
    mov (%rsp), %r8
    mov %r15, %r9
    call amdvi_uefi_snapshot
#ifdef BMO_AMDVI_POST
    cmp $4, %eax
    jne finish
    movzwl 4(%r13), %eax
    shl $8, %eax
    movzwl 6(%r13), %ecx
    lea 4(%rax,%rcx), %eax
    or $0x80000000, %eax
    mov %eax, AMDVI_POST_PCI(%rbp)
    mov %esi, AMDVI_POST_PCI_LOW(%rbp)
    mov %r12, AMDVI_POST_BASE(%rbp)
#endif
    jmp finish
restore_bad_cap:
    mov %r10d, %eax
    out %eax, %dx
bad_cap:
    mov $4, %ebx
    jmp finish
bad_root:
    mov $1, %ebx
    jmp finish
bad_ivrs:
    mov $2, %ebx
    jmp finish
ambiguous:
    mov $3, %ebx
finish:
    mov %ebx, %eax
    mov %r14, %rdi
    call *%r15
    add $16, %rsp
    pop %r15
    pop %r14
    pop %r13
    pop %r12
    pop %rdi
    pop %rsi
    pop %rbx
    ret

# Helpers use the volatile registers only and preserve the PCI selector.
#ifdef BMO_STORAGE_QUIESCE_METAL
#include "../../storage/calibrate_tsc.inc"
#endif
pci_read:
    mov %r9d, %eax
    or %ecx, %eax
    out %eax, %dx
    add $4, %dx
    in %dx, %eax
    sub $4, %dx
    ret

checksum:
    xor %eax, %eax
    mov %rsi, %rdx
checksum_byte:
    add (%rdx), %al
    inc %rdx
    dec %ecx
    jnz checksum_byte
    test %al, %al
    ret

# Read just the registers that describe translation and queue ownership.
# RCX = BootServices, RDX = validated IVRS/PCI base, R8 = report, R9 = hex32.
# EFI_CPU_IO2 is a Boot Services protocol. It never runs after EBS.
amdvi_uefi_snapshot:
    push %rbx
    push %rsi
    push %rdi
    push %r12
    push %r13
    push %r14
    push %r15
    sub $96, %rsp
    mov %rdx, %r12
    mov %r8, %r13
    mov %r9, %r14
    mov $1, %ebx                    # Aperture outside the admitted range.
    mov $0xf0000000, %eax
    cmp %rax, %r12
    jb .Lsnapshot_done
    mov $0xffffc000, %eax
    cmp %rax, %r12
    ja .Lsnapshot_done
    test $0x3fff, %r12d
    jnz .Lsnapshot_done

    mov $2, %ebx                    # CPU I/O 2 unavailable.
    mov %rcx, %rax
    lea .Lcpu_io2_guid(%rip), %rcx
    xor %edx, %edx
    lea 40(%rsp), %r8
    call *0x140(%rax)               # LocateProtocol.
    test %rax, %rax
    js .Lsnapshot_done
    mov 40(%rsp), %r15
    test %r15, %r15
    jz .Lsnapshot_done
    mov $3, %ebx                    # Incomplete or invalid MMIO snapshot.
    xor %esi, %esi
    lea .Lregister_offsets(%rip), %rdi
.Lread_register:
    movzwl (%rdi,%rsi,2), %r8d
    add %r12, %r8
    mov %r15, %rcx
    mov $2, %edx                    # Uint32; read both halves in order.
    mov $2, %r9d
    lea 48(%rsp,%rsi,8), %rax
    mov %rax, 32(%rsp)
    call *(%r15)                    # CPU I/O 2 Mem.Read.
    test %rax, %rax
    js .Lsnapshot_done
    cmpq $-1, 48(%rsp,%rsi,8)
    je .Lsnapshot_done
    inc %esi
    cmp $5, %esi
    jb .Lread_register

    xor %esi, %esi
    lea 9(%r13), %rdi
.Lprint_register:
    mov 52(%rsp,%rsi,8), %eax
    call *%r14
    mov 48(%rsp,%rsi,8), %eax
    call *%r14
    inc %rdi
    inc %esi
    cmp $5, %esi
    jb .Lprint_register
    mov $4, %ebx                    # All five registers read.
.Lsnapshot_done:
    mov %ebx, %eax
    mov %r13, %rdi
    call *%r14
#ifdef BMO_AMDVI_POST
    mov %ebx, %eax
#endif
    add $96, %rsp
    pop %r15
    pop %r14
    pop %r13
    pop %r12
    pop %rdi
    pop %rsi
    pop %rbx
    ret

.p2align 1
.Lregister_offsets:
    .short 0x0018, 0x0000, 0x0008, 0x0010, 0x2020
.p2align 3
.Lcpu_io2_guid:
    .quad 0x4c0eae5fad61f191, 0x4fc688d269e8fab9

#ifdef BMO_STORAGE_STATE
#include "../../storage/handoff_uefi.inc"
#endif

#ifdef BMO_AMDVI_POST
#include "post_ebs_probe.inc"
#endif
#ifdef BMO_AMDVI_PHYSICAL_MMIO_TEST
#include "physical_mmio_boot.inc"
#ifdef BMO_AMDVI_PHYSICAL_USB_TEST
#include "../../GPU/NVIDIA/physical_falcon.inc"
#include "board_ivrs.S"
#endif
#endif
#ifdef BMO_AMDVI_GUEST_NVME
#include "../../storage/nvme_guest.inc"
#endif
#if defined(BMO_FULL_HD) || defined(BMO_AMDVI_GSP_DMA)
#include "../../display/GOP/gop_stage.inc"
#endif
