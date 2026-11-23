# One translation window on the measured AMD platform. Win64 ABI.
# RCX: writable UC alias of AMD-Vi. RDX: validated private session.
# Session layout: physical_mmio.S receipt (72 B), TSC budget (8 B),
# lifecycle (8 B: zero/new, 1/active, 2/pinned, 3/closed).
# The caller has validated the EFI reservations and requester topology,
# blocked remote translation with DTE.I=0, and stopped every DMA engine. xHCI
# may start within the window with its private identity-mapped domain.
# All register writes are to AMD-Vi.
# NVIDIA PCI Bus Master stays closed throughout this xHCI-only trial.
# Return 0 rejected, 1 success, 2 failed with original bases restored,
# 3 unverified recovery (keep every reservation pinned).
.text
.set PHYSICAL_TSC_BUDGET, 72
.set PHYSICAL_LIFECYCLE, 80
.set PHYSICAL_IDLE_CONTROL, 0x0000220000000400
.set PHYSICAL_USB_INVALIDATE, (2 << 60 | 0x2b03)

.globl amdvi_open_physical_translation
amdvi_open_physical_translation:
.Lopen_physical_translation:
    test %rdx, %rdx
    jz .Lphysical_window_reject
    cmpq $0, PHYSICAL_LIFECYCLE(%rdx)
    jne .Lphysical_window_reject
    cmpq $0, PHYSICAL_TSC_BUDGET(%rdx)
    je .Lphysical_window_reject
    cmpq $1000000000, PHYSICAL_TSC_BUDGET(%rdx)
    ja .Lphysical_window_reject
    push %r12
    push %r13
    sub $104, %rsp
    mov %rcx, %r12
    mov %rdx, %r13
    call .Lstage_physical_registers
    cmp $3, %eax
    je .Lphysical_window_pin
    cmp $2, %eax
    je .Lphysical_window_closed
    cmp $1, %eax
    jne .Lphysical_window_return
    call .Lphysical_window_args
    # The reserved command page is identity mapped WB in supervisor RAM.
    mov 8(%r13), %rdx
    call .Lstart_translation
    cmp $1, %eax
    je .Lphysical_window_open
    cmp $3, %eax
    je .Lphysical_window_pin
    # Rejected before activation or verified stop. Restore only if the
    # stopped unit and its queues still match the private receipt.
    call .Lphysical_window_restore
    cmp $1, %eax
    jne .Lphysical_window_return
    mov $2, %eax
.Lphysical_window_closed:
    movq $3, PHYSICAL_LIFECYCLE(%r13)
    jmp .Lphysical_window_return
.Lphysical_window_open:
    movq $1, PHYSICAL_LIFECYCLE(%r13)
    jmp .Lphysical_window_return

# The caller first stops xHCI and verifies that bus mastering and pending
# transactions have cleared for the requesters allowed during the window.
.globl amdvi_close_physical_translation
amdvi_close_physical_translation:
.Lclose_physical_translation:
    test %rdx, %rdx
    jz .Lphysical_window_reject
    cmpq $1, PHYSICAL_LIFECYCLE(%rdx)
    jne .Lphysical_window_reject
    push %r12
    push %r13
    sub $104, %rsp
    mov %rcx, %r12
    mov %rdx, %r13
    call .Lphysical_window_args
    call .Lstop_translation
    cmp $1, %eax
    jne .Lphysical_window_pin
    call .Lphysical_window_restore
    jmp .Lphysical_window_return

.Lphysical_window_args:
    lea 40(%rsp), %r9              # Caller frame + Win64 shadow space.
    movabs $PHYSICAL_IDLE_CONTROL, %rax
    mov %rax, (%r9)
    mov 48(%r13), %rax
    mov %rax, 8(%r9)
    mov 56(%r13), %rax
    mov %rax, 16(%r9)
    mov 64(%r13), %rax
    mov %rax, 24(%r9)
    movabs $PHYSICAL_USB_INVALIDATE, %rax
    mov %rax, 32(%r9)
    movq $1, 40(%r9)               # Global invalidation plus the xHCI DTE.
    mov PHYSICAL_TSC_BUDGET(%r13), %r8
    mov %r12, %rcx
    ret
.Lphysical_window_restore:
    # Entered only with translation stopped. A latched fault or nonzero
    # head/tail makes the existing restore guard refuse to free the pages.
    mov %r12, %rcx
    mov %r13, %rdx
    sub $40, %rsp
    call .Lrestore_physical_registers
    add $40, %rsp
    cmp $1, %eax
    jne .Lphysical_window_restore_pin
    movq $3, PHYSICAL_LIFECYCLE(%r13)
    ret
.Lphysical_window_restore_pin:
    movq $2, PHYSICAL_LIFECYCLE(%r13)
    mov $3, %eax
    ret
.Lphysical_window_pin:
    movq $2, PHYSICAL_LIFECYCLE(%r13)
    mov $3, %eax
.Lphysical_window_return:
    add $104, %rsp
    pop %r13
    pop %r12
    ret
.Lphysical_window_reject:
    xor %eax, %eax
    ret

#ifndef BMO_PHYSICAL_MMIO_IN_STAGE
#include "physical_mmio.S"
#endif
#include "translation.S"
