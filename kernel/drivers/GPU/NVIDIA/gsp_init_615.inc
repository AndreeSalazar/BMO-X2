# One GMCAPI_CMD_GSP_INIT on the 615 MSGQ v2 boot queues.
# Win64 ABI RCX = GSP BAR0 alias, RDX = private RMARGS physical base,
# R8 = ticks per 10 ms, R9 = measured PCI revision (8 bits).
# RAX = {GMCAPI status or observed dword, trial status in high dword}.
# Caller retains the verified GSP domain and RTX Bus Master until return.
.set GSP_TX_HEAD, 0xc00
.set GSP_TX_TAIL, 0xc04
.set GSP_RX_HEAD, 0xc80
.set GSP_RX_TAIL, 0xc84
.set GSP_615_TX_ENTRY, 0x3000
.set GSP_615_RX_HEADER, 0x42000
.set GSP_615_RX_ENTRY, 0x43000
.set GSP_615_NVDM_GMCAPI, 0x2610de7e
.set GSP_615_INIT_REPLY, 0x01010001

.globl nvidia_gsp_init_615
nvidia_gsp_init_615:
.Lgsp_init_615:
    push %rbx
    push %rsi
    push %rdi
    push %r13
    push %r14
    push %r15
    mov %rcx, %r13
    mov %rdx, %r14
    mov %r8, %rbx
    mov $0x805, %r11d
    xor %eax, %eax
    test %r14, %r14
    jz .Lgsp_615_receipt
    test $4095, %r14d
    jnz .Lgsp_615_receipt
    cmp $1000000, %rbx
    jb .Lgsp_615_receipt
    cmp $100000000, %rbx
    ja .Lgsp_615_receipt
    cmp $255, %r9d
    ja .Lgsp_615_receipt

    mov $0x803, %r11d
    movl $0, 0x80(%r13)          # appVersion from the verified GA10x monitor.
    mov 0x1388(%r13), %eax
    call .Lvalid_read
    jc .Lgsp_615_receipt
    test $0x80, %al
    jnz .Lgsp_615_processor_ready
    mov 0x40(%r13), %eax
    call .Lvalid_read
    jc .Lgsp_615_receipt
    test %eax, %eax             # LibOS processor suspended while awaiting RM.
    jns .Lgsp_615_receipt
.Lgsp_615_processor_ready:
    # Fill the single unpublished TX slot. The initial queue is zeroed.
    lea GSP_615_TX_ENTRY(%r14), %rdi
    lea .Lgsp_615_request(%rip), %rsi
    mov $(.Lgsp_615_request_end-.Lgsp_615_request)/8, %ecx
    cld
    rep movsq
    mov %r9d, (GSP_615_TX_ENTRY+.Lgsp_615_revision-.Lgsp_615_request+4)(%r14)

    # Match the status header initialized by firmware before linking it.
    mov $0x804, %r11d
    imul $400, %rbx, %r10
    call .Lprep_deadline
.Lgsp_615_link:
    mov GSP_615_RX_HEADER(%r14), %eax
    test %eax, %eax
    jnz .Lgsp_615_validate
    call .Lwithin_deadline
    jb .Lgsp_615_link
    xor %eax, %eax
    jmp .Lgsp_615_receipt
.Lgsp_615_validate:
    mov $0x805, %r11d
    cmp $2, %eax
    jne .Lgsp_615_receipt
    cmpl $0x40000, (GSP_615_RX_HEADER+4)(%r14)
    jne .Lgsp_615_receipt
    cmpl $4096, (GSP_615_RX_HEADER+8)(%r14)
    jne .Lgsp_615_receipt
    cmpl $63, (GSP_615_RX_HEADER+12)(%r14)
    jne .Lgsp_615_receipt
    cmpl $4096, (GSP_615_RX_HEADER+16)(%r14)
    jne .Lgsp_615_receipt
    mov GSP_TX_HEAD(%r13), %eax
    or GSP_TX_TAIL(%r13), %eax
    jnz .Lgsp_615_receipt
    movl $0, GSP_RX_TAIL(%r13)
    cmpl $0, GSP_RX_TAIL(%r13)
    jne .Lgsp_615_receipt
    sfence
    movl $1, GSP_TX_HEAD(%r13)
    mov $0x806, %r11d
    mov GSP_TX_HEAD(%r13), %eax
    cmp $1, %eax
    jne .Lgsp_615_receipt
    imul $400, %rbx, %r10
    call .Lprep_deadline
    xor %edi, %edi               # Monotonic RX consumer, at the startup value.
