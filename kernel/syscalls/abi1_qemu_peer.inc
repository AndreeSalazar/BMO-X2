# Dedicated second address space. Both clients share only the immutable user code.
.Labi1_peer_tables:
    lea (PEER_PDPT*4096+7)(%r12), %rax
    mov %rax, (PEER_ROOT*4096)(%r12)
    mov 0x1000(%r12), %rax
    mov %rax, (PEER_PDPT*4096)(%r12)
    lea (PEER_PD*4096+7)(%r12), %rax
    mov %rax, (PEER_PDPT*4096+8)(%r12)
    lea (PEER_CODE_PT*4096+7)(%r12), %rax
    mov %rax, (PEER_PD*4096)(%r12)
    lea (PEER_STACK_PT*4096+7)(%r12), %rax
    mov %rax, (PEER_PD*4096+64)(%r12)
    lea (USER_FRAME*4096+5)(%r12), %rax
    mov %rax, (PEER_CODE_PT*4096)(%r12)
    lea (PEER_STACK_FRAME*4096+7)(%r12), %rax
    bts $63, %rax
    mov %rax, (PEER_STACK_PT*4096+8)(%r12)
    ret

.Labi1_run_peer:
    push %rbx
    push %rbp
    push %rdi
    push %rsi
    push %r8
    push %r9
    push %r10
    push %r12
    push %r13
    push %r14
    push %r15
    mov %rsp, PEER_PARENT_RSP
    movb $1, PEER_STATE
    movq $PEER_KERNEL_STACK, TSS+4
    mov $PEER_KERNEL_STACK, %esp
    mov SAVED_POOL, %rax
    add $(PEER_ROOT*4096), %rax
    mov %rax, %cr3
    pushq $0x83
    pushq $(USER_STACK+4096)
    pushq $0x202
    pushq $0x8b
    pushq $PEER_ENTRY
    jmp .Labi1_enter_user

.Labi1_peer_dispatch:
    or %rdx, %rax
    or %r8, %rax
    or %r9, %rax
    or %r10, %rax
    jnz .Luser_bad_return
    cmp $3, %rdi
    jne .Luser_bad_return
    cmp $1, %rsi
    jne .Luser_bad_return
    incq ABI_EVENT_SEQ
    movb $2, PEER_STATE
    mov SAVED_POOL, %rax
    mov %rax, %cr3
    movq $(PRIVATE_STACK+0x100000), TSS+4
    mov PEER_PARENT_RSP, %rsp
    pop %r15
    pop %r14
    pop %r13
    pop %r12
    pop %r10
    pop %r9
    pop %r8
    pop %rsi
    pop %rdi
    pop %rbp
    pop %rbx
    jmp .Labi1_sequence
