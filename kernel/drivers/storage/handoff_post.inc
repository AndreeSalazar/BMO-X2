# Observe controller state immediately after ExitBootServices, before
# xHCI claims the shared temporary MMIO alias. Never follow DMA pointers.
storage_snapshot:
    push %rbx
    push %r12
    push %r13
    push %r14
    push %r15
    mov %cr3, %rax
    lea 0x13000(%rbp), %rcx
    cmp %rcx, %rax
    jne .Lstorage_post_done
    cmpq $0, 0x15400(%rbp)
    jne .Lstorage_post_done
    mov $1, %eax
    cpuid
    test $0x10000, %edx
    jz .Lstorage_post_done
    mov $0x277, %ecx
    rdmsr
    test $0xff000000, %eax
    jnz .Lstorage_post_done      # PAT index 3 must be UC.
    mov $0x80000000, %eax
    cpuid
    cmp $0x80000008, %eax
    jb .Lstorage_post_done
    mov $0x80000008, %eax
    cpuid
    movzbl %al, %ecx
    cmp $32, %ecx
    jb .Lstorage_post_done
    cmp $52, %ecx
    ja .Lstorage_post_done
    mov $1, %r14d
    shl %cl, %r14
    mov STORAGE_HEADER(%rbp), %r15d
    cmp $STORAGE_LIMIT, %r15d
    ja .Lstorage_post_done
    lea STORAGE_ROWS(%rbp), %r12
.Lstorage_post_row:
    test %r15d, %r15d
    jz .Lstorage_post_done
    cmpw $1, STORAGE_STATUS(%r12)
    jne .Lstorage_post_next
    call .Lstorage_pci_live
    jc .Lstorage_post_next
    # Each read is inside the EFI-validated BAR and first 0x1100 bytes.
    mov STORAGE_BAR(%r12), %r8
    mov STORAGE_BAR_BYTES(%r12), %r9
    mov $0x1100, %eax
    cmp %rax, %r9
    cmova %rax, %r9
    lea 4095(%r8,%r9), %r9
    and $-4096, %r9
    cmp %r14, %r9
    ja .Lstorage_post_next
    mov %r8d, %r13d
    and $4095, %r13d
    add $0x10000000, %r13d
    and $-4096, %r8
    call .Lstorage_map_range
    jc .Lstorage_post_next
    mov $0x10000000, %ebx
    lea 0x1e000(%rbp), %rdi
    movq $0, (%rdi)
    movq $0, 8(%rdi)
    movq $0, 16(%rdi)
.Lstorage_install:
    mov %r8, %rax
    or $0x19, %rax
    bts $63, %rax
    mov %rax, (%rdi)
    add $8, %rdi
    add $4096, %r8
    cmp %r9, %r8
    jb .Lstorage_install
    lea 0x1e003(%rbp), %rax
    mov %rax, 0x15400(%rbp)
    invlpg (%rbx)
    invlpg 0x1000(%rbx)
    invlpg 0x2000(%rbx)
    cmpl $0x010601, STORAGE_CLASS(%r12)
    je .Lstorage_ahci
    mov 0x14(%r13), %eax         # NVMe CC
    mov 0x1c(%r13), %edx         # NVMe CSTS
    jmp .Lstorage_global
.Lstorage_ahci:
    mov 4(%r13), %eax            # AHCI GHC
    mov 0xc(%r13), %edx          # AHCI PI
.Lstorage_global:
    cmp $-1, %eax
    je .Lstorage_revoke
    cmp $-1, %edx
    je .Lstorage_revoke
    mov %eax, STORAGE_GLOBAL0(%r12)
    mov %edx, STORAGE_GLOBAL1(%r12)
    cmpl $0x010601, STORAGE_CLASS(%r12)
    jne .Lstorage_captured
    test %eax, %eax              # AHCI Enable (GHC bit 31)
    jns .Lstorage_captured
    mov STORAGE_BAR_BYTES(%r12), %r8
    xor %ecx, %ecx
    mov $0x100, %edi
.Lstorage_port:
    bt %ecx, %edx
    jnc .Lstorage_port_next
    lea 0x3c(%rdi), %eax
    cmp %rax, %r8
    jb .Lstorage_revoke
    mov 0x18(%r13,%rdi), %eax    # PxCMD ST/FRE/FR/CR
    cmp $-1, %eax
    je .Lstorage_revoke
    test $0xc011, %eax
    jz .Lstorage_pending
    bts %ecx, STORAGE_ENGINES(%r12)
