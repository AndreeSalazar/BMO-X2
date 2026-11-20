.text
#define DESKTOP_READER_OFFSET 0x3000
#ifdef RMLUI_GOP_REGIONS
#include "../../drivers/display/GOP/gop_layout.inc"
#endif
# Position-independent extension of the inherited EFI reader.
# The original reader has closed its files and saved SimpleFileSystem in RBP+88h.
.globl desktop_media_read
desktop_media_read:
    # The original reader expects the EFI caller's original stack alignment.
    sub $8, %rsp
    .byte 0xe8
    .long 0x800 - DESKTOP_READER_OFFSET - (. - desktop_media_read) - 4
    add $8, %rsp
    test %rax, %rax
    js done

    # Preserve the inherited INICIO.X86 length. Use separate context fields.
    sub $40, %rsp
#ifdef RMLUI_USB
#ifdef XHCI_NATIVE_DUAL
    # Separate LoaderCode pages: the legacy one-page stage remains unchanged.
    movq $0x0fffffff, 0x728(%rbp)
    mov $1, %ecx
    mov $1, %edx
    mov $2, %r8d
    lea 0x728(%rbp), %r9
    call *0x28(%r14)
    test %rax, %rax
    js failed
    movq $2, 0x730(%rbp)
#endif
    # Private QEMU USB transport: reserve DMA before the final UEFI map.
    movq $0x0fffffff, 0xb8(%rbp)
    mov $1, %ecx
    mov $2, %edx
#ifdef XHCI_NATIVE_DUAL
    mov $14, %r8d
#else
    mov $10, %r8d
#endif
    lea 0xb8(%rbp), %r9
    call *0x28(%r14)
    test %rax, %rax
    js failed
#ifdef XHCI_NATIVE_DUAL
    movq $14, 0xc0(%rbp)
#else
    movq $10, 0xc0(%rbp)
#endif
    mov 0xb8(%rbp), %rdi
    xor %eax, %eax
#ifdef XHCI_NATIVE_DUAL
    mov $7168, %ecx
#else
    mov $5120, %ecx
#endif
    cld
    rep stosq
#endif
#ifdef RMLUI_MEDIA
    movq $0x0fffffff, 0xa8(%rbp)
    mov $1, %ecx                 # AllocateMaxAddress, inside the identity map
#else
    xor %ecx, %ecx
#endif
    mov $2, %edx
#ifdef RMLUI_MEDIA
    mov $513, %r8d
#else
    mov $5, %r8d
#endif
    lea 0xa8(%rbp), %r9
    call *0x28(%r14)
    test %rax, %rax
    js failed
#ifdef RMLUI_MEDIA
    movq $513, 0xc8(%rbp)
#else
    movq $5, 0xc8(%rbp)
#endif
    mov 0x88(%rbp), %rcx
    lea 0x38(%rbp), %rdx
    call *8(%rcx)
    test %rax, %rax
    js release
    mov 0x38(%rbp), %rcx
    lea 0x40(%rbp), %rdx
    lea path(%rip), %r8
    mov $1, %r9d
    movq $0, 32(%rsp)
    call *8(%rcx)
    test %rax, %rax
    js release
#ifdef RMLUI_MEDIA
    movq $0x200001, 0xb0(%rbp)
#else
    movq $16513, 0xb0(%rbp)
#endif
    mov 0x40(%rbp), %rcx
    lea 0xb0(%rbp), %rdx
    mov 0xa8(%rbp), %r8
    call *0x20(%rcx)
    test %rax, %rax
    js release
#ifdef RMLUI_MEDIA
    cmpq $0x200000, 0xb0(%rbp)
#else
    cmpq $16512, 0xb0(%rbp)
#endif
    ja release
    cmpq $64, 0xb0(%rbp)
    jb release
    mov 0x40(%rbp), %rcx
    movq $0, 0x40(%rbp)
    call *0x10(%rcx)
    test %rax, %rax
    js release
