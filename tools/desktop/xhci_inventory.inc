# Read PCI class codes only. Preserve the PCI configuration selector.
# One scan per boot, including bridges and multifunction devices.
usb_controllers:
    cmpb $0, %gs:0x35c
    jne inventory_cached
    mov $0xcf8, %edx
    in %dx, %eax
    mov %eax, %r9d
    mov $0x80000008, %ecx
    xor %r8d, %r8d
inventory_next:
    mov %ecx, %eax
    out %eax, %dx
    add $4, %edx
    in %dx, %eax
    sub $4, %edx
    shr $8, %eax
    cmp $0x0c0330, %eax
    jne inventory_advance
    test %r8d, %r8d
    jnz inventory_count
    # Record the first function and its raw BAR0/BAR1. Reading never sizes
    # the BAR, enables bus mastering or changes firmware ownership.
    mov %ecx, %eax
    and $0x00ffff00, %eax
    shr $8, %eax
    mov %eax, %gs:0x360
    lea 8(%ecx), %eax
    out %eax, %dx
    add $4, %edx
    in %dx, %eax
    mov %eax, %gs:0x364
    sub $4, %edx
    lea 12(%ecx), %eax
    out %eax, %dx
    add $4, %edx
    in %dx, %eax
    mov %eax, %gs:0x368
    sub $4, %edx
    lea -4(%ecx), %eax
    out %eax, %dx
    add $4, %edx
    in %dx, %eax
    mov %ax, %gs:0x36c
    sub $4, %edx
inventory_count:
    inc %r8d
inventory_advance:
    add $0x100, %ecx
    cmp $0x81000008, %ecx
    jne inventory_next
    mov %r9d, %eax
    out %eax, %dx
    mov %r8d, %gs:0x358
    movb $1, %gs:0x35c
    test %r8d, %r8d
    jz inventory_cached
    call xhci_read_caps
inventory_cached:
    mov %gs:0x358, %eax
    jmp finish

# Use a temporary supervisor-only 4 KiB mapping in the private page tables.
# Context page 0x1e is reserved here for the alias PT, below the boot stack.
xhci_read_caps:
    testw $2, %gs:0x36c
    jz caps_done
    mov %gs:0x364, %eax
    mov %eax, %ecx
    and $0x0f, %ecx
    and $-16, %eax
    cmp $4, %ecx
    je caps_64
    test %ecx, %ecx
    jnz caps_done
    jmp caps_address
caps_64:
    mov %gs:0x368, %edx
    cmp $0xff, %edx
    ja caps_done
    shl $32, %rdx
    or %rdx, %rax
caps_address:
    cmp $0x10000000, %rax
    jb caps_done
    test $0xfff, %eax
    jnz caps_done
    # Reject overlap with a firmware memory descriptor other than MMIO.
    mov 0x60(%rbp), %r8
    cmp $40, %r8
    jb caps_done
    cmp $256, %r8
    ja caps_done
    mov 0x50(%rbp), %rcx
    cmp $65536, %rcx
    ja caps_done
    lea 0x1000(%rbp), %rsi
caps_map_next:
    test %rcx, %rcx
    jz caps_map
    cmp %r8, %rcx
    jb caps_done
    mov 8(%rsi), %rdx
    cmp %rax, %rdx
    ja caps_map_advance
    mov %rax, %rdi
    sub %rdx, %rdi
    shr $12, %rdi
    cmp 24(%rsi), %rdi
    jae caps_map_advance
    cmpl $11, (%rsi)
    jne caps_done
caps_map_advance:
    add %r8, %rsi
    sub %r8, %rcx
    jmp caps_map_next
caps_map:
    lea 0x1e000(%rbp), %rdi
    mov %rax, %r8
    xor %eax, %eax
    mov $512, %ecx
    cld
    rep stosq
    lea 0x1e003(%rbp), %rax
    mov %rax, 0x15400(%rbp)
    or $0x19, %r8
    bts $63, %r8
    mov %r8, 0x1e000(%rbp)
    mov $0x10000000, %edi
    invlpg (%rdi)
    mov (%rdi), %eax
    mov 4(%rdi), %edx
    mov %eax, %gs:0x370
    mov %edx, %gs:0x374
    call xhci_handoff
#ifdef XHCI_COMMAND_PROBE
    lea 0x200(%rbp), %rax
    call *%rax
#endif
    movq $0, 0x15400(%rbp)
    movq $0, 0x1e000(%rbp)
    invlpg (%rdi)
    ret

# Status: 0 unavailable, 1 no legacy capability, 2 owned, 3 timed out,
# 4 malformed or outside this mapped page.
xhci_handoff:
    mov %gs:0x370, %eax
    cmp $0x20, %al
    jb caps_done
    test $3, %al
    jnz caps_done
    mov %eax, %ecx
    shr $16, %ecx
    cmp $0x96, %ecx
    jb caps_done
    cmp $0x200, %ecx
    jae caps_done
    mov %gs:0x374, %edx
    test %dl, %dl
    jz caps_done
    test $0xff000000, %edx
    jz caps_done
    mov 0x10(%rdi), %eax
    shr $16, %eax
    test %eax, %eax
    jz legacy_absent
    mov $64, %r8d
legacy_next:
    cmp $8, %eax
    jb legacy_invalid
    cmp $1022, %eax
    ja legacy_invalid
    mov (%rdi,%rax,4), %ecx
    test %cl, %cl
    jz legacy_invalid
    cmp $0xff, %cl
    je legacy_invalid
    cmp $1, %cl
    je legacy_claim
    movzbl %ch, %ecx
    test %ecx, %ecx
    jz legacy_absent
    add %ecx, %eax
    dec %r8d
    jnz legacy_next
legacy_invalid:
    movb $4, %gs:0x378
    ret
legacy_absent:
    movb $1, %gs:0x378
    ret
legacy_claim:
    # Enable writes only for the OS semaphore byte. Preserve the BIOS byte.
    orq $2, 0x1e000(%rbp)
    invlpg (%rdi)
    lea (%rdi,%rax,4), %rsi
    movzbl 3(%rsi), %edx
    orb $1, 3(%rsi)
    mov $100000, %ecx
legacy_wait:
    testb $1, 2(%rsi)
    jz legacy_owned
    pause
    loop legacy_wait
    mov %dl, 3(%rsi)
    movb $3, %gs:0x378
    ret
legacy_owned:
    movb $2, %gs:0x378
caps_done:
    ret
