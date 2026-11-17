# Operation 22 selectors 0x200..0x207 are the keyboard's absolute LED mask.
# EP0 alternates two TDs at the unused end of its startup ring. One output
# may be pending. The live dispatcher owns the shared event ring.
native_keyboard_led_request:
    lea -0x200(%r10), %rax
    cmp $7, %rax
    ja native_keyboard_led_denied
    cmpb $1, %gs:0x3c8
    jne native_keyboard_led_denied
    cmpb $0, %gs:0x7fa
    jne native_keyboard_led_denied
    cmpb $0, %gs:0x7f9
    jne native_keyboard_led_busy
    mov %gs:0x758, %r8
    lea NATIVE_STATE_BEGIN(%r8), %rsi
    cmpb $1, NS_KIND(%rsi)
    je native_keyboard_led_slot
    add $64, %rsi
native_keyboard_led_slot:
    cmpb $1, NS_KIND(%rsi)
    jne native_keyboard_led_denied
    cmpb $1, NS_CONFIGURED(%rsi)
    jne native_keyboard_led_denied
    mov %al, %gs:0x7fb
    mov %al, 0x9900(%r8)
    mov NS_CONTROL(%rsi), %rdx
    movzbl %gs:0x7f8, %ecx
    and $1, %ecx
    imul $48, %ecx, %ecx
    add %rcx, %rdx
    movzbl NS_INTERFACE(%rsi), %eax
    shl $32, %rax
    movabs $0x0001000002000921, %rcx  # SET_REPORT(Output), one byte
    or %rcx, %rax
    mov %rax, (%rdx)
    movl $8, 8(%rdx)
    lea 0x9900(%r8), %rax
    mov %rax, 16(%rdx)
    movl $1, 24(%rdx)
    xor %eax, %eax
    mov %rax, 32(%rdx)
    movl $0, 40(%rdx)
    movzbl %gs:0x7f8, %ecx
    incb %gs:0x7f8
    mov %ecx, %eax
    shr %ecx
    and $1, %ecx
    xor $1, %ecx
    test $1, %al
    jz native_keyboard_led_stages
    mov NS_CONTROL(%rsi), %rax
    mov %rax, 48(%rdx)
    movl $0, 56(%rdx)
    lea 0x1802(%rcx), %eax         # End of ring, toggle cycle
    mov %eax, 60(%rdx)
native_keyboard_led_stages:
    lea 0xc00(%rcx), %eax            # OUT data stage
    mov %eax, 28(%rdx)
    lea 0x11020(%rcx), %eax         # IN status, IOC
    mov %eax, 44(%rdx)
    movb $1, %gs:0x7f9
    sfence
    lea 0x20840(%rcx), %eax         # OUT setup with immediate USB request
    mov %eax, 12(%rdx)
    sfence
    mov %gs:0x748, %rax
    movzbl NS_SLOT(%rsi), %ecx
    movl $1, (%rax,%rcx,4)
    xor %eax, %eax
    ret
native_keyboard_led_busy:
    mov $256, %eax
    ret
native_keyboard_led_denied:
    mov $257, %eax
    ret

# The slot is already validated by the transfer dispatcher. Only events
# pointing to the outstanding LED TD are consumed here.
native_keyboard_led_event:
    cmpb $1, NS_KIND(%rbx)
    jne native_live_identity_failed
    cmpb $1, %gs:0x7f9
    jne native_live_identity_failed
    mov NS_CONTROL(%rbx), %rax
    movzbl %gs:0x7f8, %edx
    dec %edx
    and $1, %edx
    imul $48, %edx, %edx
    add %rdx, %rax
    mov (%rsi), %rdx
    sub %rax, %rdx
    cmp $32, %rdx
    ja native_live_identity_failed
    test $15, %dl
    jnz native_live_identity_failed
    mov 8(%rsi), %eax
    cmp $0x01000000, %eax
    jne native_keyboard_led_rejected
    cmp $32, %edx
    jne native_keyboard_led_rejected
    incq %gs:0x7f0
    jmp native_keyboard_led_done
native_keyboard_led_rejected:
    movb $1, %gs:0x7fa
native_keyboard_led_done:
    movb $0, %gs:0x7f9
    call native_event_advance
    decl %gs:0x7d8
    jnz native_live_again
    jmp native_live_empty
