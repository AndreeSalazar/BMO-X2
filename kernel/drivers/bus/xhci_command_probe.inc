# QEMU qemu-xhci only. Interrupt delivery remains disabled.
#include "xhci_dma_layout.inc"
.equ keyboard_report_count, 20
.text
xhci_test_command:
    cmpb $1, %gs:0x378
    jne command_skip
    mov %gs:0x360, %ecx
    shl $8, %ecx
    or $0x80000000, %ecx
    mov $0xcf8, %edx
    in %dx, %eax
    push %rax
    mov %ecx, %eax
    out %eax, %dx
    add $4, %edx
    in %dx, %eax
    cmp $0x000d1b36, %eax
    jne command_restore
    mov 0xb8(%rbp), %r8
    cmpq $XHCI_PROBE_PAGES, 0xc0(%rbp)
    jne command_restore
    cmp $0x100000, %r8
    jb command_restore
    cmp $(0x10000000 - 4096 * XHCI_PROBE_PAGES), %r8
    ja command_restore
    test $0xfff, %r8d
    jnz command_restore
    call xhci_validate_dma
    jnz command_restore
    movb $1, %gs:0x3c4
    cmpl $0x1000, 0x18(%rdi)
    jne command_restore
    cmpl $0x2000, 0x14(%rdi)
    jne command_restore
    cmpl $XHCI_SCRATCHPAD_LIMIT, %gs:0x3bc
    ja command_restore
    push %rcx
    mov 0x1e000(%rbp), %rax
    or $2, %rax
    mov %rax, 0x1e000(%rbp)
    add $4096, %rax
    mov %rax, 0x1e008(%rbp)
    add $4096, %rax
    mov %rax, 0x1e010(%rbp)
    invlpg (%rdi)
    lea 0x1000(%rdi), %r9
    invlpg (%r9)
    lea 0x2000(%rdi), %r10
    invlpg (%r10)
    movzbl (%rdi), %eax
    lea (%rdi,%rax), %r11
    call xhci_reset
    jne command_unmap
    movl $1, 0x38(%r11)         # one device slot
    # Prepare the physical pointer array. DCBAA[0] is zero when HCSPARAMS2
    # requests no scratchpads.
    lea XHCI_SCRATCHPAD_TABLE(%r8), %rsi
    lea (4096 * XHCI_PROBE_QUEUE_PAGES)(%r8), %rax
    mov $XHCI_SCRATCHPAD_LIMIT, %ecx
scratchpad_next:
    mov %rax, (%rsi)
    add $4096, %rax
    add $8, %rsi
    loop scratchpad_next
    cmpl $0, %gs:0x3bc
    je scratchpads_ready
    lea XHCI_SCRATCHPAD_TABLE(%r8), %rax
    mov %rax, (%r8)
scratchpads_ready:

    # First TRB: No Op Command, cycle 1. Single 16-TRB event segment.
    lea 0x1000(%r8), %rax
    movl $0x5c01, 12(%rax)
    lea 0x2000(%r8), %rcx
    lea 0x3000(%r8), %rdx
    mov %rcx, (%rdx)
    movl $16, 8(%rdx)
    mov %r8, 0x30(%r11)
    or $1, %rax
    mov %rax, 0x18(%r11)
    movl $1, 0x28(%r9)
    mov %rcx, 0x38(%r9)
    mov %rdx, 0x30(%r9)

    # Set PCI Bus Master while preserving its prior command word.
    mov (%rsp), %eax
    or $4, %eax
    mov $0xcf8, %edx
    out %eax, %dx
    add $4, %edx
    in %dx, %ax
    mov %ax, %gs:0x37c
    push %rax
    or $4, %ax
    out %ax, %dx
    movl $1, (%r11)
    mov $1, %eax
    xor %esi, %esi
    call command_poll
    jne command_stop
    movl $0, (%r10)
    mov $100000, %ecx
command_event:
    testb $1, 0x200c(%r8)
    jnz command_received
    pause
    loop command_event
    jmp command_stop
command_received:
    mov 0x200c(%r8), %eax
    and $0xfc00, %eax
    cmp $0x8400, %eax
    jne command_stop
    cmpb $1, 0x200b(%r8)
    jne command_stop
    lea 0x1000(%r8), %rax
    cmp %rax, 0x2000(%r8)
    jne command_stop
    movb $1, %gs:0x379
    lea 0x2018(%r8), %rax
    mov %rax, 0x38(%r9)
    call enumerate_keyboard
    cmpb $1, %gs:0x396
    jne command_stop
    movb $1, %gs:0x3c8
    add $16, %rsp                # Saved PCI command and function.
    jmp command_restore
command_stop:
    movl $0, (%r11)
    mov $1, %eax
    mov $1, %esi
    call command_poll
    setz %gs:0x37a
    pop %rax
    je command_restore_pci
    and $0xfffb, %ax           # Halt unconfirmed: do not restore bus mastering.
command_restore_pci:
    mov $0xcfc, %edx
    out %ax, %dx
    in %dx, %ax
    mov %ax, %gs:0x37e
command_unmap:
    movq $0, 0x1e008(%rbp)
    movq $0, 0x1e010(%rbp)
    invlpg (%r9)
    invlpg (%r10)
    pop %rcx
command_restore:
    pop %rax
    mov $0xcf8, %edx
    out %eax, %dx
command_skip:
    ret

# Require exclusive coverage by a LoaderData descriptor and disjoint
# reservations for the context, packet and staged desktop image.
xhci_validate_dma:
    push %rcx
    push %rdi
    lea (4096 * XHCI_PROBE_PAGES)(%r8), %rax
    lea 0x20000(%rbp), %rsi
    cmp %rsi, %r8
    jae dma_check_packet
    cmp %rbp, %rax
    ja dma_invalid
dma_check_packet:
    mov 8(%rbp), %rsi
    cmp %rax, %rsi
    jae dma_check_desktop
    add $4096, %rsi
    cmp %rsi, %r8
    jb dma_invalid
dma_check_desktop:
    mov 0xa8(%rbp), %rsi
    cmp %rax, %rsi
    jae dma_check_map
    mov 0xc8(%rbp), %rdx
    cmp $5, %rdx
    ja dma_invalid
    shl $12, %rdx
    add %rdx, %rsi
    jc dma_invalid
    cmp %rsi, %r8
    jb dma_invalid
dma_check_map:
    mov 0x60(%rbp), %rsi
    mov 0x50(%rbp), %rcx
    cmp $40, %rsi
    jb dma_invalid
    cmp $256, %rsi
    ja dma_invalid
    cmp $65536, %rcx
    ja dma_invalid
    lea 0x1000(%rbp), %rdx
    xor %r10d, %r10d
dma_descriptor:
    test %rcx, %rcx
    jz dma_result
    sub %rsi, %rcx
    jb dma_invalid
    mov 8(%rdx), %r9
    cmp %rax, %r9
    jae dma_next
    mov 24(%rdx), %r11
    mov %r11, %rdi
    shr $52, %rdi
    jnz dma_invalid
    shl $12, %r11
    add %r9, %r11
    jc dma_invalid
    cmp %r8, %r11
    jbe dma_next
    cmpl $2, (%rdx)
    jne dma_invalid
    cmp %r8, %r9
    ja dma_invalid
    cmp %rax, %r11
    jb dma_invalid
    inc %r10d
dma_next:
    add %rsi, %rdx
    jmp dma_descriptor
dma_result:
    cmp $1, %r10d
    pop %rdi
    pop %rcx
    ret
dma_invalid:
    or $1, %eax
    pop %rdi
    pop %rcx
    ret

enumerate_keyboard:
    movzbl 7(%rdi), %ecx        # MaxPorts
    cmp $32, %ecx
    ja enum_done
    lea 0x400(%r11), %rsi
    mov $1, %eax
port_next:
    testl $1, (%rsi)
    jnz port_connected
    add $16, %rsi
    inc %eax
    loop port_next
    ret
port_connected:
    mov %al, %gs:0x380
    movl $0x210, (%rsi)        # preserve PP and request port reset
    mov $100000, %ecx
port_wait:
    mov (%rsi), %edx
    and $0x13, %edx
    cmp $3, %edx
    je port_ready
    pause
    loop port_wait
    ret
port_ready:
    mov (%rsi), %edx
    shr $10, %edx
    and $15, %edx
    cmp $3, %edx              # full, low or high speed only
    ja enum_done
    test %edx, %edx
    jz enum_done
    mov %dl, %gs:0x381
    movl $0x2401, 0x101c(%r8)  # Enable Slot
    movl $0, (%r10)
    lea 0x2010(%r8), %rsi
    lea 0x1010(%r8), %rdx
    call enum_event
    jne enum_done
    cmpb $1, 15(%rsi)
    jne enum_done
    movb $1, %gs:0x382
    lea 16(%rsi), %rax
    mov %rax, %gs:0x388

    # The output context has room for 32 entries of up to 64 bytes.
    lea XHCI_OUTPUT_CONTEXT(%r8), %rax
    mov %rax, 8(%r8)
    mov %gs:0x3c0, %ecx
    lea XHCI_INPUT_CONTEXT(%r8,%rcx), %rbx
    movl $3, XHCI_INPUT_CONTEXT+4(%r8)
    movzbl %gs:0x381, %eax
    shl $20, %eax
    or $0x08000000, %eax
    mov %eax, (%rbx)
    movzbl %gs:0x380, %eax
    shl $16, %eax
    mov %eax, 4(%rbx)
    add %rcx, %rbx
    mov $0x00080026, %eax      # control EP, CErr 3, MPS 8
    cmpb $3, %gs:0x381
    jne ep0_packet
    mov $0x00400026, %eax
