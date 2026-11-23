# Win64 ABI. Caller holds the final LoaderData reservation and AMD-Vi is off.
# RCX is the identity-mapped physical DTE base, RDX the verified FWSEC image
# base (zero to deny), R8 the start of the firmware reservation.
# Two pages after the existing AMD-Vi and CPU-alias workspace are
# private to this root. The broad GSP tree is left detached.
# Return 0 invalid arguments, 1 deny only, 2 FWSEC-only read mapping.
.text
.globl amdvi_stage_fwsec_domain
amdvi_stage_fwsec_domain:
.Lfwsec_domain:
    test $4095, %ecx
    jnz .Lfwsec_domain_invalid
    cmp $0x100000, %rcx
    jb .Lfwsec_domain_invalid
    cmp $(0x10000000-0x209000), %rcx
    ja .Lfwsec_domain_invalid
    # Detach graphics before considering the firmware pages. GPU audio and
    # the other requesters retain the existing deny or USB DTEs.
    lea (0x2900*32)(%rcx), %r9
    movabs $0x6000000000000403, %rax
    lea 0x200000(%rcx), %r10
    or %rax, %r10
    mov %r10, (%r9)
    movq $0, 8(%r9)
    movq $0, 16(%r9)
    movq $0, 24(%r9)
    cmp $0x100000, %r8
    jb .Lfwsec_domain_denied
    cmp %r8, %rdx
    jb .Lfwsec_domain_denied
    test $4095, %edx
    jnz .Lfwsec_domain_denied
    lea -0xf000(%rcx), %rax
    cmp %rax, %rdx
    ja .Lfwsec_domain_denied

    lea 0x207000(%rcx), %r10
    mov %r10, %r11
    mov $1024, %ecx
.Lfwsec_domain_clear:
    movq $0, (%r11)
    add $8, %r11
    dec %ecx
    jnz .Lfwsec_domain_clear
    lea 4096(%r10), %r11
    # The exact 15 FWSEC pages must fit the 2 MiB IOVA leaf (0xa000000).
    movabs $0x2000000000000201, %rax
    or %r11, %rax
    mov %rax, ((0x0a107000>>21)*8)(%r10)
    lea (((0x0a107000>>12)&511)*8)(%r11), %r11
    movabs $0x2000000000000001, %rax
    or %rdx, %rax
    mov $15, %ecx
.Lfwsec_domain_pages:
    mov %rax, (%r11)
    add $4096, %rax
    add $8, %r11
    dec %ecx
    jnz .Lfwsec_domain_pages

    movabs $0x2000000000000403, %rax
    or %r10, %rax
    mov %rax, (%r9)
    movq $5, 8(%r9)
    mov $2, %eax
    ret
.Lfwsec_domain_denied:
    mov $1, %eax
    ret
.Lfwsec_domain_invalid:
    xor %eax, %eax
    ret
