# R11 points to operational registers. Status is returned through ZF.
# The caller has validated the capability page and firmware ownership.
xhci_reset:
    mov $0x800, %eax             # CNR must clear before USBCMD writes.
    xor %esi, %esi
    call command_poll
    jne reset_done
    movl $0, (%r11)
    mov $1, %eax                 # Wait for HCHalted.
    mov $1, %esi
    call command_poll
    jne reset_done
    movb $1, %gs:0x3b9
    movl $2, (%r11)
    mov $2, %eax                 # Wait for HCRST to clear.
    xor %esi, %esi
    call command_poll
    jne reset_done
    movb $2, %gs:0x3b9
    mov $0x800, %eax
    call command_poll
    jne reset_done
    testl $1, 8(%r11)            # PAGESIZE supports 4 KiB.
    jz reset_done
    movb $3, %gs:0x3b9
    xor %eax, %eax
    ret
reset_done:
    # Return NZ for a timeout or unsupported page size.
    or $1, %eax
    ret

# Compare the requested mask with zero or the mask itself. ZF reports success.
command_poll:
    neg %esi
    and %eax, %esi
    mov $100000, %ecx
command_poll_next:
    mov 4(%r11), %edx
    test $2, %al
    jz command_poll_compare
    mov (%r11), %edx
command_poll_compare:
    and %eax, %edx
    cmp %esi, %edx
    je command_poll_done
    pause
    loop command_poll_next
command_poll_done:
    ret