ep0_packet:
    mov %eax, 4(%rbx)
    lea 0x4801(%r8), %rax
    mov %rax, 8(%rbx)
    movl $8, 16(%rbx)
    lea XHCI_INPUT_CONTEXT(%r8), %rax
    mov %rax, 0x1020(%r8)
    movl $0x01002c01, 0x102c(%r8) # Address Device, slot 1
    movl $0, (%r10)
    mov %gs:0x388, %rsi
    lea 0x1020(%r8), %rdx
    call enum_event
    jne enum_done
    cmpb $1, 15(%rsi)
    jne enum_done
    movb $1, %gs:0x383
    call read_device_descriptor
    cmpb $1, %gs:0x384
    jne enum_done
    call read_keyboard_configuration
enum_done:
    ret

read_device_descriptor:
    lea 0x4800(%r8), %rbx
    lea 0x4c00(%r8), %rdx
    mov $0x01000680, %eax
    mov $18, %ecx
    call control_read
    jne descriptor_done
    cmpw $0x0112, 0x4c00(%r8)
    jne descriptor_done
    movb $1, %gs:0x384
descriptor_done:
    ret

# RBX first TRB, EAX request dword, RDX destination, ECX exact length.
control_read:
    mov %eax, (%rbx)
    mov %ecx, %eax
    shl $16, %eax
    mov %eax, 4(%rbx)
    movl $8, 8(%rbx)
    movl $0x30841, 12(%rbx)
    mov %rdx, 16(%rbx)
    mov %ecx, 24(%rbx)
    movl $0x10c01, 28(%rbx)
    movl $0x1021, 44(%rbx)
    lea 32(%rbx), %rdx
control_submit:
    lea 16(%rsi), %rsi
    lea 0x2100(%r8), %rax
    cmp %rax, %rsi
    jae control_failed
    movl $1, 4(%r10)
    mov $100000, %ecx
descriptor_wait:
    testb $1, 12(%rsi)
    jnz descriptor_event
    pause
    loop descriptor_wait
    jmp control_failed
descriptor_event:
    mov 12(%rsi), %eax
    and $0xfffffc00, %eax
    cmp $0x01018000, %eax    # transfer event, slot 1, endpoint 1
    jne control_failed
    cmpl $0x01000000, 8(%rsi)
    jne control_failed
    cmp %rdx, (%rsi)
    jne control_failed
    lea 24(%rsi), %rax
    mov %rax, 0x38(%r9)
    ret
control_failed:
    or $1, %eax
    ret

read_keyboard_configuration:
    lea 0x4830(%r8), %rbx
    lea 0x4c20(%r8), %rdx
    mov $0x02000680, %eax
    mov $9, %ecx
    call control_read
    jne keyboard_done
    cmpw $0x0209, 0x4c20(%r8)
    jne keyboard_done
    movzwl 0x4c22(%r8), %ecx
    cmp $9, %ecx
    jb keyboard_done
    cmp $512, %ecx
    ja keyboard_done
    mov %ecx, %gs:0x38c
    lea 0x4860(%r8), %rbx
    lea 0x4c40(%r8), %rdx
    mov $0x02000680, %eax
    call control_read
    jne keyboard_done
    cmpw $0x0209, 0x4c40(%r8)
    jne keyboard_done
    mov %gs:0x38c, %edx
    cmp %dx, 0x4c42(%r8)
    jne keyboard_done
    movzbl 0x4c45(%r8), %eax
    test %eax, %eax
    jz keyboard_done
    mov %al, %gs:0x390
    lea 0x4c49(%r8), %rbx
    sub $9, %edx
    xor %ecx, %ecx
configuration_next:
    cmp $2, %edx
    jb keyboard_done
    movzbl (%rbx), %eax
    cmp $2, %eax
    jb keyboard_done
    cmp %edx, %eax
    ja keyboard_done
    cmpb $4, 1(%rbx)
    jne configuration_endpoint
    xor %ecx, %ecx
    cmp $9, %eax
    jb keyboard_done
    cmpb $0, 3(%rbx)
    jne configuration_advance
    cmpb $3, 5(%rbx)
    jne configuration_advance
    cmpw $0x0101, 6(%rbx)
    jne configuration_advance
    mov 2(%rbx), %cl
    or $0x100, %ecx
    jmp configuration_advance
configuration_endpoint:
    test %ecx, %ecx
    jz configuration_advance
    cmpb $5, 1(%rbx)
    jne configuration_advance
    cmp $7, %eax
    jb keyboard_done
    movzbl 2(%rbx), %edi
    and $0xf0, %edi
    cmp $0x80, %edi
    jne configuration_advance
    testb $0x0f, 2(%rbx)
    jz configuration_advance
    mov 3(%rbx), %dil
    and $3, %dil
    cmp $3, %dil
    jne configuration_advance
    mov %cl, %gs:0x391
    mov 2(%rbx), %al
    mov %al, %gs:0x392
    mov 6(%rbx), %al
    mov %al, %gs:0x393
    mov 4(%rbx), %ax
    mov %ax, %gs:0x394
    movb $1, %gs:0x385
    lea 0x4890(%r8), %rbx
    movzbl %gs:0x390, %eax
    shl $16, %eax
    or $0x0900, %eax             # SET_CONFIGURATION
    xor %ecx, %ecx
    call control_no_data
    jne keyboard_done
    movb $1, %gs:0x386
    lea 0x48b0(%r8), %rbx
    mov $0x0b21, %eax           # SET_PROTOCOL, value zero (boot)
    movzbl %gs:0x391, %ecx
    call control_no_data
    jne keyboard_done
    movb $1, %gs:0x387
    call keyboard_first_report
    jmp keyboard_done
configuration_advance:
    sub %eax, %edx
    add %rax, %rbx
    jmp configuration_next
keyboard_done:
    ret

control_no_data:
    mov %eax, (%rbx)
    mov %ecx, 4(%rbx)
    movl $8, 8(%rbx)
    movl $0x841, 12(%rbx)
    movl $0x11021, 28(%rbx)
    lea 16(%rbx), %rdx
    jmp control_submit

keyboard_first_report:
    # Emulated boot keyboard, endpoint 1 IN.
    cmpb $0x81, %gs:0x392
    jne keyboard_report_done
    cmpw $8, %gs:0x394
    jne keyboard_report_done
    movzbl %gs:0x393, %eax
    test %eax, %eax
    jz keyboard_report_done
    cmpb $3, %gs:0x381
    jne keyboard_frame_interval
    dec %eax
    cmp $15, %eax
    ja keyboard_report_done
    jmp keyboard_interval_ready
keyboard_frame_interval:
    # Full/low-speed bInterval is in frames. Encode in microframes,
    # rounding down to the nearest power of two.
    bsr %eax, %eax
    add $3, %eax
keyboard_interval_ready:
    shl $16, %eax
    mov %gs:0x3c0, %ecx
    lea XHCI_INPUT_CONTEXT(%r8,%rcx), %rbx
    andl $0x07ffffff, (%rbx)
    orl $0x18000000, (%rbx)
    lea XHCI_INPUT_CONTEXT(%r8,%rcx,4), %rbx
    mov %eax, (%rbx)
    movl $0, XHCI_INPUT_CONTEXT(%r8)
    movl $9, XHCI_INPUT_CONTEXT+4(%r8)
    movl $0x0008003e, 4(%rbx)
    lea 0x4901(%r8), %rax
    mov %rax, 8(%rbx)
    movl $0x00080008, 16(%rbx)
    lea XHCI_INPUT_CONTEXT(%r8), %rax
    mov %rax, 0x1030(%r8)
    movl $0x01003001, 0x103c(%r8)
    movl $0, (%r10)
    add $16, %rsi
    lea 0x1030(%r8), %rdx
    call enum_event
    jne keyboard_report_done
    cmpb $1, 15(%rsi)
    jne keyboard_report_done
    add $16, %rsi
    lea 0x2100-16(%r8), %rax
    cmp %rax, %rsi
    ja keyboard_report_done
    mov %rsi, %gs:0x3d0
    movw $0x0101, %gs:0x3ca   # Producer and consumer cycles.
    lea 0x4900(%r8), %rax
    mov %rax, 0x4940(%r8)
    xor %ecx, %ecx
keyboard_report_submit:
    mov %rcx, %rbx
    and $3, %ebx
    lea 0x4e80(%r8,%rbx,8), %rdx
    shl $4, %rbx
    lea 0x4900(%r8,%rbx), %rbx
    mov %rdx, (%rbx)
    movl $8, 8(%rbx)
    movzbl %gs:0x3ca, %eax
    cmpb $3, %cl
    jne keyboard_publish
    lea 0x1802(%rax), %edx
    mov %edx, 0x494c(%r8)      # Link TRB, toggle cycle.
    xorb $1, %gs:0x3ca
keyboard_publish:
    or $0x420, %eax
    mov %eax, 12(%rbx)
    movl $3, 4(%r10)
    incb %gs:0x396
    ret

xhci_live_report:
    mov $256, %eax
    cmpb $1, %gs:0x3c8
    jne keyboard_report_done
    mov %gs:0x3d0, %rsi
    mov 12(%rsi), %dl
    and $1, %dl
    cmp %gs:0x3cb, %dl
    jne keyboard_report_done
    mov 0xb8(%rbp), %r8
    movzbl %gs:0x397, %ecx
    mov %rcx, %rbx
    and $3, %ebx
    shl $4, %rbx
    lea 0x4900(%r8,%rbx), %rbx
keyboard_report_event:
    mov 12(%rsi), %eax
    and $0xfffffc00, %eax
    cmp $0x01038000, %eax
    jne keyboard_live_error
    cmpl $0x01000000, 8(%rsi)
    jne keyboard_live_error
    cmp %rbx, (%rsi)
    jne keyboard_live_error
    add $16, %rsi
    lea 0x2100(%r8), %rax
    cmp %rax, %rsi
    jne keyboard_event_next
    lea 0x2000(%r8), %rsi
    xorb $1, %gs:0x3cb
keyboard_event_next:
    lea 8(%rsi), %rax
    mov %rax, 0x10001038
    mov %rsi, %gs:0x3d0
    incb %gs:0x397
    and $3, %ecx
    pushq 0x4e80(%r8,%rcx,8)
    cmpb $keyboard_report_count, %gs:0x397
    je keyboard_live_last
    lea 0x10002000, %r10
    inc %ecx
    and $3, %ecx
    call keyboard_report_submit
    jmp keyboard_live_deliver
keyboard_live_last:
    call xhci_live_stop
keyboard_live_deliver:
    pop %rax
    incb %gs:0x398
    ret
keyboard_live_error:
    call xhci_live_stop
    mov $256, %eax
keyboard_report_done:
    ret

xhci_live_stop:
    movb $0, %gs:0x3c8
    movzbl 0x10000000, %r11d
    add $0x10000000, %r11
    movl $0, (%r11)
    mov $1, %eax
    mov $1, %esi
    call command_poll
    setz %gs:0x37a
    mov $0xcf8, %edx
    in %dx, %eax
    push %rax
    mov %gs:0x360, %eax
    shl $8, %eax
    or $0x80000004, %eax
    out %eax, %dx
    add $4, %edx
    mov %gs:0x37c, %ax
    cmpb $1, %gs:0x37a
    je keyboard_live_restore
    and $0xfffb, %ax
keyboard_live_restore:
    out %ax, %dx
    in %dx, %ax
    mov %ax, %gs:0x37e
    pop %rax
    sub $4, %edx
    out %eax, %dx
    xor %eax, %eax
    mov %rax, 0x15400(%rbp)
    mov %rax, 0x1e000(%rbp)
    mov %rax, 0x1e008(%rbp)
    mov %rax, 0x1e010(%rbp)
    invlpg 0x10000000
    invlpg 0x10001000
    invlpg 0x10002000
    ret

# Find a command completion, allowing intervening port-change events.
enum_event:
    lea 0x2100(%r8), %rax
    mov $100000, %ecx
enum_wait:
    testb $1, 12(%rsi)
    jz enum_pause
    mov 12(%rsi), %eax
    and $0xfc00, %eax
    cmp $0x8800, %eax
    je enum_port_event
    cmp $0x8400, %eax
    jne enum_failed
    cmp %rdx, (%rsi)
    jne enum_failed
    cmpb $1, 11(%rsi)
    jne enum_failed
    lea 24(%rsi), %rax
    mov %rax, 0x38(%r9)
    ret
enum_port_event:
    add $16, %rsi
    lea 0x2100(%r8), %rax
    cmp %rax, %rsi
    jae enum_failed
    lea 8(%rsi), %rax
    mov %rax, 0x38(%r9)
enum_pause:
    pause
    loop enum_wait
enum_failed:
    or $1, %eax
    ret
