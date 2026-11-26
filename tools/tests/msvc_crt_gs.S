#ifndef BMO_GS_COOKIE
#error BMO_GS_COOKIE must be supplied by the QEMU test build
#endif

.data
.p2align 3
.globl __security_cookie
__security_cookie:
    .quad BMO_GS_COOKIE

.text
#ifdef BMO_GS_NATIVE
.globl bmo_test_gs_call_client
bmo_test_gs_call_client:
    push %rsi
.Lpush_rsi:
    push %rdi
.Lpush_rdi:
    push %rbp
.Lpush_rbp:
    sub $160, %rsp
.Lallocate:
    mov %rbx, 32(%rsp)
.Lsave_rbx:
    movdqa %xmm6, 48(%rsp)
.Lsave_xmm6:
    lea 128(%rsp), %rbp
.Lset_frame:
    # Record independently observable call boundaries and saved registers.
    lea .Lclient_return(%rip), %rax
    mov %rax, bmo_gs_expected(%rip)
    mov %rsp, bmo_gs_expected+96(%rip)
    mov 184(%rsp), %rax
    mov %rax, bmo_gs_expected+16(%rip)
    lea 192(%rsp), %rax
    mov %rax, bmo_gs_expected+24(%rip)
    mov %rbx, bmo_gs_expected+32(%rip)
    mov %rsi, bmo_gs_expected+40(%rip)
    mov %rdi, bmo_gs_expected+48(%rip)
    mov %r12, bmo_gs_expected+56(%rip)
    movdqu %xmm6, bmo_gs_expected+64(%rip)
    mov 160(%rsp), %rax
    mov %rax, bmo_gs_expected+80(%rip)
    mov %rbp, bmo_gs_expected+88(%rip)
    mov $0x12340003, %ebx
    mov $0x12340006, %esi
    mov $0x12340007, %edi
    pcmpeqd %xmm6, %xmm6
    jmp bmo_test_gs_chained_fragment

.globl bmo_test_gs_chained_fragment
bmo_test_gs_chained_fragment:
    mov %r12, -64(%rbp)
.Lsave_r12:
    mov $0x1234000c, %r12d
    # The callee shadow space and dynamic area are below the fixed frame.
    sub $64, %rsp
    mov %rsp, bmo_gs_expected+8(%rip)
    call bmo_crt_client_main
.Lclient_return:
    mov -64(%rbp), %r12
    movdqa -80(%rbp), %xmm6
    mov -96(%rbp), %rbx
    lea 32(%rbp), %rsp
    pop %rbp
    pop %rdi
    pop %rsi
    ret
.Lfragment_end:

    # The later R12 save is described by a chained RUNTIME_FUNCTION.
    .section .xdata,"dr"
    .p2align 2
.Lprimary_unwind:
    .byte 1, .Lset_frame-bmo_test_gs_call_client, 10, 0x85
    .byte .Lset_frame-bmo_test_gs_call_client, 0x03  # SET_FPREG RBP, +128
    .byte .Lsave_xmm6-bmo_test_gs_call_client, 0x68  # SAVE_XMM128 XMM6
    .short 3
    .byte .Lsave_rbx-bmo_test_gs_call_client, 0x34   # SAVE_NONVOL RBX
    .short 4
    .byte .Lallocate-bmo_test_gs_call_client, 0x01   # ALLOC_LARGE (scaled)
    .short 20
    .byte .Lpush_rbp-bmo_test_gs_call_client, 0x50    # PUSH_NONVOL RBP
    .byte .Lpush_rdi-bmo_test_gs_call_client, 0x70    # PUSH_NONVOL RDI
    .byte .Lpush_rsi-bmo_test_gs_call_client, 0x60    # PUSH_NONVOL RSI
.Lfragment_unwind:
    .byte 0x21, .Lsave_r12-bmo_test_gs_chained_fragment, 2, 0x85
    .byte .Lsave_r12-bmo_test_gs_chained_fragment, 0xc4   # SAVE_NONVOL R12
    .short 8
    .rva bmo_test_gs_call_client, bmo_test_gs_chained_fragment, .Lprimary_unwind
    .section .pdata,"dr"
    .p2align 2
    .rva bmo_test_gs_call_client, bmo_test_gs_chained_fragment, .Lprimary_unwind
    .rva bmo_test_gs_chained_fragment, .Lfragment_end, .Lfragment_unwind
    .text

.globl bmo_test_gs_prologue
.seh_proc bmo_test_gs_prologue
bmo_test_gs_prologue:
    mov (%rsp), %rax
    mov %rax, bmo_gs_prologue_expected(%rip)
    lea 8(%rsp), %rax
    mov %rax, bmo_gs_prologue_expected+8(%rip)
    mov %rsi, bmo_gs_prologue_expected+16(%rip)
    mov %rdi, bmo_gs_prologue_expected+24(%rip)
    mov %rbp, bmo_gs_prologue_expected+32(%rip)
    push %rsi
    .seh_pushreg %rsi
    push %rdi
    .seh_pushreg %rdi
    push %rbp
    .seh_pushreg %rbp
    push %rbx
    .seh_pushreg %rbx
    mov $0x43210006, %esi
    mov $0x43210007, %edi
.globl bmo_test_gs_prologue_fault
bmo_test_gs_prologue_fault:
    ud2
    ud2
.Lprologue_continue:
    sub $40, %rsp
    .seh_stackalloc 40
    lea 32(%rsp), %rbp
    .seh_setframe %rbp, 32
    .seh_endprologue
    add $40, %rsp
    pop %rbx
    pop %rbp
    pop %rdi
.globl bmo_test_gs_epilogue_suffix
bmo_test_gs_epilogue_suffix:
    pop %rsi
    ret
.seh_endproc

.globl bmo_test_gs_dispatch
bmo_test_gs_dispatch:
    mov (%rsp), %rcx
    dec %rcx
    lea 8(%rsp), %rdx
    jmp bmo_gs_dispatch

.globl bmo_test_gs_cpu_fault
bmo_test_gs_cpu_fault:
    ud2
    ud2

.globl bmo_test_gs_cpu_landing
bmo_test_gs_cpu_landing:
    lea bmo_test_gs_cpu_fault(%rip), %rax
    cmp %rax, %rcx
    jne .Linvalid_delivery
    lea bmo_gs_cpu_dispatch(%rip), %rax
    lea .Lcpu_return(%rip), %r10
    jmp .Lcapture_context

.globl bmo_test_gs_prologue_landing
bmo_test_gs_prologue_landing:
    lea bmo_test_gs_prologue_fault(%rip), %rax
    cmp %rax, %rcx
    jne .Lprologue_failed
    lea bmo_gs_cpu_prologue(%rip), %rax
    lea .Lprologue_continue(%rip), %r10

.Lcapture_context:
    cmp $6, %r8d
    jne .Ldelivery_failed
    cmp %rsp, %rdx
    jne .Ldelivery_failed
    # Win64 shadow space followed by CpuContext in msvc_crt_gs_dispatch.cpp.
    sub $296, %rsp
    mov %rcx, 32(%rsp)
    mov %rdx, 40(%rsp)
    mov %r9, 48(%rsp)
    mov %rbx, 56(%rsp)
    mov %rbp, 64(%rsp)
    mov %rsi, 72(%rsp)
    mov %rdi, 80(%rsp)
    mov %r12, 88(%rsp)
    mov %r13, 96(%rsp)
    mov %r14, 104(%rsp)
    mov %r15, 112(%rsp)
    movdqu %xmm6, 120(%rsp)
    movdqu %xmm7, 136(%rsp)
    movdqu %xmm8, 152(%rsp)
    movdqu %xmm9, 168(%rsp)
    movdqu %xmm10, 184(%rsp)
    movdqu %xmm11, 200(%rsp)
    movdqu %xmm12, 216(%rsp)
    movdqu %xmm13, 232(%rsp)
    movdqu %xmm14, 248(%rsp)
    movdqu %xmm15, 264(%rsp)
    mov %r10, 280(%rsp)
    lea 32(%rsp), %rcx
    call *%rax
    mov 280(%rsp), %r10
    add $296, %rsp
    jmp *%r10
.Ldelivery_failed:
    xor %eax, %eax
    jmp *%r10
.Lprologue_failed:
    xor %eax, %eax
    jmp .Lprologue_continue
.Lcpu_return:
    ret
.Linvalid_delivery:
    xor %eax, %eax
    ret

.globl __report_gsfailure
__report_gsfailure:
    cmpl $1, bmo_gs_dispatch_active(%rip)
    jne .Lcookie_mismatch
    mov $0x47534844, %eax
    ud2
.Lcookie_mismatch:
#else
.globl __security_check_cookie
__security_check_cookie:
    cmp __security_cookie(%rip), %rcx
    jne .Lcookie_mismatch
    ret
.Lcookie_mismatch:
#endif
    # Existing CPL3 abort handler reports RAX and tears down the process.
    mov $0x4753434b, %eax
    ud2
