.text
#include "../../drivers/bus/xhci_dma_layout.inc"
#ifdef XHCI_COMMAND_PROBE
#define XHCI_RESERVE_PAGES XHCI_PROBE_PAGES
#else
#define XHCI_RESERVE_PAGES XHCI_QUEUE_PAGES
#endif
# Reserve the context and payload inside the CASM fixture's identity map.
.globl desktop_media_alloc
desktop_media_alloc:
    sub $40, %rsp
    movq $0x0fffffff, 32(%rsp)
    mov $1, %ecx                 # AllocateMaxAddress
    mov $2, %edx                 # EfiLoaderData
    mov $32, %r8d
    lea 32(%rsp), %r9
    call *0x28(%r14)
    test %rax, %rax
    js finish
    mov 32(%rsp), %rbp
    mov %rbp, %rdi
    xor %eax, %eax
    mov $0x4000, %ecx
    rep stosq
    movq $0x0fffffff, 32(%rsp)
    mov $1, %ecx
    mov $1, %edx                 # EfiLoaderCode
    mov $1, %r8d
    lea 32(%rsp), %r9
    call *0x28(%r14)
    test %rax, %rax
    js finish
    mov 32(%rsp), %rax
    mov %rax, 8(%rbp)
#ifdef RMLUI_MEDIA
    # The private large UI loader must own this range before ExitBootServices.
    movq $0x04000000, 32(%rsp)
    mov $2, %ecx                 # AllocateAddress
    mov $2, %edx                 # EfiLoaderData
    mov $4096, %r8d              # 16 MiB, including the user stack
    lea 32(%rsp), %r9
    call *0x28(%r14)
    test %rax, %rax
    js finish
    movabs $0x2131565345524955, %rax # UIRESV1!
    mov %rax, 0x700(%rbp)
    movq $0x04000000, 0x708(%rbp)
    movq $4096, 0x710(%rbp)
    jmp context_ready
#else
    # Reserve contiguous pages for the selected xHCI controller.
    # Context offsets B8/C0 describe the reservation, not a DMA grant.
    movq $0x0fffffff, 32(%rsp)
    mov $1, %ecx
    mov $2, %edx
    mov $XHCI_RESERVE_PAGES, %r8d
    lea 32(%rsp), %r9
    call *0x28(%r14)
    test %rax, %rax
    js context_ready
    mov 32(%rsp), %rdi
    mov %rdi, 0xb8(%rbp)
    movq $XHCI_RESERVE_PAGES, 0xc0(%rbp)
    xor %eax, %eax
    mov $(512 * XHCI_RESERVE_PAGES), %ecx
    cld
    rep stosq
#endif
context_ready:
    movabs $0x2134364c4154454d, %rax
    mov %rax, (%rbp)
    xor %eax, %eax
finish:
    add $40, %rsp
    ret
