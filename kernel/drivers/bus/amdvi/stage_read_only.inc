# Build a detached mode-2 AMD-Vi tree in prezeroed supervisor RAM.
# RDI = physical root (identity mapped), RSI = payload physical base,
# EDX = payload pages (nonzero), ECX = first 2 MiB IOVA index.
# Caller validates alignment, backing reservation and tree geometry.
# Only RAX, RCX, RDX, RSI, RDI and R8 are clobbered.
amdvi_stage_read_only:
    cld
    movabs $0x2000000000000201, %r8
    lea 4096(%rdi), %rax
    push %rax
    lea (%rdi,%rcx,8), %rdi
    lea 511(%rdx), %ecx
    shr $9, %ecx
.Lstage_dma_root:
    or %r8, %rax
    stosq
    add $4096, %rax
    dec %ecx
    jne .Lstage_dma_root

    pop %rdi
    movabs $0x2000000000000001, %r8
    mov %rsi, %rax
    mov %edx, %ecx
.Lstage_dma_leaf:
    or %r8, %rax
    stosq
    add $4096, %rax
    dec %ecx
    jne .Lstage_dma_leaf
    ret
