# Fixed 3:2 presentation from the first 720 rows of the native 1280x800
# surface. Region and frame copies use the same edge rule at odd origins.
gop_fhd_frame:
    lea -0x3c000000(%rdx), %rsi
    mov 0x10(%rbp), %rdi
    xor %eax, %eax
    xor %ecx, %ecx
    mov $720, %edx
    mov $1280, %r10d
    call .Lfhd_copy
    incl %gs:0x354
    xor %eax, %eax
    ret

gop_fhd_region:
    lea -0x3c000000(%rdx), %rsi
    cmp $0x80000000, %r10d
    jne .Lfhd_cursor
    xor %eax, %eax
    xor %ecx, %ecx
    mov $80, %edx
    mov $1280, %r10d
    jmp .Lfhd_region_copy
.Lfhd_cursor:
    movzwl %r10w, %eax
    mov %r10d, %ecx
    shr $16, %ecx
    cmp $1280, %eax
    jae gop_cursor_denied
    cmp $720, %ecx
    jae gop_cursor_denied
    mov $1280, %r10d
    sub %eax, %r10d
    mov $12, %edx
    cmp %edx, %r10d
    cmova %edx, %r10d
    mov $720, %edx
    sub %ecx, %edx
    cmp $17, %edx
    jbe .Lfhd_region_copy
    mov $17, %edx
.Lfhd_region_copy:
    call .Lfhd_copy
    add %rax, %gs:0x7e0
    xor %eax, %eax
    ret

# EAX/ECX origin, R10D/EDX width/height, R8D destination pitch.
# RDI and RSI point to the unmoved framebuffer and physical source.
.Lfhd_copy:
    push %rbx
    push %r12
    push %r13
    push %r14
    push %r15
    mov %eax, %r12d
    mov %ecx, %r13d
    mov %edx, %r14d
    lea (,%r8,4), %r15
    imul $1280, %ecx, %edx
    add %eax, %edx
    lea (%rsi,%rdx,4), %rsi
    lea (%rax,%rax,2), %eax
    shr %eax
    lea (%rcx,%rcx,2), %ecx
    shr %ecx
    mov %ecx, %edx
    imul %r8d, %edx
    add %eax, %edx
    lea (%rdi,%rdx,4), %rdi
    # Count destination pixels in the clipped region.
    lea (%r12,%r10), %r8d
    lea (%r8,%r8,2), %r8d
    shr %r8d
    sub %eax, %r8d
    lea (%r13,%r14), %edx
    lea (%rdx,%rdx,2), %edx
    shr %edx
    sub %ecx, %edx
    imul %edx, %r8d
    mov %cr3, %r9
    mov %gs:0x318, %rax
    mov %rax, %cr3
    cld
.Lfhd_row_pair:
    mov %rsi, %r11
    mov %rdi, %rbx
    call .Lfhd_row
    lea (%rbx,%r15), %rdi
    test $1, %r13b
    jz .Lfhd_next_row
    mov %rdi, %rbx
    mov %r11, %rsi
    call .Lfhd_row
    lea (%rbx,%r15), %rdi
.Lfhd_next_row:
    lea 5120(%r11), %rsi
    inc %r13d
    dec %r14d
    jnz .Lfhd_row_pair
    mov %r9, %cr3
    mov %r8d, %eax
    pop %r15
    pop %r14
    pop %r13
    pop %r12
    pop %rbx
    ret

.Lfhd_row:
    mov %r10d, %ecx
    mov %r12d, %edx
.Lfhd_pixel:
    lodsl
    cmpl $1, 0x2c(%rbp)
    je .Lfhd_color
    bswap %eax
    shr $8, %eax
.Lfhd_color:
    stosl
    test $1, %dl
    jz .Lfhd_pixel_done
    stosl
.Lfhd_pixel_done:
    inc %edx
    dec %ecx
    jnz .Lfhd_pixel
    ret
