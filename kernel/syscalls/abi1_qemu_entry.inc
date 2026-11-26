# One-vCPU supervisor entry for the external SBEF QEMU fixture.
.set ABI_SCE, 0xc0000080
.set ABI_STAR, 0xc0000081
.set ABI_LSTAR, 0xc0000082
.set ABI_FMASK, 0xc0000084

.macro save_msr number, storage
    mov $\number, %ecx
    rdmsr
    mov %eax, \storage
    mov %edx, (\storage+4)
.endm
.macro restore_msr number, storage
    mov $\number, %ecx
    mov \storage, %eax
    mov (\storage+4), %edx
    wrmsr
    rdmsr
    cmp \storage, %eax
    jne .Lfail
    cmp (\storage+4), %edx
    jne .Lfail
.endm

.Linstall_abi1:
    call .Labi1_timer_start
    save_msr ABI_SCE, ABI_OLD_EFER
    save_msr ABI_STAR, ABI_OLD_STAR
    save_msr ABI_LSTAR, ABI_OLD_LSTAR
    save_msr ABI_FMASK, ABI_OLD_FMASK
    mov $ABI_STAR, %ecx
    xor %eax, %eax
    xor %edx, %edx
    mov %cs, %dx
    wrmsr
    mov $ABI_LSTAR, %ecx
    lea .Labi1_entry(%rip), %rax
    mov %rax, %rdx
    shr $32, %rdx
    wrmsr
    mov $ABI_FMASK, %ecx
    mov $0x44700, %eax           # TF, IF, DF, NT and AC.
    xor %edx, %edx
    wrmsr
    mov $ABI_SCE, %ecx
    mov ABI_OLD_EFER, %eax
    mov ABI_OLD_EFER+4, %edx
    or $1, %eax
    wrmsr
    movb $1, ABI_INSTALLED
    ret

.Lremove_abi1:
    cmpb $1, ABI_INSTALLED
    jne .Labi1_removed
    mov $0xff, %al
    out %al, $0x21
    restore_msr ABI_SCE, ABI_OLD_EFER
    restore_msr ABI_STAR, ABI_OLD_STAR
    restore_msr ABI_LSTAR, ABI_OLD_LSTAR
    restore_msr ABI_FMASK, ABI_OLD_FMASK
    movb $0, ABI_INSTALLED
    lea .Labi1_restored(%rip), %rsi
    call .Lprint
.Labi1_removed:
    ret

.Labi1_entry:
    # SYSCALL leaves the user RSP active. Store it without touching user memory.
    mov %rsp, ABI_RETURN_RSP
    mov $(PRIVATE_STACK+0x100000), %esp
    incq ABI_CALL_COUNT
    cmpq $USER_STACK, ABI_RETURN_RSP
    jb .Luser_bad_return
    cmpq $(USER_STACK+4096), ABI_RETURN_RSP
    ja .Luser_bad_return
    cmp $USER_BASE, %rcx
    jb .Luser_bad_return
    cmp $0x41000000, %rcx
    jae .Luser_bad_return
    pushq $0x83
    pushq ABI_RETURN_RSP
    pushq $0x202
    pushq $0x8b
    push %rcx
    call .Labi1_dispatch
    iretq

#include "abi1_dispatch.inc"
#include "abi1_qemu_timer.inc"

.Labi1_restored: .asciz "SBEF ABI GATE RESTORED\n"