#ifdef ULTRA_J_MEDIA
    # The action is a separate FAT32 file, bounded before ExitBootServices.
    mov 0x38(%rbp), %rcx
    lea 0x40(%rbp), %rdx
    lea action_path(%rip), %r8
    mov $1, %r9d
    movq $0, 32(%rsp)
    call *8(%rcx)
    test %rax, %rax
    js release
    movq $513, 0x600(%rbp)
    mov 0x40(%rbp), %rcx
    lea 0x600(%rbp), %rdx
    lea 0xa00(%rbp), %r8
    call *0x20(%rcx)
    test %rax, %rax
    js release
    cmpq $512, 0x600(%rbp)
    ja release
    cmpq $9, 0x600(%rbp)
    jb release
    mov 0x40(%rbp), %rcx
    movq $0, 0x40(%rbp)
    call *0x10(%rcx)
    test %rax, %rax
    js release
#endif
    call cache_profile
    call boot_report
    # Return the unused tail to firmware before taking the final memory map.
    mov 0xb0(%rbp), %rax
    add $4095, %rax
    shr $12, %rax
#ifdef RMLUI_MEDIA
    mov $513, %edx
#else
    mov $5, %edx
#endif
    sub %eax, %edx
    jz staging_ready
    mov %rax, 32(%rsp)
    shl $12, %rax
    add 0xa8(%rbp), %rax
    mov %rax, %rcx
    call *0x30(%r14)
    test %rax, %rax
    js staging_ready
    mov 32(%rsp), %rax
    mov %rax, 0xc8(%rbp)
staging_ready:
    mov 0x38(%rbp), %rcx
    movq $0, 0x38(%rbp)
    call *0x10(%rcx)
    test %rax, %rax
    js release
#if defined(RMLUI_GOP_REGIONS) && !defined(BMO_FULL_HD)
    lea .Lgop_stage(%rip), %rsi
    lea GOP_CODE_OFFSET(%rbp), %rdi
    mov $(.Lgop_stage_end - .Lgop_stage), %ecx
    cld
    rep movsb
#endif
#if !defined(RMLUI_MEDIA) || defined(RMLUI_USB)
    # Copy the xHCI stage to the page between the packet buffer and page tables.
    .byte 0x48, 0x8d, 0x35
    .long 0x4000 - DESKTOP_READER_OFFSET - (. - desktop_media_read) - 4
#ifdef XHCI_NATIVE_DUAL
    mov 0x728(%rbp), %rdi
    mov $1024, %ecx
#else
    lea 0x12000(%rbp), %rdi
    mov $512, %ecx
#endif
    cld
    rep movsq
#endif
    xor %eax, %eax
    jmp finish
release:
    # The inherited error path closes any handles that are still open.
    mov 0xa8(%rbp), %rcx
    mov 0xc8(%rbp), %rdx
    call *0x30(%r14)
failed:
    lea error(%rip), %rbx
    mov $-1, %rax
finish:
    add $40, %rsp
done:
    ret

#include "../../arch/x86_64/cpu/cache_profile.inc"
#include "desktop_boot_report.inc"

    # UEFI accepts CHAR16 paths at aligned addresses.
    .p2align 1
path:
#if defined(BMO_NVIDIA_PCI_PROBE)
    # \BMO-X2\GPU\DESKTOP.SBF
    .short 92,66,77,79,45,88,50,92,71,80,85,92,68,69,83,75,84,79,80,46,83,66,70,0
#elif defined(RMLUI_MEDIA)
    .short 92,66,77,79,45,88,50,92,68,69,83,75,84,79,80,92,68,69,83,75,84,79,80,46,83,66,70,0
#else
    # \BMO-X2\DESKTOP.SBF
    .short 92,66,77,79,45,88,50,92,68,69,83,75,84,79,80,46,83,66,70,0
#endif
#ifdef ULTRA_J_MEDIA
action_path:
    # \BMO-X2\ACTION.UJB
    .short 92,66,77,79,45,88,50,92,65,67,84,73,79,78,46,85,74,66,0
#endif
error:
    .short 66,77,79,45,88,50,58,32,101,114,114,111,114,32,68,69,83,75,84,79,80,46,83,66,70,13,10,0
#if defined(RMLUI_GOP_REGIONS) && !defined(BMO_FULL_HD)
#include "../../drivers/display/GOP/gop_stage.inc"
#endif
