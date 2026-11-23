# Win64 ABI. RCX: HOST-verified 615.78.08 GA10x BOOTER_LOAD.
# RDX: separate, unpublished 15-page workspace; R8D: raw SEC2 fuse.
# Return 1 for signature 0, 2 for signature 1, 0 without writes otherwise.
.text
.globl nvidia_prepare_sec2_image
nvidia_prepare_sec2_image:
.Lprepare_sec2_image:
    test %rcx, %rcx
    jz .Lsec2_image_reject
    test %rdx, %rdx
    jz .Lsec2_image_reject
    test $4095, %edx
    jnz .Lsec2_image_reject
    cmp $-1, %r8d
    je .Lsec2_image_reject
    cmp $0xbad00000, %r8d
    jb .Lsec2_fuse_data
    cmp $0xbae00000, %r8d
    jb .Lsec2_image_reject
.Lsec2_fuse_data:
    movzwl %r8w, %r8d
    cmp $1, %r8d
    ja .Lsec2_image_reject
    # Zero selects the last production signature. Version one selects the first.
    xor $1, %r8d
    imul $384, %r8d, %r10d
    lea 60(%rcx,%r10), %r10
    push %rsi
    push %rdi
    lea 888(%rcx), %rsi
    mov %rdx, %rdi
    mov $(60928/8), %ecx
    cld
    rep movsq
    xor %eax, %eax
    mov $((15*4096-60928)/8), %ecx
    rep stosq
    mov %r10, %rsi
    lea 35856(%rdx), %rdi
    mov $(384/8), %ecx
    rep movsq
    lea 1(%r8), %eax
    pop %rdi
    pop %rsi
    ret
.Lsec2_image_reject:
    xor %eax, %eax
    ret
