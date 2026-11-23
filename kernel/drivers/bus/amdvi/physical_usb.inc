# Board-only xHCI path. RBP is the private handoff, EAX is the operation:
# 1 acquire AMD-Vi after xHC reset, 2 confirm the first command, 3 close.
# Return 0 ordinary GOP/USB path, 1 translated USB, 3 stop USB and pin.
.set PHYS_USB_PDE, 0x15408
.set PHYS_USB_IOMMU_VA, 0x10200000
.set PHYS_USB_AMDVI, 0xfd500000
.Lphysical_usb_entry:
    push %rbx
    push %r12
    push %r13
    push %r14
    push %r15
    mov %rsp, %r14
    and $-16, %rsp
    sub $32, %rsp
    mov %eax, %r15d
    lea AMDVI_PHYSICAL_USB_RECEIPT(%rbp), %r12
    cmp $1, %r15d
    jne .Lphysical_usb_active
    mov $PHYS_USB_AMDVI, %eax
    cmp %rax, AMDVI_POST_BASE(%rbp)
    jne .Lphysical_usb_skip
    cmpq $3, AMDVI_PHYSICAL_USB_STATE(%rbp)
    je .Lphysical_usb_skip
    cmpq $0, AMDVI_PHYSICAL_USB_STATE(%rbp)
    jne .Lphysical_usb_pin
    cmpq $0x101, GSP_PHYSICAL_MMIO_RESULT(%rbp)
    jne .Lphysical_usb_skip
    cmpq $1, GSP_PHYSICAL_DTE_STATUS(%rbp)
    jne .Lphysical_usb_skip
    cmpw $0x2b03, %gs:0x360
    jne .Lphysical_usb_skip
    cmpw $3, (STORAGE_ROWS+STORAGE_STATUS)(%rbp)
    jne .Lphysical_usb_skip
    cmpw $3, (STORAGE_ROWS+STORAGE_ROW_BYTES+STORAGE_STATUS)(%rbp)
    jne .Lphysical_usb_skip
    mov %gs:0x750, %rax
    testl $1, 4(%rax)             # The controller reset left HCHalted set.
    jz .Lphysical_usb_skip
    mov STORAGE_TSC_10MS(%rbp), %rax
    cmp $1000000, %rax
    jb .Lphysical_usb_skip
    cmp $100000000, %rax
    ja .Lphysical_usb_skip
    imul $10, %rax, %rax
    mov %rax, 72(%r12)            # 100 ms IOMMU command deadline.
    call .Lphysical_usb_pci
    jc .Lphysical_usb_skip
    mov GSP_PHYSICAL_DTE_BASE(%rbp), %rax
    mov %rax, (%r12)
    lea 0x204000(%rax), %rax
    mov %rax, 8(%r12)
    add $4096, %rax
    mov %rax, 16(%r12)
    call .Lphysical_usb_map
    jc .Lphysical_usb_skip
    mov $PHYS_USB_IOMMU_VA, %ecx
    mov %r12, %rdx
    call .Lopen_physical_translation
    call .Lphysical_usb_unmap
    cmp $1, %eax
    je .Lphysical_usb_started
    cmp $3, %eax
    je .Lphysical_usb_pin
    movq $0x210, AMDVI_PHYSICAL_USB_RESULT(%rbp) # Setup rejected or rolled back.
    jmp .Lphysical_usb_skip
.Lphysical_usb_started:
    movq $0x211, AMDVI_PHYSICAL_USB_RESULT(%rbp)
    jmp .Lphysical_usb_pass

.Lphysical_usb_active:
    cmpq $1, AMDVI_PHYSICAL_USB_STATE(%rbp)
    jne .Lphysical_usb_skip
    cmp $2, %r15d
    jne .Lphysical_usb_close
    call .Lphysical_usb_map
    jc .Lphysical_usb_pin
    mov $PHYS_USB_IOMMU_VA, %ecx
    mov 0x18(%rcx), %rax
    and $0x1005, %eax
    cmp $0x1005, %eax
    jne .Lphysical_usb_check_failed
    cmpq $0, 0x2018(%rcx)
    jne .Lphysical_usb_check_failed
    testq $3, 0x2020(%rcx)
    jnz .Lphysical_usb_check_failed
    call .Lphysical_usb_unmap
    movq $0x212, AMDVI_PHYSICAL_USB_RESULT(%rbp) # xHC No-Op matched, no IOMMU event.
    jmp .Lphysical_usb_pass
.Lphysical_usb_check_failed:
    call .Lphysical_usb_unmap
    movq $0x213, AMDVI_PHYSICAL_USB_RESULT(%rbp)
    jmp .Lphysical_usb_fail          # The caller stops xHCI before closing.
