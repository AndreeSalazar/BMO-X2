# Bounded sectors on the secondary IDE master of the TCG-only fixture.
.set SCRATCH_BLOCK, PRIVATE_STACK+4096
.Labi1_scratch_disk:
    cmp $4, %rsi
    je .Lscratch_transfer
    cmp $63, %r10
    ja .Labi1_bad_args
    cmp $3, %rsi
    je .Lscratch_put
    cmp $5, %rsi
    jne .Labi1_bad_op
    test %rcx, %rcx
    jnz .Labi1_bad_args
    mov SCRATCH_BLOCK(,%r10,8), %rdx
    jmp .Labi1_ok
.Lscratch_put:
    mov %rcx, SCRATCH_BLOCK(,%r10,8)
    jmp .Labi1_ok
.Lscratch_transfer:
    cmp $1, %rcx
    ja .Labi1_bad_args
#ifdef BMO_QEMU_GZIP_FAT
    # Both FAT heads, one root sector and the fixture's data pool.
    cmp $1, %r10
    je .Lscratch_lba_ok
    cmp $33, %r10
    je .Lscratch_lba_ok
    cmp $65, %r10
    je .Lscratch_lba_ok
    cmp $69, %r10
    jb .Lscratch_bpb
    cmp $70, %r10              # Cluster 5 belongs to the control file.
    je .Labi1_bad_args
    cmp $77, %r10
    jbe .Lscratch_lba_ok
.Lscratch_bpb:
    test %rcx, %rcx
    jnz .Labi1_bad_args
    test %r10, %r10
    jnz .Labi1_bad_args
.Lscratch_lba_ok:
#else
    test %r10, %r10
    jnz .Labi1_bad_args
#endif
    mov %ecx, %r8d
    mov $0x177, %edx
    xor %r11d, %r11d
    call .Lscratch_wait
    jc .Lscratch_failed
    mov $0x176, %edx
    mov $0xe0, %al
    out %al, (%dx)
    mov $0x376, %edx
    in (%dx), %al
    in (%dx), %al
    in (%dx), %al
    in (%dx), %al
    mov $0x172, %edx
    mov $1, %al
    out %al, (%dx)
    inc %edx
#ifdef BMO_QEMU_GZIP_FAT
    mov %r10b, %al
#endif
    out %al, (%dx)              # LBA low byte.
    xor %eax, %eax
    inc %edx
    out %al, (%dx)
    inc %edx
    out %al, (%dx)
    mov $0x177, %edx
    mov $0x20, %al
    test %r8d, %r8d
    jz .Lscratch_command
    mov $0x30, %al
.Lscratch_command:
    out %al, (%dx)
    mov $8, %r11d
    call .Lscratch_wait
    jc .Lscratch_failed
    mov $256, %ecx
    mov $0x170, %edx
    test %r8d, %r8d
    jnz .Lscratch_write
    mov $SCRATCH_BLOCK, %edi
    rep insw
    jmp .Lscratch_complete
.Lscratch_write:
    mov $SCRATCH_BLOCK, %esi
    rep outsw
    mov $0x177, %edx
    xor %r11d, %r11d
    call .Lscratch_wait
    jc .Lscratch_failed
    mov $0xe7, %al              # FLUSH CACHE before reporting success.
    out %al, (%dx)
.Lscratch_complete:
    mov $0x177, %edx
    xor %r11d, %r11d
    call .Lscratch_wait
    jc .Lscratch_failed
    xor %edx, %edx
    jmp .Labi1_ok
.Lscratch_failed:
    xor %edx, %edx
    mov $-4, %rax
    ret

# Wait for BSY to clear and DRQ to match R11. Polling has a fixed bound.
.Lscratch_wait:
    mov $100000, %ecx
.Lscratch_poll:
    in (%dx), %al
    cmp $0xff, %al
    je .Lscratch_error
    test $0x80, %al
    jnz .Lscratch_retry
    test $0x21, %al
    jnz .Lscratch_error
    and $8, %eax
    cmp %r11d, %eax
    je .Lscratch_ready
.Lscratch_retry:
    pause
    loop .Lscratch_poll
.Lscratch_error:
    stc
    ret
.Lscratch_ready:
    clc
    ret
