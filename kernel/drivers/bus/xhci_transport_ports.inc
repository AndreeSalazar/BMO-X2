# Finite boot probe, with the xHC already running and port geometry validated.
# Do not echo RW1C, PED, PR, WPR or LWS bits when asserting port power.
# Preserve all persistent controller and DMA pointers in R8-R11/RDI/RBP.
xhci_transport_ports:
    movl $18, %gs:0x3e0
    movzbl %gs:0x377, %ecx    # HCSPARAMS1.MaxPorts.
    lea 0x400(%r11), %rsi
    testb $8, 0x10(%rdi)     # HCCPARAMS1.PPC.
    jz transport_ports_wait
transport_power_next:
    mov (%rsi), %eax
    test $0x200, %eax
    jnz transport_power_advance
    and $0x0e00c3e0, %eax    # Writable state only; change flags stay zero.
    or $0x200, %eax
    mov %eax, (%rsi)
    incl %gs:0x3f8
transport_power_advance:
    add $16, %rsi
    loop transport_power_next
transport_ports_wait:
    # Channel 2 supplies real time without IRQs or channel 0 desktop ticks.
    # 11932 ticks at 1193182 Hz, twenty times: slightly more than 200 ms.
    in $0x61, %al
    movzbl %al, %ebx
    mov $20, %esi
transport_settle_next:
    mov %bl, %al
    and $0xfc, %al           # Gate low, speaker off.
    out %al, $0x61
    mov $0xb0, %al           # Channel 2, LSB/MSB, one-shot mode 0.
    out %al, $0x43
    mov $0x9c, %al
    out %al, $0x42
    mov $0x2e, %al
    out %al, $0x42
    # Mode 0 must drive OUT low after loading, even if no PIT is present.
    in $0x61, %al
    test $0x20, %al
    jnz transport_timer_failed
    mov %bl, %al
    and $0xfc, %al
    or $1, %al               # Gate high starts counting, without speaker.
    out %al, $0x61
    mov $2000000, %ecx
transport_timer_poll:
    in $0x61, %al
    test $0x20, %al
    jnz transport_timer_elapsed
    pause
    loop transport_timer_poll
    jmp transport_timer_failed
transport_timer_elapsed:
    incl %gs:0x3fc
    dec %esi
    jnz transport_settle_next
    mov %bl, %al
    out %al, $0x61           # Restore original gate/speaker bits.
    mov 4(%r11), %eax
    mov %eax, %gs:0x3ec      # USBSTS at census time, before stopping the xHC.
    mov %gs:0x370, %eax
    mov %gs:0x374, %edx
    call xhci_count_ports
    mov %eax, %gs:0x3e8      # Preserve running census across controller stop.
    xor %eax, %eax
    ret
transport_timer_failed:
    mov %bl, %al
    out %al, $0x61
    or $1, %eax
    ret
