.text
.globl desktop_present
desktop_present:
    # Runs on the trusted stack after the ABI probe has scrubbed user pages.
    # R15 carries two XRGB8888 pixels from the Rust compositor.
    mov $1, %r12d
    cmpq $0, 0x10(%rbp)
    je done
    cmpl $640, 0x20(%rbp)
    jb done
    cmpl $400, 0x24(%rbp)
    jb done
    mov 0x28(%rbp), %r8d
    cmp 0x20(%rbp), %r8d
    jb done
    cmp $8192, %r8d
    ja done
    cmpl $1, 0x2c(%rbp)
    ja done
    mov %cr3, %r11
    mov %r13, %cr3
    shl $2, %r8
    mov 0x10(%rbp), %r9
    imul $64, %r8, %rax
    lea 64(%r9,%rax), %r9
    mov %r15d, %r10d
    mov %r15, %rsi
    shr $32, %rsi
    and $0xffffff, %r10d
    and $0xffffff, %esi
    cmpl $0, 0x2c(%rbp)
    je draw
    bswap %r10d
    bswap %esi
    shr $8, %r10d
    shr $8, %esi
draw:
    mov $32, %edx
row:
    mov %r9, %rdi
    mov %r10d, %eax
    mov $64, %ecx
    rep stosl
    mov %esi, %eax
    mov $64, %ecx
    rep stosl
    add %r8, %r9
    dec %edx
    jnz row
    mov %r11, %cr3
done:
    mov %rbp, %rdi
    # The fixture appends its jump back to the verified terminal here.
