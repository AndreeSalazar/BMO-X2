# Full CPU presentation for the bounded framebuffer profiles.
#ifdef GOP_COPY_STAGED
#define GOP_COPY_DENIED .Lgop_copy_denied
#define GOP_COPY_DONE .Lgop_copy_done
#else
#define GOP_COPY_DENIED denied
#define GOP_COPY_DONE finish
#endif
#ifdef RMLUI_NATIVE
#ifndef DESKTOP_DOOM
#error RMLUI_NATIVE requires the bounded integer-scale presentation path
#endif
#define FRAME_W 1280
#define FRAME_H 800
#define FRAME_MIN_W 640
#define FRAME_MIN_H 400
#else
#define FRAME_W 320
#define FRAME_H 200
#define FRAME_MIN_W 640
#define FRAME_MIN_H 400
#endif
present_frame:
    cmp $1, %rdi
    jne GOP_COPY_DENIED
    cmp $0x40400000, %rdx
    jb GOP_COPY_DENIED
    cmp $(0x40e00000-FRAME_W*FRAME_H*4), %rdx
    ja GOP_COPY_DENIED
    test $3, %dl
    jnz GOP_COPY_DENIED
    cmpq $0, 0x10(%rbp)
    je GOP_COPY_DENIED
    mov 0x20(%rbp), %edi
    mov 0x24(%rbp), %ecx
    mov 0x28(%rbp), %r8d
    cmp $FRAME_MIN_W, %edi
    jb GOP_COPY_DENIED
    cmp $FRAME_MIN_H, %ecx
    jb GOP_COPY_DENIED
    cmp $4096, %ecx
    ja GOP_COPY_DENIED
    cmp %edi, %r8d
    jb GOP_COPY_DENIED
    cmp $8192, %r8d
    ja GOP_COPY_DENIED
    cmpl $1, 0x2c(%rbp)
    ja GOP_COPY_DENIED
    sub $0x3c000000, %rdx
    mov %rdx, %rsi
#ifdef RMLUI_NATIVE
    cmp $1280, %edi
    jb native_half
    cmp $800, %ecx
    jb native_half
#endif
#ifdef DESKTOP_DOOM
    # Largest whole-pixel scale that fits both axes.
    mov %edi, %eax
    xor %edx, %edx
    mov $FRAME_W, %edi
    div %edi
    mov %eax, %r10d
    mov %ecx, %eax
    xor %edx, %edx
    mov $FRAME_H, %edi
    div %edi
    cmp %eax, %r10d
    cmova %eax, %r10d
    mov 0x20(%rbp), %edi
    imul $FRAME_W, %r10d, %eax
    sub %eax, %edi
    imul $FRAME_H, %r10d, %eax
    sub %eax, %ecx
#else
    sub $640, %edi
    sub $400, %ecx
#endif
    shr %edi
    shr %ecx
    imul %r8, %rcx
    add %rdi, %rcx
    mov 0x10(%rbp), %r9
    lea (%r9,%rcx,4), %r9
    shl $2, %r8
    mov %cr3, %r11
    mov %gs:0x318, %rax
    mov %rax, %cr3
    cld
#ifdef DESKTOP_DOOM
    push %r10
#endif
    mov $FRAME_H, %edx
engine_row:
    mov %r9, %rdi
    mov $FRAME_W, %ecx
#ifdef RMLUI_NATIVE
    cmpq $1, (%rsp)
    jne engine_pixel
    cmpl $1, 0x2c(%rbp)
    jne engine_pixel
    rep movsl
    jmp engine_row_done
#endif
engine_pixel:
    lodsl
    cmpl $1, 0x2c(%rbp)
    je engine_color
    bswap %eax
    shr $8, %eax
engine_color:
#ifdef DESKTOP_DOOM
    mov %ecx, %r10d
    # Scale is stored on the kernel stack before drawing.
    mov (%rsp), %ecx
    rep stosl
    mov %r10d, %ecx
#else
    stosl
    stosl
#endif
    loop engine_pixel
#ifdef RMLUI_NATIVE
engine_row_done:
#endif
#ifdef DESKTOP_DOOM
    mov %rsi, %r10
    mov (%rsp), %esi
    dec %esi
#ifdef RMLUI_NATIVE
    # At 1280x800 the native surface has scale 1: no repeated rows.
    jz engine_row_ready
#endif
    push %rsi
    mov %r9, %rax
engine_repeat_row:
    add %r8, %r9
    mov %rax, %rsi
    mov %r9, %rdi
    imul $FRAME_W, 8(%rsp), %ecx
    rep movsl
    decl (%rsp)
    jnz engine_repeat_row
    pop %rsi
#ifdef RMLUI_NATIVE
engine_row_ready:
#endif
    mov %r10, %rsi
#else
    mov %rsi, %r10
    mov %r9, %rsi
    add %r8, %r9
    mov %r9, %rdi
    mov $640, %ecx
    rep movsl
#endif
    mov %r10, %rsi
    add %r8, %r9
    dec %edx
    jnz engine_row
#ifdef DESKTOP_DOOM
    pop %r10
#endif
    mov %r11, %cr3
    incl %gs:0x354
    xor %eax, %eax
    jmp GOP_COPY_DONE
#ifdef RMLUI_NATIVE
native_half:
    # Preserve the fixed 1280x800 input contract on smaller direct GOP modes.
    # Sample alternate columns/rows into a centered 640x400 destination.
    sub $640, %edi
    sub $400, %ecx
    shr %edi
    shr %ecx
    imul %r8, %rcx
    add %rdi, %rcx
    mov 0x10(%rbp), %r9
    lea (%r9,%rcx,4), %r9
    shl $2, %r8
    mov %cr3, %r11
    mov %gs:0x318, %rax
    mov %rax, %cr3
    mov $400, %edx
native_half_row:
    mov %r9, %rdi
    mov $640, %ecx
native_half_pixel:
    lodsl
    add $4, %rsi
    cmpl $1, 0x2c(%rbp)
    je native_half_color
    bswap %eax
    shr $8, %eax
native_half_color:
    stosl
    loop native_half_pixel
    add $5120, %rsi
    add %r8, %r9
    dec %edx
    jnz native_half_row
    mov %r11, %cr3
    incl %gs:0x354
    xor %eax, %eax
    jmp GOP_COPY_DONE
#endif
#ifdef GOP_COPY_STAGED
.Lgop_copy_denied:
    mov $257, %eax
.Lgop_copy_done:
    ret
#endif
#undef GOP_COPY_DENIED
#undef GOP_COPY_DONE
