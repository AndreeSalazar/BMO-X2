#include "layout.inc"
#include "../xhci_dma_layout.inc"
.text
# Controller state in GS: 740 runtime,748 doorbells,750 operational,758 DMA,
# 760 command index,770 role mask (1 keyboard,2 mouse),778 root port,
# 780 consumed events,788 reports,798 last report kind,7a0 last CC,
# 7a4 residual,7ac phase,7b0 expected TRB,7b8 event type,7bc slot,
# 7bd DCI,7be Enable Slot flag,7bf returned slot. No pointer is user writable.
xhci_test_command:
    push %rbx
    movl $100, %gs:0x7ac
    movzbl %gs:0x378, %eax
    dec %eax
    cmp $1, %eax
    ja native_init_return
    mov 0xb8(%rbp), %r8
    cmpq $NATIVE_DMA_PAGES, 0xc0(%rbp)
    jne native_init_return
    cmp $0x100000, %r8
    jb native_init_return
    cmp $(0x10000000 - 4096*NATIVE_DMA_PAGES), %r8
    ja native_init_return
    test $4095, %r8d
    jnz native_init_return
    call xhci_validate_dma
    jne native_init_return
    movb $1, %gs:0x3c4
    cmpb $2, %gs:0x374
    jb native_init_return
    cmpb $32, %gs:0x377
    ja native_init_return
    cmpl $4, %gs:0x3bc
    ja native_init_return
    mov 0x18(%rdi), %r9d
    mov 0x14(%rdi), %r10d
    mov %r9d, %gs:0x3f0
    mov %r10d, %gs:0x3f4
    call xhci_transport_layout
    jne native_init_return
    mov %r10d, %eax
    and $4095, %eax
    cmp $4084, %eax          # Three doorbells must fit in the mapped page.
    ja native_init_return
    lea 12(%r10), %eax
    cmp %eax, %r9d
    jae native_banks_disjoint
    lea 0x40(%r9), %eax
    cmp %eax, %r10d
    jb native_init_return
native_banks_disjoint:
    mov %r9d, %edx
    call xhci_transport_mmio
    jne native_init_return
    mov %r10d, %edx
    call xhci_transport_mmio
    jne native_init_return
    mov 0x1e000(%rbp), %rax
    or $2, %al
    mov %rax, 0x1e000(%rbp)
    mov %r9d, %edx
    and $-4096, %edx
    add %rax, %rdx
    mov %rdx, 0x1e008(%rbp)
    mov %r10d, %edx
    and $-4096, %edx
    add %rax, %rdx
    mov %rdx, 0x1e010(%rbp)
    and $4095, %r9d
    add $0x10001000, %r9
    and $4095, %r10d
    add $0x10002000, %r10
    movzbl (%rdi), %eax
    lea (%rdi,%rax), %r11
    mov %r9, %gs:0x740
    mov %r10, %gs:0x748
    mov %r11, %gs:0x750
    mov %r8, %gs:0x758
    invlpg (%rdi)
    invlpg (%r9)
    invlpg (%r10)
    # Keep the command word before reset as well: even an early failure must
    # revoke bus mastering and invalidate all three supervisor aliases.
    mov $0xcf8, %edx
    in %dx, %eax
    push %rax
    mov %gs:0x360, %eax
    shl $8, %eax
    or $0x80000004, %eax
    out %eax, %dx
    add $4, %edx
    in %dx, %ax
    mov %ax, %gs:0x37c
    pop %rax
    sub $4, %edx
    out %eax, %dx
    movb $1, %gs:0x7c4
    movl $101, %gs:0x7ac
    call xhci_reset
    jne native_init_abort
    movl $102, %gs:0x7ac
    movl $2, 0x38(%r11)
    lea NATIVE_SCRATCH_BEGIN(%r8), %rax
    lea NATIVE_SCRATCH_TABLE(%r8), %rsi
    mov $4, %ecx
native_scratch_next:
    mov %rax, (%rsi)
    add $4096, %rax
    add $8, %rsi
    loop native_scratch_next
    cmpl $0, %gs:0x3bc
    je native_scratch_ready
    lea NATIVE_SCRATCH_TABLE(%r8), %rax
    mov %rax, (%r8)
native_scratch_ready:
    mov %r8, 0x30(%r11)
    lea 0x1001(%r8), %rax
    mov %rax, 0x18(%r11)
    lea NATIVE_EVENT_BEGIN(%r8), %rax
    mov %rax, 0x3000(%r8)
    movl $256, 0x3008(%r8)
    # ERSTBA publishes the table: size and dequeue must be ready first.
    movl $1, 0x28(%r9)
    mov %rax, 0x38(%r9)
    mov %rax, %gs:0x3d0
    movb $1, %gs:0x3cb
    lea 0x3000(%r8), %rax
    mov %rax, 0x30(%r9)
    mov $0xcf8, %edx
    in %dx, %eax
    push %rax
    mov %gs:0x360, %eax
    shl $8, %eax
    or $0x80000004, %eax
    out %eax, %dx
    add $4, %edx
    in %dx, %ax
    mov %ax, %gs:0x37c
    or $4, %ax
    out %ax, %dx
    pop %rax
    sub $4, %edx
    out %eax, %dx
    movb $1, %gs:0x7c4
    movl $103, %gs:0x7ac
    movl $1, (%r11)
    mov $1, %eax
    xor %esi, %esi
    call command_poll
    jne native_init_abort
    movl $104, %gs:0x7ac
    xor %eax, %eax
    mov $0x5c00, %ecx
    call native_command
    jne native_init_abort
    movl $105, %gs:0x7ac
    movb $1, %gs:0x379
    call native_settle
    jne native_init_abort
    movl $106, %gs:0x7ac
    movl $1, %gs:0x778
native_root_next:
    movzbl %gs:0x377, %ecx
    cmp %ecx, %gs:0x778
    ja native_roots_done
    cmpb $3, %gs:0x770
    je native_roots_done
    call native_enumerate_port
    cmpl $0, %gs:0x7c0
    jne native_init_abort
    incl %gs:0x778
    jmp native_root_next
native_roots_done:
    cmpb $0, %gs:0x770
    je native_init_abort
    lea NATIVE_STATE_BEGIN(%r8), %rbx
    call native_arm_if_configured
    jne native_init_abort
    add $64, %rbx
    call native_arm_if_configured
    jne native_init_abort
    movb $1, %gs:0x3c8
    movl $199, %gs:0x7ac
    jmp native_init_return
native_init_abort:
    call xhci_live_stop
native_init_return:
    pop %rbx
    ret

native_settle:
    movl $0, %gs:0x3fc
    push %rbx
    call xhci_transport_ports
    pop %rbx
    ret

native_state_valid:
    lea NATIVE_STATE_BEGIN(%r8), %rax
    cmp %rax, %rbx
    je native_state_return
    add $64, %rax
    cmp %rax, %rbx
native_state_return:
    ret

# A normal report is copied before rearming the same device buffer.
xhci_live_report:
    push %rbx
    cmpb $1, %gs:0x3c8
    jne native_live_empty
    mov %gs:0x758, %r8
    mov %gs:0x740, %r9
    mov %gs:0x748, %r10
    mov %gs:0x750, %r11
    movl $16, %gs:0x7d8
native_live_again:
    mov %gs:0x3d0, %rsi
    mov 12(%rsi), %eax
    and $1, %eax
    cmp %gs:0x3cb, %al
    jne native_live_empty
    mov 12(%rsi), %eax
    mov %eax, %edx
    shr $10, %eax
    and $63, %eax
    cmp $34, %eax
    je native_live_port_change
    cmp $32, %eax
    jne native_live_failed
    test $4, %dl
    jnz native_live_failed
    mov %edx, %eax
    shr $24, %eax
    dec %eax
    cmp $1, %eax
    ja native_live_failed
    shl $6, %eax
    lea NATIVE_STATE_BEGIN(%r8,%rax), %rbx
    cmpb $1, NS_CONFIGURED(%rbx)
    jne native_live_failed
    shr $16, %edx
    and $31, %edx
    cmp NS_DCI(%rbx), %dl
    jne native_live_identity_failed
    mov NS_PENDING(%rbx), %rax
    cmp %rax, (%rsi)
    jne native_live_identity_failed
    mov 8(%rsi), %eax
    mov %eax, %edx
    and $0xffffff, %edx
    mov %edx, %gs:0x7a4
    shr $24, %eax
    mov %al, %gs:0x7a0
    cmp $1, %eax
    je native_live_length
    cmp $13, %eax
    jne native_live_transfer_failed
native_live_length:
    movzwl NS_MPS(%rbx), %eax
    sub %edx, %eax
    jb native_live_transfer_failed
    movzwl NS_LENGTH(%rbx), %edx
    cmp %edx, %eax
    jb native_live_transfer_failed
    cmpb $2, NS_KIND(%rbx)
    je native_live_copy
    cmp %edx, %eax
    jne native_live_transfer_failed
native_live_copy:
    mov NS_BUFFER(%rbx), %rax
    pushq (%rax)
    movzbl NS_KIND(%rbx), %eax
    mov %eax, %gs:0x798
    call native_event_advance
    incq NS_REPORTS(%rbx)
    incq %gs:0x788
    call native_arm_if_configured
    jne native_live_rearm_failed
    pop %rax
    cmpl $2, %gs:0x798
    jne native_live_return
    and $0xffffff, %eax     # Only the three boot-mouse bytes cross the ABI.
    bts $63, %rax
