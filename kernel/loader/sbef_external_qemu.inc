# QEMU-only mapping, entry and teardown of the FAT32 executable.
.macro supervisor_pt page, address
    lea (\page*4096+3)(%r12), %rax
    mov %rax, (0x2000+8*(\address>>21))(%r12)
.endm

.Lexternal_tables:
    # The inherited firmware selector cannot share our user/TSS entries.
    mov %cs, %ax
    cmp $0x70, %ax
    ja .Lfail
    mov 0xb0(%rbp), %rdx
    cmp $64, %rdx
    jb .Lfail
    cmp $16512, %rdx
    ja .Lfail
    mov %rdx, (10*4096+0xb78)(%r12)
    lea 4095(%rdx), %rcx
    shr $12, %rcx
    cmp 0xc8(%rbp), %rcx
    ja .Lfail
    cmpq $5, 0xc8(%rbp)
    ja .Lfail
    mov 0xa8(%rbp), %rax
    test $4095, %eax
    jnz .Lfail
    cmp $0x100000, %rax
    jb .Lfail
    cmp $0x0fffb000, %rax
    ja .Lfail
    mov %rcx, %rdx
    shl $12, %rdx
    add %rax, %rdx
    cmp %r12, %rdx
    jbe .Lsource_separate
    lea (POOL_PAGES*4096)(%r12), %rdx
    cmp %rdx, %rax
    jb .Lfail
.Lsource_separate:
    mov %rax, (10*4096+0xb80)(%r12)
    mov 0xc8(%rbp), %rdx
    mov %rdx, (10*4096+0xb88)(%r12)
    lea (SOURCE_PT*4096)(%r12), %rdi
    or $1, %rax
    bts $63, %rax
.Lsource_pages:
    stosq
    add $4096, %rax
    loop .Lsource_pages
    supervisor_pt SOURCE_PT, FAT_SOURCE
    supervisor_pt COPY_PT, USER_COPY
    supervisor_pt TABLE_PT, TABLE_MAP
    lea (IDT_PHYS*4096+3)(%r12), %rax
    bts $63, %rax
    mov %rax, 0x4008(%r12)
    lea (TABLE_PT*4096)(%r12), %rdi
    lea 0x2003(%r12), %rax
    bts $63, %rax
    stosq
    lea (USER_PT*4096+3)(%r12), %rax
    bts $63, %rax
    mov $8, %ecx
.Ltable_aliases:
    stosq
    add $4096, %rax
    loop .Ltable_aliases
    lea (USER_STACK_PT*4096+3)(%r12), %rax
    bts $63, %rax
    stosq
    lea (COPY_PT*4096)(%r12), %rdi
    lea (USER_FRAME*4096+3)(%r12), %rax
    bts $63, %rax
    mov $USER_MAX_PAGES, %ecx
.Lframe_aliases:
    stosq
    add $4096, %rax
    loop .Lframe_aliases
    orq $4, (%r12)
    lea (USER_PD*4096+7)(%r12), %rax
    mov %rax, 0x1008(%r12)
    lea (USER_PD*4096)(%r12), %rdi
    lea (USER_PT*4096+7)(%r12), %rax
    mov $8, %ecx
.Luser_directories:
    stosq
    add $4096, %rax
    loop .Luser_directories
    lea (USER_STACK_PT*4096+7)(%r12), %rax
    stosq
#ifdef BMO_EXTERNAL_PEER
    jmp .Labi1_peer_tables
#else
    ret
#endif

.Lexternal_gates:
    xor %edx, %edx
    mov %cs, %dx
    movabs $0x00cf92000000ffff, %rax
    mov %rax, (GDT+8)(%rdx)      # SYSCALL uses kernel SS = CS + 8.
    movabs $0x00cff2000000ffff, %rax
    mov %rax, GDT+0x80
    movabs $0x00affa000000ffff, %rax
    mov %rax, GDT+0x88
    movabs $0x100089000e000067, %rax
    mov %rax, GDT+0x90
    movq $(PRIVATE_STACK+0x100000), TSS+4
    movw $104, TSS+102
    mov $0x90, %eax
    ltr %ax
    mov $0x80, %edi
    lea .Luser_exit(%rip), %rax
    call .Lgate
    movb $0xee, (IDT+0x80*16+5)
    ret

