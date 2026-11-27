# GA106 board stage. Runs on the supervisor stack after ExitBootServices.
# Runs after the translated xHCI No-Op; GPU BME stays off during Falcon reset.
.set FALCON_BOARD_PDE, 0x15408
.set FALCON_BOARD_VA, 0x10200000
.set FALCON_BOARD_RID, 0x80290000
.set FALCON_BOARD_ROOT_RID, 0x80001900
.set SEC2_FUSE_ALIAS_SLOT, 2
.set SEC2_FUSE_ALIAS, FALCON_BOARD_VA + SEC2_FUSE_ALIAS_SLOT*4096
.set SEC2_CPU_ALIAS, FALCON_BOARD_VA+0x3000
.set SEC2_IOMMU_ALIAS, FALCON_BOARD_VA+0x5000
# PMC, SCRATCH14, Falcon, RISC-V/BROM and WPR2. CPU alias only.
# Use the same pages when installing, invalidating and retiring the alias.
#define FALCON_CPU_PAGES 0, 1, 9, 0x110, 0x111, 0x1fa

.globl nvidia_physical_begin
nvidia_physical_begin:
.Lnvidia_physical_begin:
    push %rbx
    push %r12
    push %r13
    push %r14
    push %r15
    push %rdi
    mov %rsp, %r13
    and $-16, %rsp
    sub $80, %rsp
    cmpq $0, NVIDIA_FWSEC_LAUNCH_STATUS(%rbp)
    jne .Lboard_skip
    movq $0, GSP_PCIE_INIT_FLAGS(%rbp)
    movl $0x406, NVIDIA_FWSEC_LAUNCH_STATUS(%rbp)
    cmpl $2, GSP_FWSEC_DOMAIN_STATUS(%rbp)
    jne .Lboard_skip
    cmpq $0x0a107000, GSP_POST_FWSEC(%rbp)
    jne .Lboard_skip
    cmpq $1, AMDVI_PHYSICAL_USB_STATE(%rbp)
    jne .Lboard_skip
    movl $0x407, NVIDIA_FWSEC_LAUNCH_STATUS(%rbp)
    mov $0xcf8, %dx
    in %dx, %eax
    mov %eax, %ebx
    xor %eax, %eax
    call .Lboard_pci_read
    cmp $0x250410de, %eax
    jne .Lboard_exit
    mov $4, %eax
    call .Lboard_pci_read
    movzwl %ax, %r12d
    and $6, %eax
    cmp $2, %eax
    jne .Lboard_exit
    mov $0x10, %eax
    call .Lboard_pci_read
    cmp $0xfb000000, %eax
    jne .Lboard_exit
    mov $0x2c, %eax
    call .Lboard_pci_read
    cmp $0x397d1462, %eax
    jne .Lboard_exit
    mov STORAGE_TSC_10MS(%rbp), %r15
    cmp $1000000, %r15
    jb .Lboard_exit
    cmp $100000000, %r15
    ja .Lboard_exit
    movl $0x408, NVIDIA_FWSEC_LAUNCH_STATUS(%rbp)
    call .Lboard_pcie_status
    jc .Lboard_exit
    mov %r14d, %eax
    call .Lboard_pci_read
    cmp $-1, %eax
    je .Lboard_exit
    test $0x00200000, %eax
    jnz .Lboard_exit
    movl $0x409, NVIDIA_FWSEC_LAUNCH_STATUS(%rbp)
    cmpq $0, FALCON_BOARD_PDE(%rbp)
    jne .Lboard_exit
    mov GSP_PHYSICAL_DTE_BASE(%rbp), %r10
    test $4095, %r10d
    jnz .Lboard_exit
    cmp $0x100000, %r10
    jb .Lboard_exit
    cmp $(0x10000000-GSP_PHYSICAL_WORKSPACE_END), %r10
    ja .Lboard_exit
    add $0x206000, %r10
    cld
    mov %r10, %rdi
    mov $512, %ecx
    xor %eax, %eax
    repe scasq
    jne .Lboard_exit
    mov %r10, 64(%rsp)
    movabs $0x80000000fb00001b, %rax
    .irp page,FALCON_CPU_PAGES
    lea (\page*4096)(%rax), %rcx
    mov %rcx, (\page*8)(%r10)
    .endr
    movabs $0x80000000fb824019, %rax  # Read-only supervisor CPU mapping.
    mov %rax, (SEC2_FUSE_ALIAS_SLOT*8)(%r10)
    movabs $0x80000000fb84001b, %rax
    mov %rax, 24(%r10)
    add $4096, %rax
    mov %rax, 32(%r10)
    movabs $0x80000000fd50001b, %rax
    mov %rax, 40(%r10)
    add $8192, %rax
    mov %rax, 56(%r10)
    lea 3(%r10), %rax
    mov %rax, FALCON_BOARD_PDE(%rbp)
    call .Lboard_flush
    mov $FALCON_BOARD_VA, %ecx
    mov %r15, %rdx
    call .Lprepare_ga106_falcon
    cmp $1, %eax
    je .Lboard_fwsec
    test %eax, %eax
    mov $0x40a, %eax
    cmovne %r8d, %eax
    mov %rax, NVIDIA_FWSEC_LAUNCH_STATUS(%rbp)
    mov FALCON_BOARD_VA+0x111388, %eax
    mov %eax, NVIDIA_FALCON_MODE_RECEIPT(%rbp)
    mov FALCON_BOARD_VA+0x111668, %eax
    mov %eax, (NVIDIA_FALCON_MODE_RECEIPT+4)(%rbp)
    jmp .Lboard_unmap
.Lboard_fwsec:
    movl $0x40b, NVIDIA_FWSEC_LAUNCH_STATUS(%rbp)
    mov %r12d, %ecx
    or $4, %ecx
    call .Lboard_command
    cmp %cx, %ax
    jne .Lboard_revoke
    mov $FALCON_BOARD_VA, %ecx
    mov %r15, %rdx
    mov $0x0a107000, %r8d
    lea NVIDIA_FWSEC_LAUNCH_RECEIPT(%rbp), %r9
    call .Llaunch_ga106_fwsec
    or $0x400, %eax
    mov %rax, NVIDIA_FWSEC_LAUNCH_STATUS(%rbp)
.Lboard_revoke:
    mov %r12d, %ecx
    call .Lboard_command
    cmp %r12w, %ax
    jne .Lboard_pin
    imul $10, %r15, %r15         # Bound PCIe drain to 100 ms.
    lfence
    rdtsc
    shl $32, %rdx
    or %rdx, %rax
    add %rax, %r15
.Lboard_drain:
    mov %r14d, %eax
    call .Lboard_pci_read
    cmp $-1, %eax
    je .Lboard_pin
    test $0x00200000, %eax
    jz .Lboard_drained
    call .Lwithin_deadline
    jb .Lboard_drain
.Lboard_pin:
    movq $0x404, NVIDIA_FWSEC_LAUNCH_STATUS(%rbp)
    jmp .Lboard_unmap
.Lboard_drained:
    cmpl $0x401, NVIDIA_FWSEC_LAUNCH_STATUS(%rbp)
    jne .Lboard_unmap
    mov $FALCON_BOARD_VA, %ecx
    mov GSP_UEFI_TIME_NS(%rbp), %rdx
    mov GSP_UEFI_TIME_TSC(%rbp), %r8
    mov STORAGE_TSC_10MS(%rbp), %r9
    call .Lgsp_seed_ptimer
    mov %rax, GSP_PTIMER_AFTER_WRITE(%rbp)
    movq $-2, GSP_PTIMER_BEFORE_INIT(%rbp)
    mov GSP_SEC2_SOURCE(%rbp), %rcx
    movl $0x604, (NVIDIA_SEC2_STAGE_RECEIPT+4)(%rbp)
    test %rcx, %rcx
    jz .Lboard_unmap
    mov GSP_PHYSICAL_DTE_BASE(%rbp), %rdx
    add $GSP_SEC2_WORKSPACE_OFFSET, %rdx
    mov SEC2_FUSE_ALIAS+0x148, %r8d
    mov %r8d, NVIDIA_SEC2_STAGE_RECEIPT(%rbp)
    call .Lprepare_sec2_image
    mov $0x603, %ecx
    test %eax, %eax
    jz .Lboard_sec2_record
    lea 0x600(%rax), %ecx
.Lboard_sec2_record:
    mov %ecx, (NVIDIA_SEC2_STAGE_RECEIPT+4)(%rbp)
    test %eax, %eax
    jz .Lboard_unmap
    movl $0x706, (NVIDIA_SEC2_EXEC_RECEIPT+4)(%rbp)
    mov $SEC2_CPU_ALIAS, %ecx
    mov $(FALCON_BOARD_VA+0x110000), %edx
    mov STORAGE_TSC_10MS(%rbp), %r8
    call .Lprepare_sec2_engines
    test %eax, %eax
    jz .Lboard_unmap
    movl $0x707, (NVIDIA_SEC2_EXEC_RECEIPT+4)(%rbp)
    mov GSP_NATIVE_QUEUE_BASE(%rbp), %rdx
    test $4095, %edx
    jnz .Lboard_unmap
    cmp GSP_STAGE_BASE(%rbp), %rdx
    jb .Lboard_unmap
    mov GSP_PHYSICAL_DTE_BASE(%rbp), %rax
    sub $GSP_LOG_END, %rax      # Bounds both 16-page logs in the firmware reservation.
    cmp %rax, %rdx
    ja .Lboard_unmap
    call .Lpublish_sec2_domain
    test %eax, %eax
    jz .Lboard_unmap
    movl $0x704, (NVIDIA_SEC2_EXEC_RECEIPT+4)(%rbp)
    mov %r12d, %ecx
    or $4, %ecx
    call .Lboard_command
    cmp %cx, %ax
    jne .Lboard_sec2_revoke
    mov GSP_PHYSICAL_DTE_BASE(%rbp), %rax
    mov SEC2_IOMMU_ALIAS+8192+0x18, %ecx
    mov %ecx, GSP_INIT_CAPTURE_OFFSET+GSP_INIT_EVENT_TAILS(%rax)
    mov $SEC2_CPU_ALIAS, %ecx
    mov STORAGE_TSC_10MS(%rbp), %rdx
    lea NVIDIA_FWSEC_LAUNCH_RECEIPT(%rbp), %r8
    call .Lexecute_sec2_booter
    add $0x700, %eax
    mov %eax, (NVIDIA_SEC2_EXEC_RECEIPT+4)(%rbp)
    mov (NVIDIA_FWSEC_LAUNCH_RECEIPT+8)(%rbp), %eax
    mov %eax, NVIDIA_SEC2_EXEC_RECEIPT(%rbp)
    cmpl $0x701, (NVIDIA_SEC2_EXEC_RECEIPT+4)(%rbp)
    jne .Lboard_sec2_revoke
    mov GSP_PHYSICAL_DTE_BASE(%rbp), %rax
    mov SEC2_IOMMU_ALIAS+8192+0x18, %ecx
    mov %ecx, GSP_INIT_CAPTURE_OFFSET+GSP_INIT_EVENT_TAILS+4(%rax)
    movl $0x805, (NVIDIA_GSP_INIT_RECEIPT+4)(%rbp)
    mov $0x14, %eax
    call .Lboard_pci_read
    cmp $0xd000000c, %eax
    jne .Lboard_sec2_revoke
    mov $0x18, %eax
    call .Lboard_pci_read
    test %eax, %eax
    jne .Lboard_sec2_revoke
    mov $0x1c, %eax
    call .Lboard_pci_read
    cmp $0xe000000c, %eax
    jne .Lboard_sec2_revoke
    mov $0x20, %eax
    call .Lboard_pci_read
    test %eax, %eax
    jne .Lboard_sec2_revoke
    mov $8, %eax
    call .Lboard_pci_read
    movzbl %al, %r9d
    shr $8, %eax
    cmp $0x030000, %eax
    jne .Lboard_sec2_revoke
    # The validated PCIe capability's Link Capabilities follows Device Status.
    lea 4(%r14), %eax
    call .Lboard_pci_read
    cmp $-1, %eax
    je .Lboard_sec2_revoke
    shl $32, %rax
    or %rax, %r9
    mov %r9, 32(%rsp)
    call .Lboard_gsp_pcie_flags
    mov %eax, GSP_PCIE_INIT_FLAGS(%rbp)
    shl $8, %eax
    or %rax, 32(%rsp)
    mov $FALCON_BOARD_VA, %ecx
    call .Lgsp_read_ptimer
    mov %rax, GSP_PTIMER_BEFORE_INIT(%rbp)
    mov %rbp, %rcx
    mov $0xd0000000, %edx         # BAR1 verified above on the matching RTX.
    call .Lgsp_console_bytes_615
    mov 32(%rsp), %r9
    mov %rax, 32(%rsp)
    lea 1(%rax,%rax), %eax       # Upper dword carries bytes and its valid flag.
    mov %eax, (GSP_PCIE_INIT_FLAGS+4)(%rbp)
    mov GSP_PHYSICAL_DTE_BASE(%rbp), %rax
    lea GSP_INIT_CAPTURE_OFFSET(%rax), %rax
    mov %rax, 40(%rsp)
    movq $(SEC2_IOMMU_ALIAS+8192), 48(%rsp)
    mov GSP_NATIVE_QUEUE_BASE(%rbp), %rdx
    mov $(FALCON_BOARD_VA+0x110000), %ecx
    mov STORAGE_TSC_10MS(%rbp), %r8
    call .Lgsp_init_615
    mov %rax, NVIDIA_GSP_INIT_RECEIPT(%rbp)
    mov GSP_PHYSICAL_DTE_BASE(%rbp), %r9
    mov SEC2_IOMMU_ALIAS+8192+0x18, %ecx
    mov %ecx, GSP_INIT_CAPTURE_OFFSET+GSP_INIT_EVENT_TAILS+12(%r9)
    shr $32, %rax
    mov GSP_NATIVE_QUEUE_BASE(%rbp), %rdx
    cmp $0x802, %eax
    jne .Lboard_gsp_timeout
    add $GSP_LOGRM_OFFSET, %rdx
    jmp .Lboard_gsp_snapshot
.Lboard_gsp_timeout:
    add $GSP_LOGINIT_OFFSET, %rdx
    cmp $0x804, %eax
    je .Lboard_gsp_snapshot
    cmp $0x806, %eax
    jne .Lboard_sec2_revoke
.Lboard_gsp_snapshot:
    mov $(FALCON_BOARD_VA+0x110000), %ecx
    mov $(SEC2_IOMMU_ALIAS+8192), %r8d
    mov GSP_PHYSICAL_DTE_BASE(%rbp), %r9
    lea GSP_TRACE_OFFSET(%r9), %rax
    mov %rax, 40(%rsp)          # Sixth Win64 argument, private CPU-only trace.
    add $0x205000, %r9          # Private 4-KiB AMD-Vi event ring.
    lea GSP_NATIVE_SNAPSHOT(%rbp), %rax
    mov %rax, 32(%rsp)          # Fifth Win64 argument.
    call .Lgsp_snapshot_615
.Lboard_sec2_revoke:
    mov %r12d, %ecx
    call .Lboard_command
    cmp %r12w, %ax
    jne .Lboard_sec2_pin
    mov STORAGE_TSC_10MS(%rbp), %r10
    imul $10, %r10, %r10
    call .Lprep_deadline
.Lboard_sec2_drain:
    mov %r14d, %eax
    call .Lboard_pci_read
    cmp $-1, %eax
    je .Lboard_sec2_pin
    test $0x00200000, %eax
    jz .Lboard_unmap
    call .Lwithin_deadline
    jb .Lboard_sec2_drain
.Lboard_sec2_pin:
    movl $0x705, (NVIDIA_SEC2_EXEC_RECEIPT+4)(%rbp)
.Lboard_unmap:
    movq $0, FALCON_BOARD_PDE(%rbp)
    call .Lboard_flush
    mov 64(%rsp), %r10
    .irp page,FALCON_CPU_PAGES
    movq $0, (\page*8)(%r10)
    .endr
    movq $0, (SEC2_FUSE_ALIAS_SLOT*8)(%r10)
    movq $0, 24(%r10)
    movq $0, 32(%r10)
    movq $0, 40(%r10)
    movq $0, 56(%r10)
.Lboard_exit:
    mov $0xcf8, %dx
    mov %ebx, %eax
    out %eax, %dx
    xor %eax, %eax
    cmpq $0x404, NVIDIA_FWSEC_LAUNCH_STATUS(%rbp)
    je .Lboard_unverified
    cmpl $0x705, (NVIDIA_SEC2_EXEC_RECEIPT+4)(%rbp)
    jne .Lboard_return
.Lboard_unverified:
    mov $3, %eax
    jmp .Lboard_return
.Lboard_skip:
    xor %eax, %eax
.Lboard_return:
    mov %r13, %rsp
    pop %rdi
    pop %r15
    pop %r14
    pop %r13
    pop %r12
    pop %rbx
    ret

# Sample the one root port previously identified on this board. All accesses
# below are PCI configuration reads and no reset is issued.
.Lboard_gsp_pcie_flags:
    lea -4(%r14), %eax          # Device Capabilities, before Device Control.
    call .Lboard_pci_read
    mov %eax, %ecx
    mov $FALCON_BOARD_ROOT_RID, %r8d
    xor %eax, %eax
    call .Lboard_pci_read_at
    cmp $0x14831022, %eax
    jne .Lboard_gsp_pcie_no_root
    mov $0xc, %eax
    call .Lboard_pci_read_at
    and $0x007f0000, %eax       # Header Type 1, ignoring multifunction.
    cmp $0x00010000, %eax
    jne .Lboard_gsp_pcie_no_root
    call .Lboard_pcie_cap
    jc .Lboard_gsp_pcie_no_root
    mov %eax, %r9d
    mov $8, %eax
    call .Lboard_pci_read_at
    mov %eax, %r11d
    mov $0x18, %eax
    call .Lboard_pci_read_at
    cmp $-1, %eax
    je .Lboard_gsp_pcie_no_root
    mov %eax, %r8d
    mov %r11d, %edx
    jmp .Lgsp_pcie_flags_615
.Lboard_gsp_pcie_no_root:
    xor %edx, %edx             # Suppress upstream when the root is unverified.
    jmp .Lgsp_pcie_flags_615

# Locate PCIe Device Control/Status within the conventional capabilities.
.Lboard_pcie_status:
    mov $FALCON_BOARD_RID, %r8d
    call .Lboard_pcie_cap
    jc .Lboard_pcie_status_done
    lea 8(%r10), %r14d
.Lboard_pcie_status_done:
    ret

# A 48-entry budget rejects cycles, malformed pointers, and absent PCIe.
# R8 = configuration address prefix. R10 = capability offset on success.
.Lboard_pcie_cap:
    mov $4, %eax
    call .Lboard_pci_read_at
    test $0x00100000, %eax
    jz .Lboard_pcie_bad
    mov $0x34, %eax
    call .Lboard_pci_read_at
    mov $48, %r11d
.Lboard_pcie_next:
    movzbl %al, %r10d
    cmp $0x40, %r10d
    jb .Lboard_pcie_bad
    cmp $0xf4, %r10d
    ja .Lboard_pcie_bad
    test $3, %r10d
    jnz .Lboard_pcie_bad
    mov %r10d, %eax
    call .Lboard_pci_read_at
    cmp $0x10, %al               # PCI Express capability ID.
    je .Lboard_pcie_found
    shr $8, %eax
    dec %r11d
    jnz .Lboard_pcie_next
.Lboard_pcie_bad:
    stc
    ret
.Lboard_pcie_found:
    cmp $0xf0, %r10d             # Link Capabilities must fit in PCI config space.
    ja .Lboard_pcie_bad
    clc
    ret

.Lboard_command:
    mov $(FALCON_BOARD_RID+4), %eax
    mov $0xcf8, %dx
    out %eax, %dx
    add $4, %dx
    mov %ecx, %eax
    out %ax, %dx                 # Never write PCI Status.
    in %dx, %ax
    ret
.Lboard_pci_read:
    or $FALCON_BOARD_RID, %eax
    jmp .Lboard_pci_access
.Lboard_pci_read_at:
    or %r8d, %eax
.Lboard_pci_access:
    mov $0xcf8, %dx
    out %eax, %dx
    add $4, %dx
    in %dx, %eax
    ret
.Lboard_flush:
    .irp page,FALCON_CPU_PAGES
    invlpg (FALCON_BOARD_VA+\page*4096)
    .endr
    invlpg SEC2_FUSE_ALIAS
    invlpg SEC2_CPU_ALIAS
    invlpg (SEC2_CPU_ALIAS+4096)
    invlpg SEC2_IOMMU_ALIAS
    invlpg (SEC2_IOMMU_ALIAS+8192)
    ret
#undef FALCON_CPU_PAGES

#include "fwsec_launch.S"
#include "sec2_prepare.S"
#include "sec2_execute.inc"
#include "sec2_domain.inc"
#include "gsp_init_615.inc"
#include "gsp_ptimer.inc"
.globl nvidia_physical_end
nvidia_physical_end:
