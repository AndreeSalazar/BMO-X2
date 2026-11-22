.text
#ifdef RMLUI_GOP_REGIONS
#include "../drivers/display/GOP/gop_layout.inc"
#endif
#ifdef BMO_AMDVI_POST
#include "../drivers/bus/amdvi/post_layout.inc"
#endif
#ifdef BMO_NVIDIA_GSP_STATUS
#include "../drivers/GPU/NVIDIA/gsp_layout.inc"
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
#ifdef RMLUI_GOP_REGIONS
    cmp $10, %rsi
    je present_cursor_region
#endif
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
#ifdef BMO_AMDVI_POST
    cmp $AMDVI_POST_DIAGNOSTIC, %rdx
    je amdvi_diagnostic
#endif
#ifdef BMO_DMA_CENSUS
    cmp $DMA_CENSUS_SELECTOR, %rdx
    jne .Lordinary_diagnostics
    lea DMA_CENSUS_CODE(%rbp), %rax
    call *%rax
    jmp finish
.Lordinary_diagnostics:
#endif
#ifdef XHCI_COMMAND_PROBE
    cmp $5, %rdx
    je usb_report
#ifdef RMLUI_USB
    cmp $18, %rdx
    jne usb_not_status
    movzbl %gs:0x3c8, %eax
    jmp finish
usb_not_status:
#ifdef XHCI_NATIVE_DUAL
    cmp $19, %rdx
    je native_usb_stop
    cmp $20, %rdx
    je native_usb_kind
    cmp $21, %rdx
    je native_usb_status
    cmp $22, %rdx
    je native_usb_descriptor
#endif
#endif
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
#ifdef BMO_AMDVI_POST
amdvi_diagnostic:
    cmp $5, %r10
#ifdef BMO_NVIDIA_GSP_STATUS
    jbe .Lamdvi_snapshot
    cmp $6, %r10
    je .Lamdvi_gsp_status
#else
    jbe .Lamdvi_snapshot
#endif
    cmp $7, %r10
    jb denied
    cmp $7, %r10
    ja denied
    jmp .Lamdvi_snapshot
#ifdef BMO_NVIDIA_GSP_STATUS
.Lamdvi_gsp_status:
    mov GSP_STAGE_STATUS(%rbp), %rax
    jmp finish
#endif
.Lamdvi_snapshot:
    cmpq $0, AMDVI_POST_STATUS(%rbp)
    jne .Lamdvi_diagnostic_ready
    push %r10
    lea AMDVI_POST_CODE(%rbp), %rax
    call *%rax
    pop %r10
.Lamdvi_diagnostic_ready:
    mov AMDVI_POST_STATUS(%rbp), %rax
    test %r10, %r10
    jz finish
    cmp $4, %eax
    jne denied
    cmp $7, %r10
    je .Lamdvi_dte_status
    mov AMDVI_POST_STATUS(%rbp,%r10,8), %rax
    jmp finish
.Lamdvi_dte_status:
    mov AMDVI_DTE_POST_ZERO_QWORDS(%rbp), %rax
    shl $32, %rax
    or AMDVI_DTE_POST_STATUS(%rbp), %rax
    jmp finish
#endif
#ifdef DESKTOP_MEDIA
usb_controllers:
#ifdef XHCI_NATIVE_DUAL
    call native_usb_code
    jc denied
#else
    lea 0x12000(%rbp), %rax
#endif
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
#ifdef BMO_AMDVI_GUEST_DMA
    cmpq $0, AMDVI_LAB_REQUEST(%rbp)
    je .Lusb_no_dma_lab_request
    lea AMDVI_LAB_CODE(%rbp), %rax
    call *%rax
.Lusb_no_dma_lab_request:
#endif
#ifdef XHCI_NATIVE_DUAL
    call native_usb_code
    jc native_usb_invalid
    add $5, %rax
#else
    lea 0x12005(%rbp), %rax
#endif
    call *%rax
    pop %rbx
    jmp finish
#ifdef XHCI_NATIVE_DUAL
native_usb_invalid:
    pop %rbx
    jmp denied
native_usb_kind:
    mov %gs:0x7ec, %eax
    shl $32, %rax
    mov %gs:0x798, %edx
    or %rdx, %rax
    jmp finish
native_usb_descriptor:
    call native_usb_code
    jc denied
    add $15, %rax
    call *%rax
    jmp finish
native_usb_status:
    mov %gs:0x7ac, %eax
    movzbl %gs:0x770, %edx
    shl $8, %edx
    or %edx, %eax
    movzbl %gs:0x7a0, %edx
    shl $16, %edx
    or %edx, %eax
    movzbl %gs:0x3c8, %edx
    shl $24, %edx
    or %edx, %eax
    jmp finish
native_usb_stop:
    call native_usb_code
    jc denied
    add $10, %rax
    call *%rax
    movzbl %gs:0x37a, %eax
    jmp finish
native_usb_code:
    cmpq $2, 0x730(%rbp)
    jne native_usb_bad_code
    mov 0x728(%rbp), %rax
    test $4095, %eax
    jnz native_usb_bad_code
    cmp $0x100000, %rax
    jb native_usb_bad_code
    cmp $0x0fffe000, %rax
    ja native_usb_bad_code
    clc
    ret
native_usb_bad_code:
    stc
    ret
#endif
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

#ifdef RMLUI_GOP_REGIONS
present_cursor_region:
    cmp $1, %rdi
    jne denied
    lea GOP_REGION_ENTRY(%rbp), %rax
    call *%rax
    jmp finish
present_frame:
    lea GOP_FRAME_ENTRY(%rbp), %rax
    call *%rax
    jmp finish
#else
#include "../drivers/display/GOP/frame_copy.inc"
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
