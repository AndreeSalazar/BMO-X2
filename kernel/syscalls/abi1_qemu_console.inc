# Win64 console v1. Carry stdout bytes in registers, without user pointers.
.Labi1_console:
    test %r8, %r8
    jnz .Labi1_bad_args
#ifdef BMO_QEMU_GZIP_DISK
    cmp $3, %rsi
    jae .Labi1_scratch_disk
#endif
    cmp $2, %rsi
    je .Labi1_console_exit
    cmp $1, %rsi
    jne .Labi1_bad_op
    lea -1(%r10), %rax
    cmp $7, %rax
    ja .Labi1_bad_args
    mov WIN64_OUTPUT_BYTES, %rax
    add %r10, %rax
    cmp $4096, %rax
    ja .Labi1_bad_args
    mov %rax, WIN64_OUTPUT_BYTES
    mov %r10, %r11
.Labi1_console_byte:
    mov %ecx, %eax
    out %al, $0xea
    shr $8, %rcx
    dec %r11d
    jnz .Labi1_console_byte
    mov %r10, %rdx
    jmp .Labi1_ok
.Labi1_console_exit:
    test %r10, %r10
    jnz .Labi1_bad_args
#ifdef BMO_QEMU_WIN64_PROCESS
    mov %ecx, %eax
    cmp %rax, %rcx
    jne .Labi1_bad_args
#else
    cmp $255, %rcx
    ja .Labi1_bad_args
#endif
#ifdef BMO_EXTERNAL_TLS
    test %rcx, %rcx
    jnz .Ltls_final_exit
    cmpb $0, TLS_STATE
    je .Ltls_next_thread
.Ltls_final_exit:
#endif
#ifdef BMO_EXTERNAL_DLL_LIFECYCLE
    # The fixture can reach exit only after the DLL clears its counter.
    cmpq $0, 0x40803000
    jne .Lfail
    lea .Labi1_dll_clear(%rip), %rsi
    call .Lprint
#endif
    mov %rcx, %rax
    lea .Labi1_console_receipt(%rip), %rsi
    jmp .Luser_terminal
.Labi1_console_receipt: .asciz "SBEF WIN64 EXIT "
#ifdef BMO_EXTERNAL_DLL_LIFECYCLE
.Labi1_dll_clear: .asciz "SBEF DLL COUNTER CLEARED\n"
#endif
#ifdef BMO_QEMU_GZIP_DISK
#include "abi1_qemu_scratch_disk.inc"
#endif
