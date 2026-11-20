#ifdef XHCI_NATIVE_DUAL
#define XHCI_TRANSPORT_PROBE
#endif
#ifdef XHCI_TRANSPORT_PROBE
#define XHCI_COMMAND_PROBE
#endif
.text
#ifdef XHCI_COMMAND_PROBE
    .byte 0xe9
    .long usb_controllers - . - 4
    .byte 0xe9
    .long xhci_live_report - . - 4
    .byte 0xe9
    .long xhci_live_stop - . - 4
#ifdef XHCI_NATIVE_DUAL
    .byte 0xe9
    .long native_mouse_descriptor - . - 4
#endif
#endif
# Inventory each xHC before choosing a controller. Restore PCI selector.
# One scan per boot, including bridges and multifunction devices.
usb_controllers:
    cmpb $0, %gs:0x35c
    jne inventory_cached
    mov $0xcf8, %edx
    in %dx, %eax
    mov %eax, %r9d
    mov $0x80000008, %ecx
    xor %r8d, %r8d
inventory_next:
    mov %ecx, %eax
    out %eax, %dx
    add $4, %edx
    in %dx, %eax
    sub $4, %edx
    shr $8, %eax
    cmp $0x0c0330, %eax
    jne inventory_advance
    inc %r8d
    push %rcx
    push %rdx
    push %r8
    push %r9
    call inventory_function
#if defined(XHCI_RESET_PROBE) || defined(XHCI_TRANSPORT_PROBE)
    call xhci_reset_candidate
    test %eax, %eax
    jz inventory_continue
#endif
    call xhci_read_caps
    cmp %gs:0x3b0, %eax
    jbe inventory_continue
    mov %eax, %gs:0x3b0
    mov 24(%rsp), %eax
    mov %eax, %gs:0x3b4
inventory_continue:
    pop %r9
    pop %r8
    pop %rdx
    pop %rcx
    jmp inventory_advance
inventory_function:
    mov %ecx, %eax
    and $0x00ffff00, %eax
    shr $8, %eax
    mov %eax, %gs:0x360
    lea 8(%ecx), %eax
    out %eax, %dx
    add $4, %edx
    in %dx, %eax
    mov %eax, %gs:0x364
    sub $4, %edx
    lea 12(%ecx), %eax
    out %eax, %dx
    add $4, %edx
    in %dx, %eax
    mov %eax, %gs:0x368
    sub $4, %edx
    lea -4(%ecx), %eax
    out %eax, %dx
    add $4, %edx
    in %dx, %eax
    mov %ax, %gs:0x36c
    sub $4, %edx
    ret
inventory_advance:
    add $0x100, %ecx
    cmp $0x81000008, %ecx
    jne inventory_next
    mov %r8d, %gs:0x358
    movb $1, %gs:0x35c
    mov %gs:0x3b4, %ecx
    test %ecx, %ecx
    jz inventory_restore
    call inventory_function
inventory_restore:
    mov %r9d, %eax
    out %eax, %dx
    test %ecx, %ecx
    jz inventory_cached
    movb $1, %gs:0x3b8
    call xhci_read_caps
inventory_cached:
    mov %gs:0x358, %eax
    ret

#if defined(XHCI_RESET_PROBE) || defined(XHCI_TRANSPORT_PROBE)
# Read vendor/device from the function currently being ranked.
xhci_reset_candidate:
    lea -8(%ecx), %eax
    out %eax, %dx
    add $4, %dx
    in %dx, %eax
    sub $4, %dx
    cmp $0x149c1022, %eax       # AMD xHCI in the target machine.
    je reset_candidate_yes
    cmp $0x000d1b36, %eax       # QEMU emulator for verification.
    je reset_candidate_yes
    xor %eax, %eax
    ret
reset_candidate_yes:
    mov $1, %eax
    ret
#endif

# Use a temporary supervisor-only 4 KiB mapping in the private page tables.
# Context page 0x1e is reserved here for the alias PT, below the boot stack.
xhci_read_caps:
    testw $2, %gs:0x36c
    jz caps_done
    mov %gs:0x364, %eax
    mov %eax, %ecx
    and $0x0f, %ecx
    and $-16, %eax
    cmp $4, %ecx
    je caps_64
    test %ecx, %ecx
    jnz caps_done
    jmp caps_address
caps_64:
    mov %gs:0x368, %edx
    cmp $0xff, %edx
    ja caps_done
    shl $32, %rdx
    or %rdx, %rax
caps_address:
    cmp $0x10000000, %rax
    jb caps_done
    test $0xfff, %eax
    jnz caps_done
    # Reject overlap with a firmware memory descriptor other than MMIO.
    mov 0x60(%rbp), %r8
    cmp $40, %r8
    jb caps_done
    cmp $256, %r8
    ja caps_done
    mov 0x50(%rbp), %rcx
    cmp $65536, %rcx
    ja caps_done
    lea 0x1000(%rbp), %rsi
caps_map_next:
    test %rcx, %rcx
    jz caps_map
    cmp %r8, %rcx
    jb caps_done
    mov 8(%rsi), %rdx
    cmp %rax, %rdx
    ja caps_map_advance
    mov %rax, %rdi
    sub %rdx, %rdi
    shr $12, %rdi
    cmp 24(%rsi), %rdi
    jae caps_map_advance
    cmpl $11, (%rsi)
    jne caps_done
caps_map_advance:
    add %r8, %rsi
    sub %r8, %rcx
    jmp caps_map_next
caps_map:
    lea 0x1e000(%rbp), %rdi
    mov %rax, %r8
    xor %eax, %eax
    mov $512, %ecx
    cld
    rep stosq
    lea 0x1e003(%rbp), %rax
    mov %rax, 0x15400(%rbp)
    or $0x19, %r8
    bts $63, %r8
    mov %r8, 0x1e000(%rbp)
    mov $0x10000000, %edi
    invlpg (%rdi)
    mov (%rdi), %eax
    mov 4(%rdi), %edx
    mov %eax, %gs:0x370
    mov %edx, %gs:0x374
    cmpb $0, %gs:0x3b8
    je xhci_census
    # Record DMA requirements before doing anything to the controller.
    mov 8(%rdi), %eax
    mov %eax, %ecx
    shr $27, %eax
    shr $16, %ecx
    and $0x3e0, %ecx
    or %ecx, %eax
    mov %eax, %gs:0x3bc
    mov 0x10(%rdi), %eax
    and $4, %eax
    shl $3, %eax
    add $32, %eax
    mov %eax, %gs:0x3c0
    call xhci_handoff
#ifdef XHCI_RESET_PROBE
    call xhci_reset_probe
#endif
#ifdef XHCI_COMMAND_PROBE
    push %rbx
    push %rdi
    call xhci_test_command
    pop %rdi
    pop %rbx
    cmpb $1, %gs:0x3c8
    je caps_done
#endif
    xor %eax, %eax
    jmp xhci_unmap
xhci_census:
    call xhci_count_ports
    jmp xhci_unmap
# Return PORTSC.CCS count plus one, or zero for invalid geometry.
xhci_count_ports:
    movzbl %al, %ecx
    cmp $0x20, %ecx
    jb xhci_census_invalid
    test $3, %ecx
    jnz xhci_census_invalid
    shr $24, %edx
    jz xhci_census_invalid
    lea 0x400(%rdi,%rcx), %rsi
    lea (%rsi,%rdx,8), %rax
    lea (%rax,%rdx,8), %rax
    lea 4096(%rdi), %rcx
    cmp %rcx, %rax
    ja xhci_census_invalid
    mov $1, %eax                 # Rank valid empty controllers below connected ones.
xhci_port_next:
    mov (%rsi), %ecx
    and $1, %ecx
    add %ecx, %eax
    add $16, %rsi
    dec %edx
    jnz xhci_port_next
    ret
xhci_census_invalid:
    xor %eax, %eax
    ret
xhci_unmap:
#if defined(RMLUI_USB) && defined(XHCI_MOUSE_PROBE)
    # Compact zeroing keeps this bounded stage in its one reserved page.
    # Preserve EAX: inventory ranking returns the connected-port score here.
    xor %r10d, %r10d
    mov %r10, 0x15400(%rbp)
    mov %r10, 0x1e000(%rbp)
#else
    movq $0, 0x15400(%rbp)
    movq $0, 0x1e000(%rbp)
#endif
    invlpg (%rdi)
    ret

# Status: 0 unavailable, 1 no legacy capability, 2 owned, 3 timed out,
# 4 malformed or outside this mapped page.
xhci_handoff:
    mov %gs:0x370, %eax
    cmp $0x20, %al
    jb caps_done
    test $3, %al
    jnz caps_done
    mov %eax, %ecx
    shr $16, %ecx
    cmp $0x96, %ecx
    jb caps_done
    cmp $0x200, %ecx
    jae caps_done
    mov %gs:0x374, %edx
    test %dl, %dl
    jz caps_done
    test $0xff000000, %edx
    jz caps_done
    mov 0x10(%rdi), %eax
    shr $16, %eax
    test %eax, %eax
    jz legacy_absent
    mov $64, %r8d
legacy_next:
    cmp $8, %eax
    jb legacy_invalid
    cmp $1022, %eax
    ja legacy_invalid
    mov (%rdi,%rax,4), %ecx
    test %cl, %cl
    jz legacy_invalid
    cmp $0xff, %cl
    je legacy_invalid
    cmp $1, %cl
    je legacy_claim
    movzbl %ch, %ecx
    test %ecx, %ecx
    jz legacy_absent
    add %ecx, %eax
    dec %r8d
    jnz legacy_next
legacy_invalid:
    movb $4, %gs:0x378
    ret
legacy_absent:
    movb $1, %gs:0x378
#if !defined(XHCI_COMMAND_PROBE) && !defined(XHCI_RESET_PROBE)
    jmp legacy_sample
#else
    ret
#endif
legacy_claim:
#if !defined(XHCI_COMMAND_PROBE) && !defined(XHCI_RESET_PROBE)
    # Inventory does not request ownership from firmware.
    movb $5, %gs:0x378
    jmp legacy_sample
#else
    # Enable writes only for the OS semaphore byte. Preserve the BIOS byte.
    orq $2, 0x1e000(%rbp)
    invlpg (%rdi)
    lea (%rdi,%rax,4), %rsi
    movzbl 3(%rsi), %edx
    orb $1, 3(%rsi)
    mov $100000, %ecx
legacy_wait:
    testb $1, 2(%rsi)
    jz legacy_owned
    pause
    loop legacy_wait
    mov %dl, 3(%rsi)
    movb $3, %gs:0x378
    ret
legacy_owned:
    movb $2, %gs:0x378
#endif
#if !defined(XHCI_COMMAND_PROBE) && !defined(XHCI_RESET_PROBE)
legacy_sample:
    mov %gs:0x370, %eax
    call xhci_preflight
#endif
caps_done:
    xor %eax, %eax
    ret

#ifdef XHCI_COMMAND_PROBE
#ifdef XHCI_NATIVE_DUAL
#include "native/controller.inc"
#include "xhci_validate_dma.inc"
#include "xhci_transport_layout.inc"
#include "xhci_transport_mmio.inc"
#include "xhci_transport_ports.inc"
#else
#include "xhci_command_probe.inc"
#endif
#include "xhci_reset.inc"
#else
#include "xhci_preflight.inc"
#ifdef XHCI_RESET_PROBE
#include "xhci_reset.inc"
#include "xhci_reset_probe.inc"
#endif
#endif
