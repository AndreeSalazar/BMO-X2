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
    jmp bmo_test_gs_dispatch
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
