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
.seh_proc bmo_test_gs_call_client
bmo_test_gs_call_client:
    push %rbx
    .seh_pushreg %rbx
    push %rsi
    .seh_pushreg %rsi
    push %rdi
    .seh_pushreg %rdi
    sub $32, %rsp
    .seh_stackalloc 32
    .seh_endprologue
    # Record independently observable call boundaries and saved registers.
    lea .Lclient_return(%rip), %rax
    mov %rax, bmo_gs_expected(%rip)
    mov %rsp, bmo_gs_expected+8(%rip)
    mov 56(%rsp), %rax
    mov %rax, bmo_gs_expected+16(%rip)
    lea 64(%rsp), %rax
    mov %rax, bmo_gs_expected+24(%rip)
    mov %rbx, bmo_gs_expected+32(%rip)
    mov %rsi, bmo_gs_expected+40(%rip)
    mov %rdi, bmo_gs_expected+48(%rip)
    mov $0x12340003, %ebx
    mov $0x12340006, %esi
    mov $0x12340007, %edi
    call bmo_crt_client_main
.Lclient_return:
    add $32, %rsp
    pop %rdi
    pop %rsi
    pop %rbx
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
    cmp $6, %r8d
    jne .Linvalid_delivery
    lea bmo_test_gs_cpu_fault(%rip), %rax
    cmp %rax, %rcx
    jne .Linvalid_delivery
    cmp %rsp, %rdx
    jne .Linvalid_delivery
    # Win64 shadow space followed by CpuContext in msvc_crt_gs_dispatch.cpp.
    sub $120, %rsp
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
    lea 32(%rsp), %rcx
    call bmo_gs_cpu_dispatch
    add $120, %rsp
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