.Lexternal_admit:
    lea .Lfat_bytes(%rip), %rsi
    call .Lprint
    mov FAT_LENGTH, %rax
    call .Lhex
    mov FAT_LENGTH, %rdx
    mov $288, %ecx
    cmp %rcx, %rdx
    cmovb %rdx, %rcx
    lea 8(%rcx), %rax
    mov %rax, DATA+0x958
    mov %rdx, DATA+24
    xor %eax, %eax
    mov $(DATA+32), %edi
    mov $7, %ecx
    rep stosq
    mov FAT_LENGTH, %rdx
    mov $288, %ecx
    cmp %rcx, %rdx
    cmovb %rdx, %rcx
    mov $FAT_SOURCE, %esi
.Lfat_prefix:
    lodsb
    movzbl %al, %eax
    stosq
    loop .Lfat_prefix
    mov $BMO_MODULE_ENTRY, %eax
    mov $5, %edi
    call .Lguarded
    cmpl $0, VECTOR
    jne .Lfail
    mov %rax, %r15
    lea .Lreceipt(%rip), %rsi
    call .Lprint
    mov %r15, %rax
    call .Lhex
    test %r15, %r15
    jnz .Lreject_unmapped
    cmpw $1, FAT_SOURCE+6
    jne .Labi_reject
#ifdef BMO_EXTERNAL_PEER
    cmpq $USER_BASE, FAT_SOURCE+32
    jne .Labi_reject
    cmpl $5, FAT_SOURCE+52
    jne .Labi_reject
    cmpl $0x400, FAT_SOURCE+44
    jbe .Labi_reject
#endif
    mov $1, %edi
    cmpw $1, FAT_SOURCE+4
    je .Lrequire_cpu
    mov FAT_SOURCE+24, %edi
.Lrequire_cpu:
    call .Lx2_isa_profile_check
    jc .Lcpu_reject

    # Check every region and the total page budget before publishing any leaf.
    movzwl FAT_SOURCE+10, %r15d
    mov $(FAT_SOURCE+32), %esi
    xor %ebx, %ebx
    mov %r15d, %edx
.Lbudget:
    mov 16(%rsi), %eax
    add $4095, %rax
    shr $12, %rax
    add %rax, %rbx
    cmp $USER_MAX_PAGES, %rbx
    ja .Lbudget_reject
    add $32, %rsi
    dec %edx
    jnz .Lbudget

    mov %r12, SAVED_POOL
    mov %r13, SAVED_CR3
    mov %r14, OLD_STACK
    mov $(FAT_SOURCE+32), %r10d
    xor %r11d, %r11d
.Lpublish:
    mov %r11d, %edi
    shl $12, %edi
    add $USER_COPY, %edi
    mov 8(%r10), %esi
    add $FAT_SOURCE, %esi
    mov 12(%r10), %ecx
    rep movsb
    mov (%r10), %edi
    sub $USER_BASE, %edi
    shr $12, %edi
    lea (TABLE_MAP+4096)(,%rdi,8), %rdi
    lea USER_FRAME(%r11), %eax
    shl $12, %eax
    add %r12, %rax
    or $5, %rax
    cmpl $5, 20(%r10)
    je .Lleaf_ready
    bts $63, %rax
    cmpl $6, 20(%r10)
    jne .Lleaf_ready
    or $2, %rax
.Lleaf_ready:
    mov 16(%r10), %ecx
    add $4095, %rcx
    shr $12, %rcx
    add %ecx, %r11d
.Lpublish_page:
    stosq
    add $4096, %rax
    loop .Lpublish_page
    add $32, %r10
    dec %r15d
    jnz .Lpublish
    # Publish the stack through its own PT before dropping the writable aliases.
    lea ((USER_FRAME+USER_MAX_PAGES)*4096+7)(%r12), %rax
    bts $63, %rax
    # TABLE_MAP entry 9 maps the stack PT only for this setup.
    mov %rax, (TABLE_MAP+9*4096+8)
#ifdef BMO_EXTERNAL_TLS
    lea (TLS_STACK_FRAME*4096+7)(%r12), %rax
    bts $63, %rax
    mov %rax, (TABLE_MAP+9*4096+16)
#endif
    movq $0, (TABLE_MAP+8*(USER_COPY>>21))
    movq $0, (TABLE_MAP+8*(TABLE_MAP>>21))
    mov %cr3, %rax
    mov %rax, %cr3
    lea .Luser_pages(%rip), %rsi
    call .Lprint
#ifdef BMO_EXTERNAL_TLS
    lea 2(%rbx), %rax
#else
    lea 1(%rbx), %rax
#endif
    call .Lhex
#ifdef BMO_EXTERNAL_REBASE
    call .Labi1_timer_start
#else
    call .Linstall_abi1
#endif
    pushq $0x83
    pushq $(USER_STACK+4096)
    pushq $0x202
    pushq $0x8b
    pushq FAT_SOURCE+16
.Labi1_enter_user:
    xor %eax, %eax
    xor %ebx, %ebx
    xor %ecx, %ecx
    xor %edx, %edx
    xor %esi, %esi
    xor %edi, %edi
    xor %ebp, %ebp
    xor %r8d, %r8d
    xor %r9d, %r9d
    xor %r10d, %r10d
    xor %r11d, %r11d
    xor %r12d, %r12d
    xor %r13d, %r13d
    xor %r14d, %r14d
    xor %r15d, %r15d
    iretq

.Luser_exit:
    testb $3, 8(%rsp)
    jz .Lfail
    lea .Lexit_receipt(%rip), %rsi
    jmp .Luser_terminal
.Luser_pf:
    mov (%rsp), %rax
    push %rax
    lea .Lfault_error(%rip), %rsi
    call .Lprint
    pop %rax
    call .Lhex
    mov %cr2, %rax
    lea .Lfault_receipt(%rip), %rsi
    jmp .Luser_terminal
.Luser_abort:
    lea .Labort_receipt(%rip), %rsi
    jmp .Luser_terminal
.Luser_bad_return:
    mov ABI_RETURN_RSP, %rax
    lea .Lbad_return_receipt(%rip), %rsi
.Luser_terminal:
    push %rax
    call .Lprint
    pop %rax
    call .Lhex
    lea .Lcall_count(%rip), %rsi
    call .Lprint
    mov ABI_CALL_COUNT, %rax
    call .Lhex
    lea .Lwait_wakes(%rip), %rsi
    call .Lprint
    mov ABI_WAIT_WAKES, %rax
    call .Lhex
#ifdef BMO_EXTERNAL_PEER
    lea .Lpeer_state(%rip), %rsi
    call .Lprint
    movzbl PEER_STATE, %eax
    call .Lhex
#endif
    mov SAVED_POOL, %r12
    mov SAVED_CR3, %r13
    mov OLD_STACK, %r14
    jmp .Lfinish
.Lbudget_reject:
    lea .Lbudget_receipt(%rip), %rsi
    jmp .Lpolicy_reject
.Lcpu_reject:
    lea .Lcpu_receipt(%rip), %rsi
    jmp .Lpolicy_reject
.Labi_reject:
    lea .Labi_receipt(%rip), %rsi
.Lpolicy_reject:
    call .Lprint
.Lreject_unmapped:
    mov $(TABLE_MAP+4096), %edi
    mov $(9*512), %ecx
    xor %eax, %eax
    repe scasq
    jne .Lfail
    lea .Lunmapped_receipt(%rip), %rsi
    call .Lprint
    jmp .Lfinish

.Lfat_bytes: .asciz "SBEF FAT32 BYTES "
.Luser_pages: .asciz "SBEF USER PAGES "
.Lexit_receipt: .asciz "SBEF CPL3 EXIT "
.Lfault_receipt: .asciz "SBEF CPL3 PF "
.Lfault_error: .asciz "SBEF PF ERROR "
.Labort_receipt: .asciz "SBEF CPL3 ABORT "
.Lbad_return_receipt: .asciz "SBEF ABI BAD RETURN "
.Lcall_count: .asciz "SBEF SYSCALLS "
.Lwait_wakes: .asciz "SBEF WAIT WAKES "
.Lbudget_receipt: .asciz "SBEF USER BUDGET\n"
.Lcpu_receipt: .asciz "SBEF CPU UNSUPPORTED\n"
.Labi_receipt: .asciz "SBEF ABI UNSUPPORTED\n"
.Lunmapped_receipt: .asciz "SBEF REJECTED BEFORE USER MAP\n"
.Lfat_scrubbed: .asciz "SBEF FAT32 SCRUBBED "

#include "../arch/x86_64/cpu/isa_profile_check.inc"
#ifdef BMO_EXTERNAL_PEER
.Lpeer_state: .asciz "SBEF PEER STATE "
#include "../syscalls/abi1_qemu_peer.inc"
#endif
#ifdef BMO_EXTERNAL_EXT
.org 4096
#endif
#ifdef BMO_GS_FAULT_PC
// Explicit, one-shot #UD delivery at the two locally built GS fixture PCs.
.Lgs_user_ud:
    cmpq $BMO_GS_FAULT_PC, 0(%rsp)
    je .Lgs_ud_registered
    cmpq $BMO_GS_PROLOGUE_FAULT_PC, 0(%rsp)
    jne .Luser_abort
.Lgs_ud_registered:
    cmpq $0x8b, 8(%rsp)
    jne .Luser_abort
    cmpq $0x83, 32(%rsp)
    jne .Luser_abort
    cmpq $(USER_STACK+768), 24(%rsp)
    jb .Luser_abort
    cmpq $(USER_STACK+4096-40), 24(%rsp)
    ja .Luser_abort
    testb $8, 24(%rsp)
    jz .Luser_abort
    testb $7, 24(%rsp)
    jnz .Luser_abort
    cmpb $0, GS_UD_DELIVERED
    jne .Lgs_ud_repeat
    movb $1, GS_UD_DELIVERED
    push %rsi
    lea .Lgs_ud_receipt(%rip), %rsi
    cmpq $BMO_GS_PROLOGUE_FAULT_PC, 8(%rsp)
    jne .Lgs_ud_print
    lea .Lgs_prologue_receipt(%rip), %rsi
.Lgs_ud_print:
    call .Lprint
    pop %rsi
    mov 0(%rsp), %rcx
    mov 24(%rsp), %rdx
    mov $6, %r8d
    mov $USER_STACK, %r9d
    cmpq $BMO_GS_PROLOGUE_FAULT_PC, 0(%rsp)
    je .Lgs_deliver_prologue
    movq $BMO_GS_LANDING_PC, 0(%rsp)
    iretq
.Lgs_deliver_prologue:
    movq $BMO_GS_PROLOGUE_LANDING_PC, 0(%rsp)
    iretq
.Lgs_ud_repeat:
    mov $0x47534455, %eax
    jmp .Luser_abort
.Lgs_ud_receipt: .asciz "SBEF WIN64 #UD DELIVERED\n"
.Lgs_prologue_receipt: .asciz "SBEF WIN64 #UD PROLOGUE DELIVERED\n"
#endif
#ifdef BMO_EXTERNAL_REBASE
#include "../syscalls/abi1_qemu_timer.inc"
#else
#include "../syscalls/abi1_qemu_entry.inc"
#endif