native_live_return:
    pop %rbx
    ret
native_live_rearm_failed:
    pop %rax
    jmp native_live_port_failed
native_live_port_change:
    mov (%rsi), %eax
    shr $24, %eax
    test %eax, %eax
    jz native_live_failed
    movzbl %gs:0x377, %edx
    cmp %edx, %eax
    ja native_live_failed
    lea NATIVE_STATE_BEGIN(%r8), %rbx
    cmp NS_PORT(%rbx), %al
    je native_live_bound_port
    add $64, %rbx
    cmp NS_PORT(%rbx), %al
    jne native_live_ack_port
native_live_bound_port:
    cmpb $1, NS_CONFIGURED(%rbx)
    jne native_live_ack_port
    dec %eax
    shl $4, %eax
    mov 0x400(%r11,%rax), %edx
    and $3, %edx
    cmp $3, %edx
    jne native_live_port_failed
native_live_ack_port:
    mov (%rsi), %eax
    shr $24, %eax
    dec %eax
    shl $4, %eax
    lea 0x400(%r11,%rax), %rdx
    mov (%rdx), %eax
    and $0x0e00c3e0, %eax
    or $0x20000, %eax
    mov %eax, (%rdx)
    call native_event_advance
    decl %gs:0x7d8
    jnz native_live_again
    jmp native_live_empty
native_live_failed:
    movl $210, %gs:0x7ac
    jmp native_live_stop_failed
native_live_identity_failed:
    movl $211, %gs:0x7ac
    jmp native_live_stop_failed
native_live_transfer_failed:
    movl $212, %gs:0x7ac
    jmp native_live_stop_failed
native_live_port_failed:
    movl $213, %gs:0x7ac
native_live_stop_failed:
    call xhci_live_stop
native_live_empty:
    mov $256, %eax
    jmp native_live_return

native_arm_if_configured:
    cmpb $1, NS_CONFIGURED(%rbx)
    jne native_arm_return
    movzbl NS_PORT(%rbx), %eax
    dec %eax
    shl $4, %eax
    mov 0x400(%r11,%rax), %edx
    and $3, %edx
    cmp $3, %edx
    jne native_arm_failed
    mov NS_INDEX(%rbx), %eax
    shl $4, %eax
    add NS_RING(%rbx), %rax
    mov %rax, NS_PENDING(%rbx)
    mov NS_BUFFER(%rbx), %rdx
    mov %rdx, (%rax)
    movzwl NS_MPS(%rbx), %edx
    mov %edx, 8(%rax)
    movzbl NS_CYCLE(%rbx), %edx
    or $0x424, %edx
    sfence
    mov %edx, 12(%rax)
    incl NS_INDEX(%rbx)
    cmpl $16, NS_INDEX(%rbx)
    jne native_arm_ring
    mov NS_RING(%rbx), %rax
    mov %rax, 256(%rax)
    movzbl NS_CYCLE(%rbx), %edx
    or $0x1802, %edx
    mov %edx, 268(%rax)
    xorb $1, NS_CYCLE(%rbx)
    movl $0, NS_INDEX(%rbx)
native_arm_ring:
    sfence
    movzbl NS_SLOT(%rbx), %eax
    movzbl NS_DCI(%rbx), %edx
    mov %edx, (%r10,%rax,4)
native_arm_return:
    xor %eax, %eax
    ret
native_arm_failed:
    or $1, %eax
    ret

xhci_live_stop:
    movb $0, %gs:0x3c8
    cmpb $1, %gs:0x7c4
    jne native_stop_return
    mov %gs:0x750, %r11
    movl $0, (%r11)
    mov $1, %eax
    mov $1, %esi
    call command_poll
    setz %gs:0x37a
    mov $0xcf8, %edx
    in %dx, %eax
    push %rax
    mov %gs:0x360, %eax
    shl $8, %eax
    or $0x80000004, %eax
    out %eax, %dx
    add $4, %edx
    mov %gs:0x37c, %ax
    and $0xfffb, %ax
    out %ax, %dx
    in %dx, %ax
    mov %ax, %gs:0x37e
    pop %rax
    sub $4, %edx
    out %eax, %dx
    movq $0, 0x15400(%rbp)
    movq $0, 0x1e000(%rbp)
    movq $0, 0x1e008(%rbp)
    movq $0, 0x1e010(%rbp)
    invlpg 0x10000000
    invlpg 0x10001000
    invlpg 0x10002000
    movb $0, %gs:0x7c4
native_stop_return:
    ret

#include "events.inc"
#include "enumerate.inc"
