# One GMCAPI_CMD_GSP_INIT on the 615 MSGQ v2 boot queues.
# Win64 ABI RCX = GSP BAR0 alias, RDX = private RMARGS physical base,
# R8 = ticks per 10 ms, R9 = PCIe Link Capabilities (high dword)
# and measured PCIe flags (bits 8..23) and PCI revision (bits 0..7).
# Fifth argument = validated GOP console bytes, or zero when unverified.
# Sixth argument = optional, supervisor-only frame capture page.
# Seventh argument = optional AMD-Vi event MMIO alias for the pre-TX sample.
# RAX = {GMCAPI status or observed dword, trial status in high dword}.
# Caller retains the verified GSP domain and RTX Bus Master until return.
.set GSP_TX_HEAD, 0xc00
.set GSP_TX_TAIL, 0xc04
.set GSP_RX_HEAD, 0xc80
.set GSP_RX_TAIL, 0xc84
.set GSP_615_RX_HEADER, 0x42000
.set GSP_615_RX_ENTRY, 0x43000
.set GSP_615_NVDM_GMCAPI, 0x2610de7e
.set GSP_615_INIT_REPLY, 0x01010001
.set GSP_615_PCIE_FLR, 0x002
.set GSP_615_PCIE_UPSTREAM, 0x400

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
    mov %r9d, %r15d
    shr $8, %r15d
    test $~(GSP_615_PCIE_FLR | GSP_615_PCIE_UPSTREAM), %r15d
    jnz .Lgsp_615_receipt

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

    # Fill the unpublished TX slot only after linking the status queue.
    lea GSP_615_TX_ENTRY(%r14), %rdi
    lea .Lgsp_615_request(%rip), %rsi
    mov $(.Lgsp_615_request_end-.Lgsp_615_request)/8, %ecx
    cld
    rep movsq
    movzbl %r9b, %eax
    mov %eax, (GSP_615_TX_ENTRY+.Lgsp_615_revision-.Lgsp_615_request+4)(%r14)
    mov %r9d, %eax
    shr $8, %eax
    shr $32, %r9
    mov %r9d, (GSP_615_TX_ENTRY+.Lgsp_615_link_cap-.Lgsp_615_request+4)(%r14)
    mov %rax, (GSP_615_TX_ENTRY+.Lgsp_615_pcie_flags-.Lgsp_615_request+8)(%r14)
    mov 88(%rsp), %rax
    mov %rax, (GSP_615_TX_ENTRY+.Lgsp_615_console_mem-.Lgsp_615_request+8)(%r14)

    mov 96(%rsp), %rdi
    test %rdi, %rdi
    jz .Lgsp_615_publish
    lea GSP_615_TX_ENTRY(%r14), %rsi
    mov $(GSP_615_INIT_FRAME_BYTES/8), %ecx
    rep movsq
    mov 104(%rsp), %rdx
    test %rdx, %rdx
    jz .Lgsp_615_publish
    mov 0x18(%rdx), %eax
    mov %eax, (GSP_INIT_EVENT_TAILS+8-GSP_615_INIT_FRAME_BYTES)(%rdi)
    # Preserve early firmware evidence before INIT can change it. LOGINIT
    # is a 16-page ring with one producer word and 8191 data words.
    lea (GSP_PRE_TX_LOG-GSP_615_INIT_FRAME_BYTES)(%rdi), %rdi
    lea GSP_LOGINIT_OFFSET(%r14), %rsi
    lfence
    mov (%rsi), %r8
    cmp $GSP_PRE_TX_LOG_WORDS, %r8
    jb .Lgsp_615_publish
    lea -GSP_PRE_TX_LOG_WORDS(%r8), %r9
    mov $GSP_PRE_TX_LOG_WORDS, %ecx
.Lgsp_615_early_log:
    mov %r9, %rax
    xor %edx, %edx
    mov $8191, %r10d
    div %r10
    mov 8(%rsi,%rdx,8), %rax
    mov %rax, 8(%rdi)
    add $8, %rdi
    inc %r9
    dec %ecx
    jnz .Lgsp_615_early_log
    lfence
    cmp %r8, (%rsi)
    jne .Lgsp_615_publish
    mov %r8, -8*GSP_PRE_TX_LOG_WORDS(%rdi)
.Lgsp_615_publish:
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

# Win64 RCX = trusted GOP handoff, RDX = verified GPU BAR1 address.
# The size-only INIT field can cover a console at the aperture start.
.globl nvidia_gsp_console_bytes_615
nvidia_gsp_console_bytes_615:
.Lgsp_console_bytes_615:
    xor %eax, %eax
    test %rdx, %rdx
    jz .Lgsp_console_done
    cmp %rdx, 0x10(%rcx)
    jne .Lgsp_console_done
    cmpl $1, 0x2c(%rcx)
    ja .Lgsp_console_done
    mov 0x20(%rcx), %edx
    test %edx, %edx
    jz .Lgsp_console_done
    mov 0x28(%rcx), %r8d
    cmp %edx, %r8d
    jb .Lgsp_console_done
    cmp $8192, %r8d
    ja .Lgsp_console_done
    mov 0x24(%rcx), %edx
    cmp $4096, %edx
    ja .Lgsp_console_done
    imul %rdx, %r8
    shl $2, %r8
    test $4095, %r8d
    jnz .Lgsp_console_done
    cmp 0x18(%rcx), %r8
    cmovbe %r8, %rax
.Lgsp_console_done:
    ret

