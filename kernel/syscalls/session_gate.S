.text
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
    cmp $1, %rax
    je wait_input
    test %rax, %rax
    jne denied
#ifdef DESKTOP_EXTERNAL
    cmp $8, %rsi
    je session_exit
#endif
#ifdef DOOM_ENGINE
#ifdef RMLUI_NATIVE
    # Private native UI profile: operation 9 is a fixed 1280x800 surface.
    # Do not reinterpret DOOM's existing 320x200 operation 6.
    cmp $9, %rsi
#else
    cmp $6, %rsi
#endif
    je present_frame
    cmp $7, %rsi
    je serial_byte
#endif
#ifdef DOOM_WAD
    cmp $4, %rsi
    je read_wad
    cmp $5, %rsi
    je wad_length
#endif
    cmp $3, %rsi
    je diagnostics
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
#if !defined(DOOM_ENGINE) || defined(DESKTOP_DOOM)
    cmpb $0, %gs:0x328
    je enable_mouse
#endif
    xor %eax, %eax
    in $0x64, %al
    cmp $0xff, %al
    je empty
    test $1, %al
    jz empty
    mov %eax, %edx
    xor %eax, %eax
    in $0x60, %al
    test $0x20, %dl
    jz finish
    or $512, %eax
    jmp finish
#if !defined(DOOM_ENGINE) || defined(DESKTOP_DOOM)
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
    cmp $0xff, %al
    je absent
    test $2, %al
    jz ready
    loop poll_write
absent:
    stc
    ret
ready:
    clc
    ret
#endif

# One-client QEMU profile: WAIT(input, 0, relative PIT ticks).
# Timer IRQs are enabled only around HLT. Input stays in the PS/2 FIFO.
wait_input:
    cmp $2, %rdi
    jne denied
#ifdef DOOM_ENGINE
    cmp $1, %rsi
    je valid_wait_op
#endif
    test %rsi, %rsi
    jne denied
#ifdef DOOM_ENGINE
valid_wait_op:
#endif
    cmp $100, %rdx
    ja denied
    cmpb $0, %gs:0x330
    jne timer_ready
    mov %rdx, %r9
    lea timer_irq(%rip), %rax
    mov %ax, %gs:0x400
    movl $0x8e000008, %gs:0x402
    shr $16, %rax
    mov %ax, %gs:0x406
    shr $16, %rax
    mov %eax, %gs:0x408
    movw $0x20f, %gs:0x90
    lidt %gs:0x90
    mov $0xff, %al
    out %al, $0xa1
    out %al, $0x21
    mov $0x11, %al
    out %al, $0x20
    out %al, $0xa0
    mov $0x20, %al
    out %al, $0x21
    mov $0x28, %al
    out %al, $0xa1
    mov $4, %al
    out %al, $0x21
    mov $2, %al
    out %al, $0xa1
    mov $1, %al
    out %al, $0x21
    out %al, $0xa1
    mov $0xff, %al
    out %al, $0xa1
    mov $0xfe, %al
    out %al, $0x21
    mov $0x34, %al
    out %al, $0x43
    mov $11932, %ax
    out %al, $0x40
    mov %ah, %al
    out %al, $0x40
    movb $1, %gs:0x330
    mov %r9, %rdx
timer_ready:
    mov %gs:0x338, %r8
    add %rdx, %r8
wait_check:
#ifdef XHCI_COMMAND_PROBE
    cmpb $1, %gs:0x3c8
    jne wait_ps2
    mov %gs:0x3d0, %rax
    mov 12(%rax), %al
    and $1, %al
    cmp %gs:0x3cb, %al
    je event_ready
wait_ps2:
#endif
#if !defined(DOOM_ENGINE) || defined(DESKTOP_DOOM)
#ifdef DESKTOP_DOOM
    test %rsi, %rsi
    jnz wait_clock
#endif
    in $0x64, %al
    cmp $0xff, %al
    je wait_clock
    test $1, %al
    jnz event_ready
#endif
wait_clock:
    cmp %r8, %gs:0x338
    jae wait_timeout
    sti
    hlt
    cli
    jmp wait_check
#if !defined(DOOM_ENGINE) || defined(DESKTOP_DOOM)
event_ready:
    incl %gs:0x340
    xor %eax, %eax
    jmp finish
#endif
wait_timeout:
    incl %gs:0x344
    jmp empty
timer_irq:
    push %rax
    incq %gs:0x338
    mov $0x20, %al
    out %al, $0x20
    pop %rax
    iretq
diagnostics:
    cmp $3, %rdi
    jne denied
#ifdef XHCI_COMMAND_PROBE
    cmp $5, %rdx
    je usb_report
#endif
#ifdef DESKTOP_MEDIA
    cmp $4, %rdx
    je usb_controllers
#ifndef XHCI_COMMAND_PROBE
    cmp $6, %rdx
    je usb_preflight
    cmp $7, %rdx
    je usb_port_census
#ifdef XHCI_ENUM_PROBE
    lea -13(%rdx), %rax
    cmp $3, %rax
    jbe usb_context_read
    cmp $8, %rdx
    je usb_event_words
    cmp $9, %rdx
    je usb_event_pointer
    cmp $10, %rdx
    je usb_descriptor_head
    cmp $11, %rdx
    je usb_port_speed
    cmp $12, %rdx
    je usb_expected_pointer
#endif
#endif
#endif
    cmp $2, %rdx
    ja denied
    test %rdx, %rdx
    jz diagnostics_ticks
    mov %gs:0x33c(,%rdx,4), %eax
    jmp diagnostics_result
diagnostics_ticks:
    mov %gs:0x338, %eax
diagnostics_result:
    mov %edx, %gs:0x348
    mov %eax, %gs:0x34c
    jmp finish
#ifdef DESKTOP_MEDIA
usb_controllers:
    lea 0x12000(%rbp), %rax
    call *%rax
    jmp finish
#ifndef XHCI_COMMAND_PROBE
usb_preflight:
    mov %gs:0x3e0, %eax
    jmp finish
usb_port_census:
    mov %gs:0x3e8, %eax
    jmp finish
#ifdef XHCI_ENUM_PROBE
usb_context_read:
    cmpb $1, %gs:0x3c4
    jne denied
    mov %gs:0x3c0, %ecx
    cmp $16, %rdx
    je usb_context_size
    mov 0xb8(%rbp), %rax
    cmp $15, %rdx
    je usb_input_dequeue
    lea 0x5800(%rax,%rcx), %rax
    cmp $14, %rdx
    je usb_context_dequeue
    mov (%rax), %rax
    jmp finish
usb_input_dequeue:
    lea 0x5000(%rax,%rcx,2), %rax
usb_context_dequeue:
    mov 8(%rax), %rax
    jmp finish
usb_context_size:
    mov %ecx, %eax
    jmp finish
usb_event_words:
    mov %gs:0x3d0, %rax
    jmp finish
usb_event_pointer:
    mov %gs:0x398, %rax
    jmp finish
usb_expected_pointer:
    mov %gs:0x3d8, %rax
    jmp finish
usb_descriptor_head:
    cmpb $1, %gs:0x3c4
    jne denied
    mov 0xb8(%rbp), %rax
    cmpb $1, %gs:0x384
    jne usb_head_initial
    add $0x220, %rax       # Verified device prefix retained before config reads.
usb_head_initial:
    mov 0x4c00(%rax), %rax
    jmp finish
usb_port_speed:
    movzwl %gs:0x385, %eax
    shl $16, %eax
    mov %gs:0x380, %ax
    jmp finish
#endif
#endif
#endif
#ifdef XHCI_COMMAND_PROBE
usb_report:
    push %rbx
    lea 0x12005(%rbp), %rax
    call *%rax
    pop %rbx
    jmp finish
#endif
#ifdef DOOM_ENGINE
serial_byte:
    cmp $5, %rdi
    jne denied
    cmp $255, %rdx
    ja denied
    mov %edx, %r8d
    mov $0x3fd, %edx
    mov $65536, %ecx
serial_ready:
    in %dx, %al
    test $32, %al
    jnz serial_out
    loop serial_ready
    jmp denied
serial_out:
    mov $0x3f8, %edx
    mov %r8d, %eax
    out %al, %dx
    xor %eax, %eax
    jmp finish

present_frame:
    cmp $1, %rdi
    jne denied
    cmp $0x40400000, %rdx
    jb denied
    cmp $(0x40e00000-FRAME_W*FRAME_H*4), %rdx
    ja denied
    test $3, %dl
    jnz denied
    cmpq $0, 0x10(%rbp)
    je denied
    mov 0x20(%rbp), %edi
    mov 0x24(%rbp), %ecx
    mov 0x28(%rbp), %r8d
    cmp $FRAME_MIN_W, %edi
    jb denied
    cmp $FRAME_MIN_H, %ecx
    jb denied
    cmp $4096, %ecx
    ja denied
    cmp %edi, %r8d
    jb denied
    cmp $8192, %r8d
    ja denied
    cmpl $1, 0x2c(%rbp)
    ja denied
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
    jmp finish
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
    jmp finish
#endif
#endif
#ifdef DOOM_WAD
read_wad:
    call wad_header
    sub $4, %eax
    cmp %rax, %rdx
    ja wad_denied
    mov 8(%rcx,%rdx), %eax
    jmp finish
wad_length:
    call wad_header
    jmp finish
wad_header:
    cmp $4, %rdi
    jne wad_header_denied
    mov $0x3000000, %ecx
    mov (%rcx), %eax
    cmp $12, %eax
    jb wad_header_denied
    cmp $0x1000000, %eax
    ja wad_header_denied
    ret
wad_header_denied:
    pop %rcx
wad_denied:
    mov $-1, %rax
    jmp finish
#endif
empty:
    mov $256, %eax
    jmp finish
denied:
    mov $257, %eax
finish:
    pop %rbp
    swapgs
    iretq

#ifdef DESKTOP_EXTERNAL
# The fixed external profile owns five user pages.
session_exit:
    test %rdi, %rdi
    jne denied
#ifdef XHCI_COMMAND_PROBE
    cmpb $1, %gs:0x3c8
    jne exit_no_usb
    lea 0x1200a(%rbp), %rax
    call *%rax
exit_no_usb:
#endif
    mov %cr3, %r8
    mov %gs:0x318, %rax
    mov %rax, %cr3
    lea 0x4000(%r8), %rdi
    xor %eax, %eax
    push $5
    pop %rcx
    cld
    rep stosq
    lea 0x5000(%r8), %rdi
    mov $4, %ch                  # RCX is zero after REP; 1024 qwords.
    rep stosq
    # Skip the reserved page between RX and the stack.
    add $4096, %rdi
    mov $6, %ch                  # 1536 qwords for stack, rodata and data.
    rep stosq
    # Revoke the single client's access to INVOKE and WAIT (EFER.SCE).
    mov $0xc0000080, %ecx
    rdmsr
    and $0xfe, %al
    wrmsr
    mov $5, %r12d
#ifdef DESKTOP_REUSE
    # 0 = first owner, 1 = free, 2 = second owner, 3 = free and stopped.
    incb %gs:0x3a8
    cmpb $1, %gs:0x3a8
    jne session_closed
restart_wait:
    in $0x64, %al
    cmp $0xff, %al
    je restart_sleep
    test $1, %al
    jz restart_sleep
    mov %eax, %edx
    in $0x60, %al
    test $0x20, %dl
    jnz restart_wait
    cmp $0x3e, %al                # PS/2 F4 make code.
    je restart_session
restart_sleep:
    cmpb $0, %gs:0x330
    je restart_wait
    sti
    hlt
    cli
    jmp restart_wait
restart_session:
    mov %gs:0x308, %rsp
    mov %r8, %r11
    lea 0x7000(%r11), %r10
    jmp *%gs:0x3a0
#endif
session_closed:
    hlt
    jmp session_closed
#endif
