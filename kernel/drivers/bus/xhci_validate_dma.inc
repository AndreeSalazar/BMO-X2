# Require exclusive coverage by a LoaderData descriptor and disjoint
# reservations for the context, packet and staged desktop image.
xhci_validate_dma:
    push %rcx
    push %rdi
    lea (4096 * XHCI_PROBE_PAGES)(%r8), %rax
    lea 0x20000(%rbp), %rsi
    cmp %rsi, %r8
    jae dma_check_packet
    cmp %rbp, %rax
    ja dma_invalid
dma_check_packet:
    mov 8(%rbp), %rsi
    cmp %rax, %rsi
    jae dma_check_desktop
    add $4096, %rsi
    cmp %rsi, %r8
    jb dma_invalid
dma_check_desktop:
#ifdef XHCI_NATIVE_DUAL
    mov 0x728(%rbp), %rsi
    cmp %rax, %rsi
    jae dma_check_ui
    add $8192, %rsi
    cmp %rsi, %r8
    jb dma_invalid
dma_check_ui:
#endif
#ifdef RMLUI_USB
    # The native UI backing range is separately reserved and never DMA storage.
    cmp $0x05000000, %r8
    jae dma_check_native_staging
    cmp $0x04000000, %rax
    ja dma_invalid
dma_check_native_staging:
#endif
    mov 0xa8(%rbp), %rsi
    cmp %rax, %rsi
    jae dma_check_map
    mov 0xc8(%rbp), %rdx
#ifdef RMLUI_USB
    cmp $513, %rdx
#else
    cmp $5, %rdx
#endif
    ja dma_invalid
    shl $12, %rdx
    add %rdx, %rsi
    jc dma_invalid
    cmp %rsi, %r8
    jb dma_invalid
dma_check_map:
    mov 0x60(%rbp), %rsi
    mov 0x50(%rbp), %rcx
    cmp $40, %rsi
    jb dma_invalid
    cmp $256, %rsi
    ja dma_invalid
    cmp $65536, %rcx
    ja dma_invalid
    lea 0x1000(%rbp), %rdx
    xor %r10d, %r10d
dma_descriptor:
    test %rcx, %rcx
    jz dma_result
    sub %rsi, %rcx
    jb dma_invalid
    mov 8(%rdx), %r9
    cmp %rax, %r9
    jae dma_next
    mov 24(%rdx), %r11
    mov %r11, %rdi
    shr $52, %rdi
    jnz dma_invalid
    shl $12, %r11
    add %r9, %r11
    jc dma_invalid
    cmp %r8, %r11
    jbe dma_next
    cmpl $2, (%rdx)
    jne dma_invalid
    cmp %r8, %r9
    ja dma_invalid
    cmp %rax, %r11
    jb dma_invalid
    inc %r10d
dma_next:
    add %rsi, %rdx
    jmp dma_descriptor
dma_result:
    cmp $1, %r10d
    pop %rdi
    pop %rcx
    ret
dma_invalid:
    or $1, %eax
    pop %rdi
    pop %rcx
    ret

