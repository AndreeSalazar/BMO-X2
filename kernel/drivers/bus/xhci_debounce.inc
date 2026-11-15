# RDX: PORTSC array, ECX: validated MaxPorts, RSI: one byte per port.
# Sample every >=10 ms. First connected observation is 1; 11 means ten
# unchanged intervals (>=100 ms). Disconnect, lost power or CSC restarts it.
# EAX flags: 1 connected, 2 connected pending, 4 power pending.
xhci_debounce_sample:
    push %rdi
    xor %eax, %eax
debounce_port:
    mov (%rdx), %edi
    test $0x200, %edi
    jz debounce_no_power
    test $1, %edi
    jz debounce_disconnected
    or $1, %eax
    test $0x20000, %edi
    jnz debounce_changed
    cmpb $11, (%rsi)
    jae debounce_advance
    incb (%rsi)
    cmpb $11, (%rsi)
    jae debounce_advance
    jmp debounce_pending
debounce_changed:
    movb $1, (%rsi)
debounce_pending:
    or $2, %eax
    jmp debounce_advance
debounce_no_power:
    or $4, %eax
debounce_disconnected:
    movb $0, (%rsi)
debounce_advance:
    inc %rsi
    add $16, %rdx
    loop debounce_port
    pop %rdi
    ret
