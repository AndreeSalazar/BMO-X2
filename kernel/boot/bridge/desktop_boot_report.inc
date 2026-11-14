# Snapshot before ExitBootServices. Failure leaves desktop boot available.
boot_report:
    push %rsi
    push %rdi
    sub $56, %rsp
    lea report_template(%rip), %rsi
    lea 0x800(%rbp), %rdi
    mov $(report_end-report_template), %ecx
    cld
    rep movsb
    lea (0x800+report_sbef-report_template)(%rbp), %rdi
    mov 0xb0(%rbp), %eax
    call report_hex32
    lea (0x800+report_l1-report_template)(%rbp), %rdi
    mov 0xd0(%rbp), %eax
    call report_hex32
    xor %eax, %eax
    in $0x64, %al
    lea (0x800+report_ps2-report_template)(%rbp), %rdi
    call report_hex32
    mov $0xcf8, %dx
    in %dx, %eax
    mov %eax, %r9d
    mov $0x80000008, %ecx
    xor %r8d, %r8d
report_pci_next:
    mov %ecx, %eax
    out %eax, %dx
    add $4, %dx
    in %dx, %eax
    sub $4, %dx
    shr $8, %eax
    cmp $0x0c0330, %eax
    jne report_pci_advance
    cmp $2, %r8d
    jae report_pci_count
    push %rcx
    push %rdx
    lea (0x800+report_pci0-report_template)(%rbp), %rdi
    imul $(report_pci1-report_pci0), %r8d, %eax
    add %rax, %rdi
    mov %ecx, %eax
    shr $8, %eax
    and $0xffff, %eax
    call report_hex32
    inc %rdi
    mov (%rsp), %edx
    mov 8(%rsp), %eax
    sub $8, %eax
    out %eax, %dx
    add $4, %dx
    in %dx, %eax
    call report_hex32
    inc %rdi
    mov (%rsp), %edx
    mov 8(%rsp), %eax
    sub $4, %eax
    out %eax, %dx
    add $4, %dx
    xor %eax, %eax
    in %dx, %ax
    call report_hex32
    pop %rdx
    pop %rcx
report_pci_count:
    inc %r8d
report_pci_advance:
    add $0x100, %ecx
    cmp $0x81000008, %ecx
    jne report_pci_next
    mov %r9d, %eax
    out %eax, %dx
    mov %r8d, %eax
    lea (0x800+report_xhci-report_template)(%rbp), %rdi
    call report_hex32

    mov 0x38(%rbp), %rcx
    lea 40(%rsp), %rdx
    lea report_path(%rip), %r8
    movabs $0x8000000000000003, %r9
    movq $0, 32(%rsp)
    call *8(%rcx)
    test %rax, %rax
    js report_done
    movq $(report_end-report_template), 48(%rsp)
    mov 40(%rsp), %rcx
    lea 48(%rsp), %rdx
    lea 0x800(%rbp), %r8
    call *0x28(%rcx)
    test %rax, %rax
    js report_close
    cmpq $(report_end-report_template), 48(%rsp)
    jne report_close
    mov 40(%rsp), %rcx
    call *0x50(%rcx)
    test %rax, %rax
    js report_close
    movb $1, 0xf0(%rbp)
report_close:
    mov 40(%rsp), %rcx
    call *0x10(%rcx)
report_done:
    add $56, %rsp
    pop %rdi
    pop %rsi
    ret

report_hex32:
    mov $8, %ecx
report_hex_digit:
    rol $4, %eax
    mov %al, %dl
    and $15, %dl
    add $'0', %dl
    cmp $'9', %dl
    jbe report_hex_store
    add $7, %dl
report_hex_store:
    mov %dl, (%rdi)
    inc %rdi
    loop report_hex_digit
    ret

report_template:
    .ascii "BMO-X2 V2 UEFI\r\nSBEF="
report_sbef:
    .ascii "00000000\r\nCPUID="
report_l1:
    .ascii "00000000\r\nPS2="
report_ps2:
    .ascii "00000000\r\nXHCI="
report_xhci:
    .ascii "00000000\r\nBDF ID CMD\r\n"
report_pci0:
    .ascii "-------- -------- --------\r\n"
report_pci1:
    .ascii "-------- -------- --------\r\n"
report_end:
    .p2align 1
report_path:
    # \\BMO-X2\\BOOTLOG.TXT
    .short 92,66,77,79,45,88,50,92,66,79,79,84,76,79,71,46,84,88,84,0
