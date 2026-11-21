# The caller has revalidated the requester's PCI ID and topology.
.Llab_graphics_index:
#ifdef BMO_AMDVI_ROUTED
    mov AMDVI_LAB_EDU_RID(%rbp), %esi
    shl $5, %esi
#else
    mov $0x400, %esi
#endif
    ret

# DIL is zero to close DMA, or 6 to open it. Write only PCI Command.
.Llab_graphics_command:
    call .Llab_graphics_index
    shl $3, %esi
    or $0x80000004, %esi
    mov $0xcf8, %dx
    in %dx, %eax
    mov %eax, %r8d
    mov %esi, %eax
    out %eax, %dx
    add $4, %dx
    in %dx, %ax
    and $~4, %al
    or %dil, %al
    mov %ax, %cx
    out %ax, %dx
    in %dx, %ax
    sub $4, %dx
    xchg %eax, %r8d
    out %eax, %dx
    cmp %cx, %r8w
    je .Llab_graphics_confirmed
    stc
    ret
.Llab_graphics_confirmed:
    clc
    ret
