# Read PCI Command in segment 0 after xHCI startup. R10 selects one
# bounded scalar. The snapshot writes only its reserved context range.
dma_census:
    cmp $DMA_CENSUS_MAX*2, %r10
    ja .Lcensus_denied
    cmpb $0, DMA_CENSUS_READY(%rbp)
    jne .Lcensus_result
    test %r10d, %r10d
    jnz .Lcensus_denied
    push %rbx
    mov $0xcf8, %dx
    in %dx, %eax
    mov %eax, %r11d
    mov $0x80000000, %r8d
    xor %esi, %esi                  # Total BME-enabled functions.
    xor %ecx, %ecx                  # Stored records (maximum 64).
    lea DMA_CENSUS_ROWS(%rbp), %rdi
.Lcensus_next:
    mov %r8d, %eax
    call .Lcensus_read_pci
    cmp $0xffff, %ax
    je .Lcensus_advance
    mov %eax, %ebx
    lea 4(%r8), %eax
    call .Lcensus_read_pci
    test $4, %al
    jz .Lcensus_advance
    inc %esi
    cmp $DMA_CENSUS_MAX, %ecx
    jae .Lcensus_advance
    movzwl %ax, %eax
    shl $16, %eax
    mov %r8d, %r9d
    shr $8, %r9d
    movzwl %r9w, %r9d
    or %r9d, %eax
    mov %eax, (%rdi)               # BDF, PCI Command.
    mov %ebx, 4(%rdi)              # Vendor and device ID.
    lea 8(%r8), %eax
    call .Lcensus_read_pci
    shr $8, %eax
    mov %rax, 8(%rdi)              # 24-bit class code.
    add $16, %rdi
    inc %ecx
.Lcensus_advance:
    add $256, %r8d
    cmp $0x81000000, %r8d
    jne .Lcensus_next
    mov %r11d, %eax
    out %eax, %dx
    mov $0xffff, %eax
    cmpb $1, %gs:0x3c8
    jne .Lcensus_save
    movzwl %gs:0x360, %eax
.Lcensus_save:
    shl $16, %eax
    or %ecx, %eax
    shl $32, %rsi
    or %rsi, %rax
    mov %rax, DMA_CENSUS_HEADER(%rbp)
    movb $1, DMA_CENSUS_READY(%rbp)
    pop %rbx
.Lcensus_result:
    mov DMA_CENSUS_HEADER(%rbp), %rax
    test %r10d, %r10d
    jz .Lcensus_done
    movzwl %ax, %ecx
    add %ecx, %ecx
    cmp %ecx, %r10d
    ja .Lcensus_denied
    mov (DMA_CENSUS_ROWS-8)(%rbp,%r10,8), %rax
.Lcensus_done:
    ret
.Lcensus_denied:
    mov $257, %eax
    ret
.Lcensus_read_pci:
    out %eax, %dx
    add $4, %dx
    in %dx, %eax
    sub $4, %dx
    ret