.Lstorage_pending:
    mov 0x34(%r13,%rdi), %eax    # PxSACT
    or 0x38(%r13,%rdi), %eax     # PxCI
    jz .Lstorage_port_next
    bts %ecx, STORAGE_PENDING(%r12)
.Lstorage_port_next:
    add $0x80, %edi
    inc %ecx
    cmp $32, %ecx
    jb .Lstorage_port
.Lstorage_captured:
    movw $2, STORAGE_STATUS(%r12)
#ifdef BMO_STORAGE_QUIESCE
    call storage_quiesce
#endif
.Lstorage_revoke:
    movq $0, 0x15400(%rbp)
    movq $0, 0x1e000(%rbp)
    movq $0, 0x1e008(%rbp)
    movq $0, 0x1e010(%rbp)
    invlpg (%rbx)
    invlpg 0x1000(%rbx)
    invlpg 0x2000(%rbx)
.Lstorage_post_next:
    add $STORAGE_ROW_BYTES, %r12
    dec %r15d
    jmp .Lstorage_post_row
.Lstorage_post_done:
    pop %r15
    pop %r14
    pop %r13
    pop %r12
    pop %rbx
    ret

# Resolve the current BAR and decode before opening the temporary alias.
.Lstorage_pci_live:
    mov $0xcf8, %dx
    in %dx, %eax
    mov %eax, %r10d
    movzwl STORAGE_BDF(%r12), %ecx
    shl $8, %ecx
    or $0x80000000, %ecx
    mov %ecx, %eax
    call .Lcensus_read_pci
    cmp STORAGE_ID(%r12), %eax
    jne .Lstorage_pci_bad
    lea 4(%rcx), %eax
    call .Lcensus_read_pci
    mov %ax, STORAGE_COMMAND_POST(%r12)
    test $2, %al
    jz .Lstorage_pci_bad
    lea 8(%rcx), %eax
    call .Lcensus_read_pci
    shr $8, %eax
    cmp STORAGE_CLASS(%r12), %eax
    jne .Lstorage_pci_bad
    add $0x10, %ecx
    cmp $0x010601, %eax
    jne .Lstorage_bar_low
    add $0x14, %ecx              # AHCI BAR5
.Lstorage_bar_low:
    mov %ecx, %eax
    call .Lcensus_read_pci
    mov %eax, %r11d
    and $7, %eax
    jz .Lstorage_bar_check
    cmp $4, %eax
    jne .Lstorage_pci_bad
    cmpl $0x010802, STORAGE_CLASS(%r12)
    jne .Lstorage_pci_bad        # BAR5 cannot be a paired 64-bit BAR.
    lea 4(%rcx), %eax
    call .Lcensus_read_pci
    shl $32, %rax
    or %rax, %r11
.Lstorage_bar_check:
    and $-16, %r11
    cmp STORAGE_BAR(%r12), %r11
    jne .Lstorage_pci_bad
    mov %r10d, %eax
    out %eax, %dx
    clc
    ret
.Lstorage_pci_bad:
    mov %r10d, %eax
    out %eax, %dx
    stc
    ret

# Refuse any mapped page that collides with a non-MMIO EFI descriptor.
.Lstorage_map_range:
    mov 0x60(%rbp), %rsi
    cmp $40, %rsi
    jb .Lstorage_map_bad
    cmp $256, %rsi
    ja .Lstorage_map_bad
    mov 0x50(%rbp), %rcx
    test %rcx, %rcx
    jz .Lstorage_map_bad
    cmp $65536, %rcx
    ja .Lstorage_map_bad
    lea 0x1000(%rbp), %rdi
.Lstorage_map_next:
    cmp %rsi, %rcx
    jb .Lstorage_map_bad
    cmpl $11, (%rdi)
    je .Lstorage_map_advance
    mov 8(%rdi), %rax
    cmp %r9, %rax
    jae .Lstorage_map_advance
    mov 24(%rdi), %rdx
    mov %rdx, %r10
    shr $40, %r10
    jnz .Lstorage_map_bad
    shl $12, %rdx
    add %rax, %rdx
    jc .Lstorage_map_bad
    cmp %r8, %rdx
    ja .Lstorage_map_bad
.Lstorage_map_advance:
    add %rsi, %rdi
    sub %rsi, %rcx
    jnz .Lstorage_map_next
    clc
    ret
.Lstorage_map_bad:
    stc
    ret

#ifdef BMO_STORAGE_QUIESCE
#include "quiesce.inc"
#endif
