.text
#include "native_ui_layout.inc"
#ifdef BMO_NVIDIA_GSP_PREPARE
#include "../drivers/GPU/NVIDIA/gsp_layout.inc"
#endif
# Private 256 MiB QEMU profile. Validate the complete module before mapping.
.globl doom_engine_loader
doom_engine_loader:
    cld
#ifdef BMO_NVIDIA_GSP_PREPARE
    # The absent/corrupt path leaves the executable stage uninstalled.
    cmpl $5, GSP_STAGE_STATUS(%rbp)
    jne .Lnvidia_boot_continue
    lea GSP_POST_CODE(%rbp), %rax
    call *%rax
.Lnvidia_boot_continue:
#endif
#ifdef RMLUI_MEDIA
    mov 0xa8(%rbp), %rsi
    mov 0xb0(%rbp), %rdx
    movabs $0x2131565345524955, %rax
    cmp %rax, 0x700(%rbp)
    jne reject
    cmpq $NATIVE_UI_PHYSICAL, 0x708(%rbp)
    jne reject
    cmpq $NATIVE_UI_POOL_PAGES, 0x710(%rbp)
    jne reject
#else
    mov $0x2000000, %esi
    mov (%rsi), %rdx
    add $8, %rsi
#endif
    cmp $128, %rdx
    jb reject
#ifdef RMLUI_NATIVE
    cmp $0x200000, %rdx
#else
    cmp $0x100000, %rdx
#endif
    ja reject
    cmpl $0x46454253, (%rsi)     # SBEF
    jne reject
    cmpw $1, 6(%rsi)
    jne reject
    cmpw $1, 4(%rsi)
    je .Llegacy_isa_profile
    cmpw $2, 4(%rsi)
    jne reject
    mov 24(%rsi), %edi
    cmpl $0, 28(%rsi)
    jne reject_isa_reserved
    jmp .Lcheck_isa_profile
.Llegacy_isa_profile:
    cmpq $0, 24(%rsi)
    jne reject_isa_profile
    mov $1, %edi
.Lcheck_isa_profile:
    # The CASM continuation still needs R15 for CR4.
    push %rdx
    call .Lx2_isa_profile_check
    pop %rdx
    jc reject_isa_profile
    cmpl $0x3003e, 8(%rsi)
    jne reject
    cmp %edx, 12(%rsi)
    jne reject
    mov 16(%rsi), %r12
    mov %r12, %rax
    sub $0x40000000, %rax
    mov 44(%rsi), %ecx
    cmp %rcx, %rax
    jae reject
    lea 32(%rsi), %rdi
    mov $128, %ecx
    mov $0x40000000, %r8d
check_region:
    cmp %r8, (%rdi)
    jne reject
    cmp %ecx, 8(%rdi)
    jne reject
    cmpq $0, 24(%rdi)
    jne reject
    mov $0x200000, %r9d
    mov $5, %eax
    cmp $0x40000000, %r8d
    je check_flags
    mov $4, %eax
    cmp $0x40200000, %r8d
    je check_flags
    mov $6, %eax
    mov $NATIVE_UI_DATA_BYTES, %r9d
check_flags:
    cmp %eax, 20(%rdi)
    jne reject_permissions
    mov 16(%rdi), %eax
    test %eax, %eax
    jz reject
    cmp %r9d, %eax
    ja reject
    mov 12(%rdi), %r9d
    cmp %eax, %r9d
    ja reject
    add %r9d, %ecx
    cmp %edx, %ecx
    ja reject
    add $32, %rdi
    add $0x200000, %r8d
    cmp $0x40600000, %r8d
    jne check_region
    cmp %edx, %ecx
    jne reject

    # Check the map geometry and require one conventional descriptor
    # covering the entire private backing range.
    lea 0x1000(%rbp), %rdi
    mov 0x50(%rbp), %rcx
    mov 0x60(%rbp), %r8
    cmp $40, %r8
    jb reject
    cmp $256, %r8
    ja reject
    cmp $65536, %rcx
    ja reject
find_range:
    cmp %r8, %rcx
    jb reject
#ifdef RMLUI_MEDIA
    cmpl $2, (%rdi)             # UI-owned EfiLoaderData reservation
#else
    cmpl $7, (%rdi)
#endif
    jne next_descriptor
    mov 8(%rdi), %rax
    cmp $NATIVE_UI_PHYSICAL, %rax
    ja next_descriptor
    mov $NATIVE_UI_POOL_END, %r9d
    sub %rax, %r9
    add $4095, %r9
    shr $12, %r9
    cmp %r9, 24(%rdi)
    jae copy_image
next_descriptor:
    add %r8, %rdi
    sub %r8, %rcx
    jmp find_range

copy_image:
    mov $NATIVE_UI_PHYSICAL, %edi
    xor %eax, %eax
    mov $(NATIVE_UI_POOL_BYTES / 8), %ecx
    rep stosq
    lea 32(%rsi), %r8
    mov %rsi, %r9
    mov $0x4000000, %edx
copy_region:
    mov 8(%r8), %esi
    add %r9, %rsi
    mov %edx, %edi
    mov 12(%r8), %ecx
    rep movsb
    add $32, %r8
    add $0x200000, %edx
    cmp $0x4600000, %edx
    jne copy_region

    lea 0x3000(%r11), %rdi
    mov $0x4000085, %eax
    stosq
    mov $0x4200085, %eax
    bts $63, %rax
    stosq
    or $2, %al
    mov $((NATIVE_UI_DATA_BYTES + NATIVE_UI_STACK_BYTES) / 0x200000), %ecx
map_writable:
    add $0x200000, %rax
    stosq
    loop map_writable
    jmp exit
reject_permissions:
    sub %rsi, %rdi
    add $20, %edi
    mov %edi, 0x350(%r10)
    jmp reject
reject_isa_reserved:
    movl $28, 0x350(%r10)
    jmp reject
reject_isa_profile:
    movl $24, 0x350(%r10)
reject:
    xor %r12d, %r12d
    mov %rbp, %rdi
    hlt
exit:
    jmp .Lstaging_return
    # The packet builder appends the jump to the CASM GDT setup.

#include "../arch/x86_64/cpu/isa_profile_check.inc"

.Lstaging_return:
