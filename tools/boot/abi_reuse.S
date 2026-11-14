.text
# Enter after the CASM handler has invalidated and scrubbed the first client.
# RBX is not used. R11 is the original private page-table reservation.
    lea 0x7000(%r11), %r8
    cmpb $0, 0x350(%r8)
    jne done
    cmpq $3, 0x310(%r8)
    jne failed
    mov 0x4000(%r11), %rax
    or 0x4008(%r11), %rax
    jnz failed
    lea 0x5000(%r11), %rdi
    mov $1024, %ecx
    cld
    repe scasq
    jne failed
    movb $1, 0x350(%r8)
    movq $0, 0x310(%r8)

    # The builder admits the second SBEF before embedding it here.
    # Copy only its RX bytes and restore the same RX and RW/NX mappings.
    lea next_image(%rip), %rsi
    mov 44(%rsi), %ecx
    mov 16(%rsi), %r9
    add $64, %rsi
    lea 0x5000(%r11), %rdi
    rep movsb
    lea 0x5005(%r11), %rax
    mov %rax, 0x4000(%r11)
    lea 0x6007(%r11), %rax
    bts $63, %rax
    mov %rax, 0x4008(%r11)
    mov %cr3, %rax
    mov %rax, %cr3
    add $48, %rsp
    pushq $0x1b
    pushq $0x40002000
    pushq $2
    pushq $0x23
    push %r9
    iretq
failed:
    hlt
    jmp failed
done:
    movb $2, 0x350(%r8)
    mov $1, %r12d
    .byte 0xe9
    .long 0
next_image:
