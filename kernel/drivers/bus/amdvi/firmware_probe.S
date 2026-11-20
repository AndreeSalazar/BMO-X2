.text
# Read-only AMD-Vi inventory while UEFI still owns the platform.
# RCX = EFI_SYSTEM_TABLE, RDX = packed report fields, R8 = report_hex32.
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
    mov $6, %ebx                    # MMIO decode disabled in PCI.
    test $1, %esi
    jz finish
    mov $7, %ebx                    # PCI decode and firmware base agree.
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
    pop %r15
    pop %r14
    pop %r13
    pop %r12
    pop %rdi
    pop %rsi
    pop %rbx
    ret

# Helpers use the volatile registers only and preserve the PCI selector.
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