.Lgsp_615_poll:
    mov GSP_RX_HEAD(%r13), %eax
    call .Lvalid_read
    jc .Lgsp_615_receipt
    mov %eax, %r9d
    sub %edi, %r9d
    cmp $63, %r9d
    ja .Lgsp_615_bad_msg
    test %r9d, %r9d
    jz .Lgsp_615_poll_next
    mov %edi, %eax
    xor %edx, %edx
    mov $63, %ecx
    div %ecx
    shl $12, %edx
    lea GSP_615_RX_ENTRY(%r14,%rdx), %rsi
    lfence
    mov (%rsi), %eax
    cmp $0x4d435450, %eax
    jne .Lgsp_615_bad_msg
    cmpl $0xc0000001, 8(%rsi)
    jne .Lgsp_615_bad_msg
    cmpl $0, 20(%rsi)
    jne .Lgsp_615_bad_msg
    mov 4(%rsi), %ecx
    lea -24(%rcx), %edx
    cmp $(65536-24), %edx
    ja .Lgsp_615_bad_msg
    cmp %edx, 16(%rsi)
    jne .Lgsp_615_bad_msg
    lea 4095(%rcx), %r8d
    shr $12, %r8d
    cmp %r8d, %r9d
    jb .Lgsp_615_poll_next
    mov 12(%rsi), %eax
    cmp $0x2510de7e, %eax       # Ordinary RPC event ahead of GMCAPI reply.
    jne .Lgsp_615_gmc_reply
    # A native message handler must own unsolicited RPC requests.
    # Report this event instead of acknowledging requests we cannot service.
    cmp $56, %ecx
    jb .Lgsp_615_bad_msg
    mov 36(%rsi), %eax
    mov $0x808, %r11d
    jmp .Lgsp_615_receipt
.Lgsp_615_gmc_reply:
    cmp $GSP_615_NVDM_GMCAPI, %eax
    jne .Lgsp_615_bad_msg
    cmp $64, %ecx
    jb .Lgsp_615_bad_msg
    mov 24(%rsi), %eax
    cmp $GSP_615_INIT_REPLY, %eax
    jne .Lgsp_615_bad_msg
    cmpq $1, 32(%rsi)
    jne .Lgsp_615_bad_msg
    mov 44(%rsi), %edx
    or 48(%rsi), %edx
    or 52(%rsi), %edx
    or 56(%rsi), %edx
    or 60(%rsi), %edx
    jnz .Lgsp_615_bad_msg
    sub $64, %ecx
    cmp 28(%rsi), %ecx
    jne .Lgsp_615_bad_msg
    cmp $(48*1024), %ecx
    ja .Lgsp_615_bad_msg
    mov 40(%rsi), %eax
    test %eax, %eax
    jnz .Lgsp_615_ack
    test %ecx, %ecx
    jz .Lgsp_615_bad_msg
    test $7, %ecx
    jnz .Lgsp_615_bad_msg
.Lgsp_615_ack:
    add %r8d, %edi
    mfence
    mov %edi, GSP_RX_TAIL(%r13)
    cmp %edi, GSP_RX_TAIL(%r13)
    jne .Lgsp_615_bad_msg
    mov $0x802, %r11d
    test %eax, %eax
    jnz .Lgsp_615_receipt
    mov $0x801, %r11d
    jmp .Lgsp_615_receipt
.Lgsp_615_poll_next:
    call .Lwithin_deadline
    jb .Lgsp_615_poll
    mov GSP_TX_TAIL(%r13), %eax
    jmp .Lgsp_615_receipt
.Lgsp_615_bad_msg:
    mov $0x807, %r11d
.Lgsp_615_receipt:
    shl $32, %r11
    or %r11, %rax
    pop %r15
    pop %r14
    pop %r13
    pop %rdi
    pop %rsi
    pop %rbx
    ret

# Read-only timeout snapshot. Win64: RCX = GSP, RDX = LOGINIT,
# R8 = event MMIO, R9 = private event ring, fifth arg = summary,
# sixth arg = private 17-page trace (event page, then LOGINIT).
.globl nvidia_gsp_snapshot_615
nvidia_gsp_snapshot_615:
.Lgsp_snapshot_615:
    push %rsi
    push %rdi
    mov 56(%rsp), %r10
    mov 64(%rsp), %r11
    mov 0x40(%rcx), %eax
    mov %eax, 0(%r10)
    mov 0x44(%rcx), %eax
    mov %eax, 4(%r10)
    mov 0x1388(%rcx), %eax
    mov %eax, 8(%r10)
    mov GSP_RX_HEAD(%rcx), %eax
    mov %eax, 12(%r10)
    mov GSP_TX_HEAD(%rcx), %eax
    mov %eax, 4080(%r11)
    mov GSP_TX_TAIL(%rcx), %eax
    mov %eax, 4084(%r11)
    mov (%rdx), %eax
    mov %eax, 16(%r10)
    mov %rdx, %rsi
    lea 4096(%r11), %rdi
    mov $8192, %ecx
    cld
    lfence
    rep movsq
    mov -65536(%rsi), %eax
    mov %eax, 4092(%r11)         # Producer after copying, for comparison.
    mov 0x18(%r8), %rax
    mov %eax, 20(%r10)
    mov 0x20(%r8), %edx
    mov %edx, 24(%r10)
    movl $0, 28(%r10)
    movq $0, 32(%r10)
    movl $0, 4088(%r11)
    # Copy all published entries without advancing Head.
    cmpq $0, 0x10(%r8)
    jne .Lgsp_snapshot_done
    cmp $16, %rax
    jb .Lgsp_snapshot_done
    cmp $4096, %rax
    jae .Lgsp_snapshot_done
    test $15, %al
    jnz .Lgsp_snapshot_done
    lfence
    mov %eax, 4088(%r11)
    mov %eax, %ecx
    shr $3, %ecx
    mov %r9, %rsi
    mov %r11, %rdi
    rep movsq
    mov 4(%r11), %eax
    test $0xf0000000, %eax
    jz .Lgsp_snapshot_done
    and $0xffff0000, %eax       # Event type and flags, without PASID.
    movzwl (%r11), %edx         # PCI requester.
    or %edx, %eax
    mov %eax, 28(%r10)
    mov 8(%r11), %rax
    mov %rax, 32(%r10)
.Lgsp_snapshot_done:
    pop %rdi
    pop %rsi
    ret

.p2align 3
.Lgsp_615_request:
    .long 0x4d435450, .Lgsp_615_request_end-.Lgsp_615_request
    .long 0xc0000001, GSP_615_NVDM_GMCAPI
    .long .Lgsp_615_request_end-.Lgsp_615_gmc, 0
.Lgsp_615_gmc:
    .long 0x00010001, .Lgsp_615_request_end-.Lgsp_615_kv
    .quad 1
    .long 48*1024
    .zero 20
.Lgsp_615_kv:
.macro gsp_u32 key,val
    .long \key, \val
.endm
.macro gsp_u64 key,val
    .long (0x20000000|\key), 1
    .quad \val
.endm
    gsp_u32 0x1, 0x250410de
    gsp_u32 0x2, 0x397d1462
.Lgsp_615_revision:
    gsp_u32 0x3, 0
    gsp_u64 0x1010, 0xfb000000
    gsp_u64 0x1011, 0xd0000000
    gsp_u64 0x1012, 0xe0000000
    gsp_u64 0x1013, 0
    gsp_u64 0x1020, 0x2900
    gsp_u64 0x1031, 0
    gsp_u64 0x1032, 0x7ffffffff000
    gsp_u32 0x70, 1               # HOST_ARCH_X86_64.
    gsp_u32 0x71, 0               # HOST_OS_OTHER.
    gsp_u32 0x78, 4096
    gsp_u32 0x10, 0x88000         # PCI configuration mirror offset in BAR0.
    gsp_u32 0x11, 4096
    gsp_u64 0x1001, 0
    gsp_u64 0x1110, 3
    .long 0x30001100, 7
    .asciz "BMO-X2"
    .zero 1
.Lgsp_615_request_end:
.purgem gsp_u32
.purgem gsp_u64
