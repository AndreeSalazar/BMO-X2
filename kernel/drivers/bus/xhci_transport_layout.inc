# RDI: capability snapshot. R9D: RTSOFF, R10D: DBOFF. ZF: admissible.
# Preserve ECX (PCI selector) and R8 (DMA reservation).
# Banks may share the capability page, but never operational/port registers
# or each other. Only interrupter zero and doorbell zero are used here.
xhci_transport_layout:
    test $0x1f, %r9d
    jnz transport_layout_invalid
    test $3, %r10d
    jnz transport_layout_invalid
    cmp $0xffc0, %r9d
    ja transport_layout_invalid
    cmp $0xfffc, %r10d
    ja transport_layout_invalid
    mov %r9d, %eax
    and $0xfff, %eax
    cmp $0xfc0, %eax
    ja transport_layout_invalid
    movzbl (%rdi), %eax
    movzbl 7(%rdi), %edx
    shl $4, %edx
    lea 0x400(%rax,%rdx), %eax
    cmp %eax, %r9d
    jb transport_layout_invalid
    cmp %eax, %r10d
    jb transport_layout_invalid
    lea 0x40(%r9), %eax
    cmp %eax, %r10d
    jae transport_layout_valid
    lea 4(%r10), %eax
    cmp %eax, %r9d
    jb transport_layout_invalid
transport_layout_valid:
    xor %eax, %eax
    ret
transport_layout_invalid:
    or $1, %eax
    ret
