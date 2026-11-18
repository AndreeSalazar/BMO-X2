# Check a declared x86-64 psABI level before loading user code.
# Input: EDI = profile id (1..4). Output: CF=0 supported, CF=1 unsupported.
.Lx2_isa_profile_check:
    # CPUID writes EBX; preserve the loader's callee-saved register.
    push %rbx
    cmp $1, %edi
    jb .Lx2_isa_profile_reject
    cmp $4, %edi
    ja .Lx2_isa_profile_reject

    # x86-64-v1: CPUID.1 EDX baseline plus enabled SSE state, and SYSCALL.
    xor %eax, %eax
    cpuid
    cmp $1, %eax
    jb .Lx2_isa_profile_reject
    mov $1, %eax
    cpuid
    mov $0x07808101, %ebx
    and %edx, %ebx
    cmp $0x07808101, %ebx
    jne .Lx2_isa_profile_reject
    mov %cr4, %rax
    test $0x200, %rax
    jz .Lx2_isa_profile_reject
    mov $0x80000000, %eax
    cpuid
    cmp $0x80000001, %eax
    jb .Lx2_isa_profile_reject
    mov $0x80000001, %eax
    cpuid
    test $0x800, %edx
    jz .Lx2_isa_profile_reject
    cmp $1, %edi
    je .Lx2_isa_profile_accept

    # x86-64-v2 additions.
    mov $1, %eax
    cpuid
    mov $0x00982201, %ebx
    and %ecx, %ebx
    cmp $0x00982201, %ebx
    jne .Lx2_isa_profile_reject
    mov $0x80000001, %eax
    cpuid
    test $0x1, %ecx
    jz .Lx2_isa_profile_reject
    cmp $2, %edi
    je .Lx2_isa_profile_accept

    # x86-64-v3 additions: AVX state must be enabled by the OS in XCR0.
    mov $1, %eax
    cpuid
    mov $0x38401000, %ebx
    and %ecx, %ebx
    cmp $0x38401000, %ebx
    jne .Lx2_isa_profile_reject
    xor %eax, %eax
    cpuid
    cmp $7, %eax
    jb .Lx2_isa_profile_reject
    mov $7, %eax
    xor %ecx, %ecx
    cpuid
    mov $0x128, %eax
    and %ebx, %eax
    cmp $0x128, %eax
    jne .Lx2_isa_profile_reject
    mov $0x80000001, %eax
    cpuid
    test $0x20, %ecx
    jz .Lx2_isa_profile_reject
    xor %ecx, %ecx
    xgetbv
    and $0x6, %eax
    cmp $0x6, %eax
    jne .Lx2_isa_profile_reject
    cmp $3, %edi
    je .Lx2_isa_profile_accept

    # x86-64-v4 additions: all five AVX-512 subsets and enabled ZMM state.
    mov $7, %eax
    xor %ecx, %ecx
    cpuid
    mov $0xD0030000, %eax
    and %ebx, %eax
    cmp $0xD0030000, %eax
    jne .Lx2_isa_profile_reject
    xor %ecx, %ecx
    xgetbv
    and $0xE6, %eax
    cmp $0xE6, %eax
    jne .Lx2_isa_profile_reject

.Lx2_isa_profile_accept:
    pop %rbx
    clc
    ret
.Lx2_isa_profile_reject:
    pop %rbx
    stc
    ret
