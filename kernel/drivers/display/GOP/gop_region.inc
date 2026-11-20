# Ring 0 platform probe: copy a clipped box from the 1280x800 XRGB surface.
# RDX: user surface, R10: packed 16-bit x/y or 0x80000000 for the top 80 rows.
# Other scales use op 9.
gop_cursor_region:
    cmp $0x40400000, %rdx
    jb gop_cursor_denied
    cmp $(0x40e00000-1280*800*4), %rdx
    ja gop_cursor_denied
    test $3, %dl
    jnz gop_cursor_denied
    mov %r10, %rax
    shr $32, %rax
    jnz gop_cursor_denied
    mov 0x10(%rbp), %rdi
    test %rdi, %rdi
    jz gop_cursor_denied
    mov 0x20(%rbp), %eax
    mov 0x24(%rbp), %ecx
    mov 0x28(%rbp), %r8d
    cmp $1280, %eax
    jb gop_cursor_denied
    cmp $800, %ecx
    jb gop_cursor_denied
    cmp $4096, %ecx
    ja gop_cursor_denied
    cmp %eax, %r8d
    jb gop_cursor_denied
    cmp $8192, %r8d
    ja gop_cursor_denied
    cmpl $1, 0x2c(%rbp)
    ja gop_cursor_denied
#ifdef BMO_FULL_HD
    cmp $1920, %eax
    jne .Lgop_region_legacy
    cmp $1080, %ecx
    je gop_fhd_region
.Lgop_region_legacy:
#endif
    cmp $2560, %eax
    jb gop_cursor_scale_one
    cmp $1600, %ecx
    jae gop_cursor_denied
gop_cursor_scale_one:
    sub $1280, %eax
    sub $800, %ecx
    shr %eax
    shr %ecx
    imul %r8d, %ecx
    add %eax, %ecx
    lea (%rdi,%rcx,4), %rdi
    lea -0x3c000000(%rdx), %rsi
    cmpl $0x80000000, %r10d
    je gop_status_strip
    movzwl %r10w, %eax
    shr $16, %r10d
    cmp $1280, %eax
    jae gop_cursor_denied
    cmp $800, %r10d
    jae gop_cursor_denied
    imul $1280, %r10d, %ecx
    add %eax, %ecx
    lea (%rsi,%rcx,4), %rsi
    mov %r10d, %ecx
    imul %r8d, %ecx
    add %eax, %ecx
    lea (%rdi,%rcx,4), %rdi
    mov $800, %edx
    sub %r10d, %edx
    mov $17, %ecx
    cmp %ecx, %edx
    cmova %ecx, %edx
    mov $1280, %r10d
    sub %eax, %r10d
    mov $12, %ecx
    cmp %ecx, %r10d
    cmova %ecx, %r10d
    jmp gop_region_copy
gop_status_strip:
    mov $80, %edx
    mov $1280, %r10d
gop_region_copy:
    mov %edx, %eax
    imul %r10d, %eax
    add %rax, %gs:0x7e0
    mov $1280, %r9d
    sub %r10d, %r9d
    sub %r10d, %r8d
    mov %cr3, %r11
    mov %gs:0x318, %rax
    mov %rax, %cr3
    cld
gop_cursor_row:
    mov %r10d, %ecx
    cmpl $1, 0x2c(%rbp)
    jne gop_cursor_convert
    rep movsl
    jmp gop_cursor_next
gop_cursor_convert:
    lodsl
    bswap %eax
    shr $8, %eax
    stosl
    loop gop_cursor_convert
gop_cursor_next:
    lea (%rsi,%r9,4), %rsi
    lea (%rdi,%r8,4), %rdi
    dec %edx
    jnz gop_cursor_row
    mov %r11, %cr3
    xor %eax, %eax
    ret
gop_cursor_denied:
    mov $257, %eax
    ret
