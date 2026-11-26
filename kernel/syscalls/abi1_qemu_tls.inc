# Two sequential CPL3 threads in one address space, with private TLS and stacks.
.set TLS_GS_BASE, 0xc0000101

.Ltls_install:
    save_msr TLS_GS_BASE, TLS_OLD_GS
    mov $0x40e00000, %eax
    jmp .Ltls_set_base

.Ltls_restore:
    restore_msr TLS_GS_BASE, TLS_OLD_GS
    lea .Ltls_restored(%rip), %rsi
    jmp .Lprint

.Ltls_next_thread:
    movb $1, TLS_STATE
    lea .Ltls_switch(%rip), %rsi
    call .Lprint
    mov $0x40e01000, %eax
    call .Ltls_set_base
    pushq $0x83
    pushq $(USER_STACK+8192)
    pushq $0x202
    pushq $0x8b
    pushq FAT_SOURCE+16
    jmp .Labi1_enter_user

.Ltls_set_base:
    mov $TLS_GS_BASE, %ecx
    xor %edx, %edx
    wrmsr
    ret

.Ltls_switch: .asciz "SBEF TLS THREAD SWITCH\n"
.Ltls_restored: .asciz "SBEF TLS GS BASE RESTORED\n"
