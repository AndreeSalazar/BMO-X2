.text
.globl session_gate
session_gate:
    swapgs
    mov %rsp, %gs:0x300
    mov %gs:0x308, %rsp
    pushq $0x1b
    pushq %gs:0x300
    pushq $2
    pushq $0x23
    pushq %rcx
    push %rbp
    mov %gs:0x320, %rbp
    test %rax, %rax
    jne denied
    cmp $2, %rsi
    je input
    cmp $1, %rsi
    jne denied
    cmp $1, %rdi
    jne denied

    # Fixed 640x400 viewport. Coordinates and size are packed in RDX.
    movzwl %dx, %edi
    mov %rdx, %rsi
    shr $16, %rsi
    movzwl %si, %esi
    mov %rdx, %rcx
    shr $32, %rcx
    movzwl %cx, %ecx
    shr $48, %rdx
    lea (%rdi,%rcx), %r8d
    cmp $640, %r8d
    ja denied
    lea (%rsi,%rdx), %r8d
    cmp $400, %r8d
    ja denied
    test %edx, %edx
    jz denied
    test %ecx, %ecx
    jz denied
    cmpq $0, 0x10(%rbp)
    je denied
    cmpl $640, 0x20(%rbp)
    jb denied
    cmpl $400, 0x24(%rbp)
    jb denied
    mov 0x28(%rbp), %r8d
    cmp 0x20(%rbp), %r8d
    jb denied
    cmp $8192, %r8d
    ja denied
    cmpl $4096, 0x24(%rbp)
    ja denied
    cmpl $1, 0x2c(%rbp)
    ja denied
    # A full viewport repaint also clears the surrounding boot image.
    cmp $640, %ecx
    jne scale
    cmp $400, %edx
    jne scale
    incl %gs:0x32c
    mov 0x20(%rbp), %ecx
    mov 0x24(%rbp), %edx
    jmp geometry_ready
scale:
    cmpl $1280, 0x20(%rbp)
    jb geometry_ready
    cmpl $800, 0x24(%rbp)
    jb geometry_ready
    add %edi, %edi
    add %esi, %esi
    add %ecx, %ecx
    add %edx, %edx
geometry_ready:
    imul %r8, %rsi
    add %rdi, %rsi
    shl $2, %r8
    mov 0x10(%rbp), %r9
    lea (%r9,%rsi,4), %r9
    mov %r10d, %eax
    and $0xffffff, %eax
    cmpl $0, 0x2c(%rbp)
    jne draw
    bswap %eax
    shr $8, %eax
draw:
    cld
    mov %cr3, %r11
    mov %gs:0x318, %rsi
    mov %rsi, %cr3
    mov %ecx, %esi
row:
    mov %r9, %rdi
    mov %esi, %ecx
    rep stosl
    add %r8, %r9
    dec %edx
    jnz row
    mov %r11, %cr3
    xor %eax, %eax
    jmp finish
input:
    cmp $2, %rdi
    jne denied
    cmpb $0, %gs:0x328
    je enable_mouse
    xor %eax, %eax
    in $0x64, %al
    test $1, %al
    jz empty
    mov %eax, %edx
    xor %eax, %eax
    in $0x60, %al
    test $0x20, %dl
    jz finish
    or $512, %eax
    jmp finish
enable_mouse:
    call writable
    jc denied
    mov $0xa8, %al
    out %al, $0x64
    call writable
    jc denied
    mov $0xd4, %al
    out %al, $0x64
    call writable
    jc denied
    mov $0xf4, %al
    out %al, $0x60
    movb $1, %gs:0x328
    jmp empty
writable:
    mov $65536, %ecx
poll_write:
    in $0x64, %al
    test $2, %al
    jz ready
    loop poll_write
    stc
    ret
ready:
    clc
    ret
empty:
    mov $256, %eax
    jmp finish
denied:
    mov $257, %eax
finish:
    pop %rbp
    swapgs
    iretq