.Lphysical_usb_close:
    cmp $3, %r15d
    jne .Lphysical_usb_skip
    cmpb $1, %gs:0x37a
    jne .Lphysical_usb_pin
    movzwl %gs:0x37e, %eax
    cmp $0xffff, %eax
    je .Lphysical_usb_pin
    test $4, %al
    jnz .Lphysical_usb_pin
    call .Lphysical_usb_map
    jc .Lphysical_usb_pin
    mov $PHYS_USB_IOMMU_VA, %ecx
    mov %r12, %rdx
    call .Lclose_physical_translation
    call .Lphysical_usb_unmap
    cmp $1, %eax
    jne .Lphysical_usb_pin
    jmp .Lphysical_usb_pass
.Lphysical_usb_pin:
    movq $2, AMDVI_PHYSICAL_USB_STATE(%rbp)
    movq $0x214, AMDVI_PHYSICAL_USB_RESULT(%rbp)
.Lphysical_usb_fail:
    mov $3, %eax
    jmp .Lphysical_usb_exit
.Lphysical_usb_pass:
    mov $1, %eax
    jmp .Lphysical_usb_exit
.Lphysical_usb_skip:
    xor %eax, %eax
.Lphysical_usb_exit:
    mov %r14, %rsp
    pop %r15
    pop %r14
    pop %r13
    pop %r12
    pop %rbx
    ret

# The extra EFI LoaderData page belongs exclusively to the IOMMU CPU
# alias. AMD-Vi tables do not grant the page to any PCI requester.
.Lphysical_usb_map:
    cmpq $0, PHYS_USB_PDE(%rbp)
    jne .Lphysical_usb_bad_map
    mov GSP_PHYSICAL_DTE_BASE(%rbp), %r13
    test $0xfff, %r13d
    jnz .Lphysical_usb_bad_map
    cmp $0x100000, %r13
    jb .Lphysical_usb_bad_map
    cmp $(0x10000000-0x207000), %r13
    ja .Lphysical_usb_bad_map
    add $0x206000, %r13
    mov %r13, %rdi
    xor %eax, %eax
    mov $512, %ecx
    cld
    repe scasq
    jne .Lphysical_usb_bad_map
    movabs $0x80000000fd50001b, %rax
    mov %rax, (%r13)
    add $0x2000, %rax
    mov %rax, 16(%r13)
    lea 3(%r13), %rax
    mov %rax, PHYS_USB_PDE(%rbp)
    invlpg PHYS_USB_IOMMU_VA
    invlpg (PHYS_USB_IOMMU_VA+0x2000)
    clc
    ret
.Lphysical_usb_bad_map:
    stc
    ret
.Lphysical_usb_unmap:
    movq $0, PHYS_USB_PDE(%rbp)
    invlpg PHYS_USB_IOMMU_VA
    invlpg (PHYS_USB_IOMMU_VA+0x2000)
    movq $0, (%r13)
    movq $0, 16(%r13)
    ret

# All endpoints must leave BME clear. Only measured PCI-to-PCI bridges
# may keep forwarding; a legacy bridge can originate on behalf of a bus.
.Lphysical_usb_pci:
    mov $0xcf8, %dx
    in %dx, %eax
    push %rax
    mov $0x802b0300, %eax
    call .Lphysical_usb_read_pci
    cmp $0x149c1022, %eax
    jne .Lphysical_usb_pci_fail
    mov $0x802b0304, %eax
    call .Lphysical_usb_read_pci
    test $2, %al
    jz .Lphysical_usb_pci_fail
    and $0xfffb, %ax
    add $4, %dx
    out %ax, %dx
    sub $4, %dx
    mov $0x80290000, %eax
    call .Lphysical_usb_read_pci
    cmp $0x250410de, %eax
    jne .Lphysical_usb_pci_fail
    mov $0x80000000, %r8d
.Lphysical_usb_scan:
    mov %r8d, %eax
    call .Lphysical_usb_read_pci
    cmp $0xffff, %ax
    je .Lphysical_usb_next
    mov %eax, %r9d
    lea 4(%r8), %eax
    call .Lphysical_usb_read_pci
    test $4, %al
    jz .Lphysical_usb_next
    lea 8(%r8), %eax
    call .Lphysical_usb_read_pci
    shr $8, %eax
    cmp $0x060400, %eax
    jne .Lphysical_usb_pci_blocked
    cmp $0x1022, %r9w
    jne .Lphysical_usb_pci_blocked
.Lphysical_usb_next:
    add $0x100, %r8d
    cmp $0x81000000, %r8d
    jne .Lphysical_usb_scan
    pop %rax
    out %eax, %dx
    clc
    ret
.Lphysical_usb_pci_blocked:
    shr $8, %r8d
    movzwl %r8w, %eax
    shl $16, %eax
    or $0x215, %eax
    mov %rax, AMDVI_PHYSICAL_USB_RESULT(%rbp)
.Lphysical_usb_pci_fail:
    pop %rax
    out %eax, %dx
    stc
    ret
.Lphysical_usb_read_pci:
    out %eax, %dx
    add $4, %dx
    in %dx, %eax
    sub $4, %dx
    ret
