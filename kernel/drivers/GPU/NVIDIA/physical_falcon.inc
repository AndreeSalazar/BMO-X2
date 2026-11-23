# Board-only post-EBS path. Translation is disabled and its bases restored.
# No PCI Command writes. Map only the four pages that the Falcon routine can read.
# Receipt: zero untouched, 0x300 refused, 0x301 ready, 0x302 uncertain.
.set FALCON_BOARD_PDE, 0x15408
.set FALCON_BOARD_VA, 0x10200000
.Lnvidia_board_falcon_reset:
    push %rdi
    push %r13
    mov %rsp, %r13
    and $-16, %rsp
    sub $48, %rsp
    movq $0x300, NVIDIA_FALCON_RESET_RESULT(%rbp)
    cmpq $0, FALCON_BOARD_PDE(%rbp)
    jne .Lboard_falcon_return
    mov $0xcf8, %dx
    in %dx, %eax
    push %rax
    mov $0x80290000, %eax
    call .Lphysical_usb_read_pci
    cmp $0x250410de, %eax
    jne .Lboard_falcon_pci_fail
    mov $0x80290004, %eax
    call .Lphysical_usb_read_pci
    and $6, %eax
    cmp $2, %eax                  # Memory decode on, Bus Master off.
    jne .Lboard_falcon_pci_fail
    mov $0x80290010, %eax
    call .Lphysical_usb_read_pci
    cmp $0xfb000000, %eax
    jne .Lboard_falcon_pci_fail
    mov $0x8029002c, %eax
    call .Lphysical_usb_read_pci
    cmp $0x397d1462, %eax
    jne .Lboard_falcon_pci_fail
    pop %rax
    out %eax, %dx

    mov GSP_PHYSICAL_DTE_BASE(%rbp), %r10
    test $4095, %r10d
    jnz .Lboard_falcon_return
    cmp $0x100000, %r10
    jb .Lboard_falcon_return
    cmp $(0x10000000-0x207000), %r10
    ja .Lboard_falcon_return
    add $0x206000, %r10           # Validated LoaderData page also used by xHCI later.
    cld
    mov %r10, %rdi
    mov $512, %ecx
    xor %eax, %eax
    repe scasq
    jne .Lboard_falcon_return
    mov %r10, 32(%rsp)            # Outside the Win64 shadow space.
    movabs $0x80000000fb00001b, %rax
    mov %rax, 0(%r10)
    lea 0x110000(%rax), %rcx
    mov %rcx, (0x110*8)(%r10)
    lea 4096(%rcx), %rcx
    mov %rcx, (0x111*8)(%r10)
    add $0x1fa000, %rax
    mov %rax, (0x1fa*8)(%r10)
    lea 3(%r10), %rax
    mov %rax, FALCON_BOARD_PDE(%rbp)
    call .Lboard_falcon_flush
    mov $FALCON_BOARD_VA, %ecx
    mov STORAGE_TSC_10MS(%rbp), %rdx
    call .Lprepare_ga106_falcon
    or $0x300, %eax
    mov %rax, NVIDIA_FALCON_RESET_RESULT(%rbp)
    movq $0, FALCON_BOARD_PDE(%rbp)
    call .Lboard_falcon_flush
    mov 32(%rsp), %r10
    movq $0, 0(%r10)
    movq $0, (0x110*8)(%r10)
    movq $0, (0x111*8)(%r10)
    movq $0, (0x1fa*8)(%r10)
    jmp .Lboard_falcon_return
.Lboard_falcon_pci_fail:
    pop %rax
    out %eax, %dx
.Lboard_falcon_return:
    mov %r13, %rsp
    pop %r13
    pop %rdi
    ret
.Lboard_falcon_flush:
    invlpg FALCON_BOARD_VA
    invlpg (FALCON_BOARD_VA+0x110000)
    invlpg (FALCON_BOARD_VA+0x111000)
    invlpg (FALCON_BOARD_VA+0x1fa000)
    ret
