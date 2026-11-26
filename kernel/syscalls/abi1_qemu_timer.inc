# QEMU PC only. The guest exits through debug-exit after this trial.
.Labi1_timer_start:
    mov $0x20, %edi
    lea .Labi1_timer_irq(%rip), %rax
    call .Lgate
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
    ret

.Labi1_timer_irq:
    push %rax
    addq $10000150, ABI_TIME_NS
    mov $0x20, %al
    out %al, $0x20
    pop %rax
    iretq
