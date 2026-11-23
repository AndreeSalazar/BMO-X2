# GA106 board stage. Runs on the supervisor stack after ExitBootServices.
# Runs after the translated xHCI No-Op; GPU BME stays off during Falcon reset.
.set FALCON_BOARD_PDE, 0x15408
.set FALCON_BOARD_VA, 0x10200000
.set FALCON_BOARD_RID, 0x80290000
# PMC, SCRATCH14, Falcon, RISC-V/BROM and WPR2. CPU alias only.
# Use the same pages when installing, invalidating and retiring the alias.
#define FALCON_CPU_PAGES 0, 1, 0x110, 0x111, 0x1fa

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
    sub $48, %rsp
    cmpq $0, NVIDIA_FWSEC_LAUNCH_STATUS(%rbp)
    jne .Lboard_skip
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
    cmp $(0x10000000-0x209000), %r10
    ja .Lboard_exit
    add $0x206000, %r10
    cld
    mov %r10, %rdi
    mov $512, %ecx
    xor %eax, %eax
    repe scasq
    jne .Lboard_exit
    mov %r10, 32(%rsp)
    movabs $0x80000000fb00001b, %rax
    .irp page,FALCON_CPU_PAGES
    lea (\page*4096)(%rax), %rcx
    mov %rcx, (\page*8)(%r10)
    .endr
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
    jz .Lboard_unmap
    call .Lwithin_deadline
    jb .Lboard_drain
.Lboard_pin:
    movq $0x404, NVIDIA_FWSEC_LAUNCH_STATUS(%rbp)
.Lboard_unmap:
    movq $0, FALCON_BOARD_PDE(%rbp)
    call .Lboard_flush
    mov 32(%rsp), %r10
    .irp page,FALCON_CPU_PAGES
    movq $0, (\page*8)(%r10)
    .endr
.Lboard_exit:
    mov $0xcf8, %dx
    mov %ebx, %eax
    out %eax, %dx
    xor %eax, %eax
    cmpq $0x404, NVIDIA_FWSEC_LAUNCH_STATUS(%rbp)
    jne .Lboard_return
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

# Locate PCIe Device Control/Status within the conventional capabilities.
# A 48-entry budget rejects cycles, malformed pointers, and absent PCIe.
.Lboard_pcie_status:
    mov $4, %eax
    call .Lboard_pci_read
    test $0x00100000, %eax
    jz .Lboard_pcie_bad
    mov $0x34, %eax
    call .Lboard_pci_read
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
    call .Lboard_pci_read
    cmp $0x10, %al               # PCI Express capability ID.
    je .Lboard_pcie_found
    shr $8, %eax
    dec %r11d
    jnz .Lboard_pcie_next
.Lboard_pcie_bad:
    stc
    ret
.Lboard_pcie_found:
    lea 8(%r10), %r14d
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
    mov $0xcf8, %dx
    out %eax, %dx
    add $4, %dx
    in %dx, %eax
    ret
.Lboard_flush:
    .irp page,FALCON_CPU_PAGES
    invlpg (FALCON_BOARD_VA+\page*4096)
    .endr
    ret
#undef FALCON_CPU_PAGES

#include "fwsec_launch.S"
.globl nvidia_physical_end
nvidia_physical_end:
