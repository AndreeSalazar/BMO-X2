# QEMU-only post-EBS exercise of the independently audited Native module.
.text
.set STREAM, 0x02000000
.set MODULE, 0x00400000
.set DATA, 0x10000000
.set PRIVATE_STACK, 0x20000000
#ifndef BMO_EXTERNAL_SBEF
.set IDT, DATA+0xa00
.set IDT_LIMIT, 0xef
#endif
.set OLD_IDTR, DATA+0xb00
.set NEW_IDTR, DATA+0xb10
.set SAVED_RSP, DATA+0xb20
.set VECTOR, DATA+0xb28
.set PHASE, DATA+0xb2c
.set JUMP_RIP, DATA+0xb30
.set OLD_GDTR, DATA+0xb40
.set NEW_GDTR, DATA+0xb50
.set GDT, DATA+0xc00
.set TABLES, 8
.set STACK_PHYS, 11
#ifdef BMO_EXTERNAL_SBEF
#include "sbef_external_qemu_layout.inc"
#else
.set POOL_PAGES, STACK_PHYS+256
#endif

.globl sbef_ring0_probe
sbef_ring0_probe:
    cli
    cld
    mov %rdi, %rbp
    mov $0x40000000, %eax
    cpuid
    cmp $0x54474354, %ebx
    jne .Lhalt
    cmp $0x43544743, %ecx
    jne .Lhalt
    cmp $0x47435447, %edx
    jne .Lhalt
    mov %cs, %ax
    test $3, %al
    jnz .Lfail
    movabs $0x2134364c4154454d, %rax
    cmp %rax, (%rbp)
    jne .Lfail
    cmpl $1, 0x78(%rbp)
    jne .Lfail
    cmpq $POOL_PAGES, 0xc0(%rbp)
    jne .Lfail
    mov 0xb8(%rbp), %r12
    cmp $0x100000, %r12
    jb .Lfail
    cmp $(0x10000000-POOL_PAGES*4096), %r12
    ja .Lfail
    test $4095, %r12d
    jnz .Lfail
    mov %cr0, %rax
    bt $16, %rax
    jnc .Lfail
    mov $0xc0000080, %ecx
    rdmsr
    test $0x800, %eax
    jz .Lfail

    # All table entries outside these supervisor mappings stay absent.
    lea 0x1003(%r12), %rax
    mov %rax, (%r12)
    lea 0x2003(%r12), %rax
    mov %rax, 0x1000(%r12)
    lea 0x3003(%r12), %rax
    mov %rax, (0x2000+8*(MODULE>>21))(%r12)
    lea 0x4003(%r12), %rax
    mov %rax, (0x2000+8*(DATA>>21))(%r12)
    lea 0x5003(%r12), %rax
    mov %rax, (0x2000+8*(PRIVATE_STACK>>21))(%r12)
    mov 8(%rbp), %rdx
    test $4095, %edx
    jnz .Lfail
    cmp $0x10000000, %rdx
    jae .Lfail
    mov %rdx, %rcx
    shr $21, %rcx
    cmpq $0, 0x2000(%r12,%rcx,8)
    jne .Lfail
    lea 0x6003(%r12), %rax
    mov %rax, 0x2000(%r12,%rcx,8)
    mov %rdx, %rcx
    shr $12, %rcx
    and $511, %ecx
    or $1, %rdx
    mov %rdx, 0x6000(%r12,%rcx,8)
#ifdef BMO_EXTERNAL_PEER
    cmp $511, %ecx
    je .Lfail
    lea (PEER_EXT*4096+1)(%r12), %rax
    mov %rax, 0x6008(%r12,%rcx,8)
    lea (PEER_EXT*4096)(%r12), %rdi
    mov $(STREAM+0x3000), %esi
    mov $512, %ecx
    rep movsq
#endif
    lea (TABLES*4096+1)(%r12), %rax
    mov %rax, 0x3000(%r12)
    add $4096, %rax
    mov %rax, 0x3008(%r12)
    lea (10*4096+3)(%r12), %rax
    bts $63, %rax
    mov %rax, 0x4000(%r12)
    lea (STACK_PHYS*4096+3)(%r12), %rax
    bts $63, %rax
    lea 0x5000(%r12), %rdi
    mov $256, %ecx
.Lstack_pages:
    stosq
    add $4096, %rax
    loop .Lstack_pages
    # Case input is RO/NX. CASM code and data are copied into owned pages.
#ifndef BMO_EXTERNAL_SBEF
    lea 0x7003(%r12), %rax
    mov %rax, (0x2000+8*(STREAM>>21))(%r12)
    movabs $(0x8000000000000001+STREAM+0x3000), %rax
    lea (0x7000+3*8)(%r12), %rdi
    mov $((BMO_CASE_COUNT*304+4095)/4096), %ecx
.Lcase_pages:
    stosq
    add $4096, %rax
    loop .Lcase_pages
#endif
    mov $STREAM, %esi
    lea (TABLES*4096)(%r12), %rdi
    mov $3072, %ecx
    rep movsl
    movabs $0x32464542534f4d42, %rax
    cmp %rax, (10*4096+0x958)(%r12)
    jne .Lfail
#ifdef BMO_EXTERNAL_SBEF
    call .Lexternal_tables
#endif

    # Restore the original map, IDTR and stack after the isolated trial.
    mov %cr3, %r13
    mov %rsp, %r14
    sidt (10*4096+0xb00)(%r12)
    sgdt (10*4096+0xb40)(%r12)
    movzwl (10*4096+0xb40)(%r12), %ecx
    mov (10*4096+0xb42)(%r12), %rsi
    xor %eax, %eax
    mov %cs, %ax
    cmp $0xf8, %eax
    ja .Lfail
    lea 7(%rax), %edx
    cmp %ecx, %edx
    ja .Lfail
    mov (%rsi,%rax), %rdx
    mov %rdx, (10*4096+0xc00)(%r12,%rax)
    mov %r12, %cr3
    mov $(PRIVATE_STACK+0x100000), %esp
    movw $0xff, NEW_GDTR
    movq $GDT, NEW_GDTR+2
    lgdt NEW_GDTR
    movw $IDT_LIMIT, NEW_IDTR
    movq $IDT, NEW_IDTR+2
    mov $6, %edi
    lea .Lud(%rip), %rax
    call .Lgate
    mov $13, %edi
    lea .Lgp(%rip), %rax
    call .Lgate
    mov $14, %edi
    lea .Lpf(%rip), %rax
    call .Lgate
#ifdef BMO_EXTERNAL_SBEF
    call .Lexternal_gates
#endif
    lidt NEW_IDTR
    lea .Lstarted(%rip), %rsi
    call .Lprint

#ifdef BMO_EXTERNAL_SBEF
    jmp .Lexternal_admit
#else
    # Deliberate trap from the audited module and a supervisor guard page.
    mov $1, %edi
    mov $BMO_TRAP_ENTRY, %eax
    call .Lguarded
    cmp $-1, %rax
    jne .Lfail
    cmpl $6, VECTOR
    jne .Lfail
    lea .Lguard_read(%rip), %rax
    mov $2, %edi
    call .Lguarded
    cmp $-1, %rax
    jne .Lfail
    cmpl $14, VECTOR
    jne .Lfail
    mov %cr2, %rax
    cmp $(DATA+4096), %rax
    jne .Lfail
    lea .Lwrite_text(%rip), %rax
    mov $3, %edi
    call .Lguarded
    cmp $-1, %rax
    jne .Lfail
    cmpl $14, VECTOR
    jne .Lfail
    mov %cr2, %rax
    cmp $MODULE, %rax
    jne .Lfail
    movb $0xc3, DATA+0xd00
    mov $(DATA+0xd00), %eax
    mov $4, %edi
    call .Lguarded
    cmp $-1, %rax
    jne .Lfail
    cmpl $14, VECTOR
    jne .Lfail
    mov %cr2, %rax
    cmp $(DATA+0xd00), %rax
    jne .Lfail
    lea .Ltraps(%rip), %rsi
    call .Lprint

    mov $(STREAM+0x3000), %r15d
    mov $BMO_CASE_COUNT, %ebx
.Lcase:
    mov (%r15), %rax
    cmp $296, %rax
    ja .Lfail
    mov %rax, DATA+0x958
    lea 8(%r15), %rsi
    mov $(DATA+24), %edi
    mov $296, %ecx
.Lcopy_byte:
    lodsb
    movzbl %al, %eax
    stosq
    loop .Lcopy_byte
    mov $5, %edi
    mov $BMO_MODULE_ENTRY, %eax
    call .Lguarded
    cmpl $0, VECTOR
    jne .Lfail
    push %rax
    lea .Lreceipt(%rip), %rsi
    call .Lprint
    pop %rax
    call .Lhex
    add $304, %r15
    dec %ebx
    jnz .Lcase
#endif
.Lfinish:
#ifdef BMO_EXTERNAL_SBEF
    call .Lremove_abi1
    mov FAT_PHYSICAL, %r8
    mov FAT_PAGES, %r9
#endif
    lidt OLD_IDTR
    lgdt OLD_GDTR
    mov %r13, %cr3
    mov %r14, %rsp
    mov %r12, %rdi
    xor %eax, %eax
    mov $(POOL_PAGES*512), %ecx
    rep stosq
    mov %r12, %rdi
    mov $(POOL_PAGES*512), %ecx
    repe scasq
    jne .Lfail
    mov %cr3, %rax
    cmp %r13, %rax
    jne .Lfail
#ifdef BMO_EXTERNAL_SBEF
    mov %r8, %rdi
    mov %r9, %rcx
    shl $9, %rcx
    xor %eax, %eax
    rep stosq
    mov %r8, %rdi
    mov %r9, %rcx
    shl $9, %rcx
    repe scasq
    jne .Lfail
    lea .Lfat_scrubbed(%rip), %rsi
    call .Lprint
    mov %r9, %rax
    shl $12, %rax
    call .Lhex
#endif
    lea .Lpassed(%rip), %rsi
    call .Lprint
    mov $0x10, %eax
    jmp .Lexit

#ifndef BMO_EXTERNAL_SBEF
.Lguard_read:
    mov DATA+4096, %eax
    ret
.Lwrite_text:
    movb $0xcc, MODULE
    ret
#endif

# The handler only recovers faults inside these explicitly scoped calls.
.Lguarded:
    movl $0, VECTOR
    mov %edi, PHASE
    mov %rsp, SAVED_RSP
    lea .Lrecover(%rip), %rdx
    mov %rdx, JUMP_RIP
    sub $8, %rsp
    call *%rax
    add $8, %rsp
.Lrecover:
    movl $0, PHASE
    ret

.Lud:
#ifdef BMO_EXTERNAL_SBEF
    testb $3, 8(%rsp)
    jnz .Luser_abort
#endif
    mov $6, %eax
    jmp .Ltrap
.Lgp:
#ifdef BMO_EXTERNAL_SBEF
    testb $3, 16(%rsp)
    jnz .Luser_abort
#endif
    mov $13, %eax
    jmp .Ltrap
.Lpf:
#ifdef BMO_EXTERNAL_SBEF
    testb $3, 16(%rsp)
    jnz .Luser_pf
#endif
    mov $14, %eax
.Ltrap:
    cmpl $0, PHASE
    je .Lfail
    mov %eax, VECTOR
    mov SAVED_RSP, %rsp
    mov $-1, %rax
    jmp *JUMP_RIP

.Lgate:
    shl $4, %edi
    add $IDT, %edi
    mov %ax, (%rdi)
    mov %cs, %dx
    mov %dx, 2(%rdi)
    movw $0x8e00, 4(%rdi)
    shr $16, %rax
    mov %ax, 6(%rdi)
    shr $16, %rax
    mov %eax, 8(%rdi)
    ret

.Lprint:
    mov $0xe9, %dx
.Lchar:
    lodsb
    test %al, %al
    jz .Lreturn
    out %al, %dx
    jmp .Lchar
.Lreturn:
    ret
.Lhex:
    mov %rax, %r8
    mov $16, %ecx
    mov $0xe9, %dx
.Lnibble:
    rol $4, %r8
    mov %r8d, %eax
    and $15, %al
    add $48, %al
    cmp $57, %al
    jbe .Ldigit
    add $7, %al
.Ldigit:
    out %al, %dx
    loop .Lnibble
    mov $10, %al
    out %al, %dx
    ret
.Lfail:
    lea .Lfailed(%rip), %rsi
    call .Lprint
    mov $0x11, %eax
.Lexit:
    mov $0xf4, %dx
    out %eax, %dx
.Lhalt:
    hlt
    jmp .Lhalt
.Lstarted: .asciz "SBEF CPL0 POST-EBS\n"
#ifndef BMO_EXTERNAL_SBEF
.Ltraps: .asciz "SBEF UD2 GUARD RX-WRITE NX-EXEC RECOVERED\n"
#endif
.Lreceipt: .asciz "SBEF RECEIPT "
.Lpassed: .asciz "SBEF MAP RESTORED AND SCRUBBED\n"
.Lfailed: .asciz "SBEF FAIL\n"
#ifdef BMO_EXTERNAL_SBEF
#include "sbef_external_qemu.inc"
#endif