# Win64 RCX = endpoint Device Capabilities, EDX = bridge class/revision,
# R8 = bridge primary/secondary/subordinate buses, R9 = bridge PCIe header.
# The caller has already checked the bridge vendor/device and type-1 header.
# Reject absent, indirect, or misidentified ports without executing FLR.
.globl nvidia_gsp_pcie_flags_615
nvidia_gsp_pcie_flags_615:
.Lgsp_pcie_flags_615:
    xor %eax, %eax
    cmp $-1, %ecx
    je .Lgsp_pcie_port
    test $0x10000000, %ecx      # PCI_EXP_DEVCAP_FLR
    jz .Lgsp_pcie_port
    mov $GSP_615_PCIE_FLR, %eax
.Lgsp_pcie_port:
    shr $8, %edx
    cmp $0x060400, %edx
    jne .Lgsp_pcie_done
    and $0xffffff, %r8d
    cmp $0x292900, %r8d        # Primary 00, direct secondary/subordinate 29.
    jne .Lgsp_pcie_done
    and $0x00ff00ff, %r9d      # Ignore next capability pointer.
    cmp $0x00410010, %r9d      # PCIe root port, capability v1 or v2.
    je .Lgsp_pcie_direct
    cmp $0x00420010, %r9d
    jne .Lgsp_pcie_done
.Lgsp_pcie_direct:
    or $GSP_615_PCIE_UPSTREAM, %eax
.Lgsp_pcie_done:
    ret

# Read-only init failure snapshot. Win64: RCX = GSP, RDX = selected log,
# R8 = event MMIO, R9 = private event ring, fifth arg = summary,
# sixth arg = private 17-page trace (event page, then 64-KiB log).
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
    gsp_u64 0x1022, GSP_NOTIFY_OP_IOVA # NOTIFY_OP_SHARED_SURF_PHYS_ADDR.
.Lgsp_615_console_mem:
    gsp_u64 0x1031, 0             # CONSOLE_MEM_SIZE, patched from the GOP handoff.
    gsp_u64 0x1032, 0x7ffffffff000
    gsp_u32 0x70, 1               # HOST_ARCH_X86_64.
    gsp_u32 0x71, 0               # HOST_OS_OTHER.
    gsp_u32 0x78, 4096
    gsp_u32 0x10, 0x88000         # PCI configuration mirror offset in BAR0.
    gsp_u32 0x11, 4096
.Lgsp_615_link_cap:
    gsp_u32 0x52, 0               # PCIE_LINK_CAP, sampled before publication.
    # OpenRM 615.78.08 completed INIT on this board with these NVKV keys.
    # Report only capabilities backed by the native host. In particular,
    # Linux's VF resources, ACPI cache and registry are private to that host.
    gsp_u32 0x20, 0               # PCIE_ATOMICS_CPL_DEV_CAP_MASK.
    gsp_u32 0x31, 0               # CHIPSET_L1SS_ENABLE.
    gsp_u32 0x41, 0               # VIRTUAL_CONFIG_BITS.
    gsp_u32 0x50, 0               # PCIE_POWER_CONTROL_VALUE.
    gsp_u32 0x51, 0               # PF0_DEVICE_CONTROL2_REG policy.
    gsp_u32 0x60, 0               # GRID_BUILD_CSP.
    gsp_u32 0x80, 0               # VF_TOTAL_VFS exposed by this host.
    gsp_u32 0x81, 0               # VF_FIRST_VF_OFFSET.
.Lgsp_615_pcie_flags:
    gsp_u64 0x1000, 0             # Filled only from PCI config observations.
    gsp_u64 0x1001, 0             # No host platform services advertised.
    gsp_u64 0x1002, 0             # No host display or power callbacks.
    gsp_u64 0x1003, 0             # No host VF services advertised.
    gsp_u64 0x1030, 0             # PCIE_ATOMICS_OP_MASK.
    gsp_u64 0x1040, 0             # SYS_TIMER_OFFSET_NS.
    gsp_u64 0x1050, 0             # VF_FIRST_BAR0_ADDRESS.
    gsp_u64 0x1051, 0             # VF_FIRST_BAR1_ADDRESS.
    gsp_u64 0x1052, 0             # VF_FIRST_BAR2_ADDRESS.
    .long 0x30001100, 7
    .asciz "BMO-X2"
    .zero 1
    .long 0x30001101, 10          # KERNEL_DRIVER_VERSION_STRING.
    .asciz "615.78.08"
    .zero 6
    gsp_u32 0x1102, 0            # No NVIDIA internal build changelist.
    gsp_u32 0x1110, 3            # UNSTABLE_INTERFACE_SUPPORT is U32.
.Lgsp_615_cl_flags:
    # This board-only request follows successful PCI config reads in physical_falcon.inc.
    gsp_u64 0x1033, 1            # CL_FLAGS_PCIE_CONFIG_ACCESSIBLE only.
.Lgsp_615_request_end:
    .if (.Lgsp_615_request_end-.Lgsp_615_request) != GSP_615_INIT_FRAME_BYTES
    .error "Update the bounded GSP_INIT diagnostic frame length"
    .endif
    .if (.Lgsp_615_revision-.Lgsp_615_request) != 80 || (.Lgsp_615_link_cap-.Lgsp_615_request) != 256 || (.Lgsp_615_pcie_flags-.Lgsp_615_request) != 328 || (.Lgsp_615_console_mem-.Lgsp_615_request) != 184
    .error "Update the GSP_INIT diagnostic field offsets"
    .endif
    .if (.Lgsp_615_cl_flags-.Lgsp_615_request) != 528
    .error "Update the GSP_INIT Core Logic diagnostic field offset"
    .endif
    .if (.Lgsp_615_request_end-.Lgsp_615_request) > 4096
    .error "GSP_INIT must fit one MSGQ slot"
    .endif
.purgem gsp_u32
.purgem gsp_u64
