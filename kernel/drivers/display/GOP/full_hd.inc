#include "../../../loader/native_ui_layout.inc"

# The native Ring 3 surface and GOP have the same dimensions.
#define FHD_W 1920
#define FHD_H 1080
#define FHD_SURFACE_LIMIT (NATIVE_UI_DATA_END - FHD_W * FHD_H * 4)

gop_fhd_frame:
    cmp $FHD_SURFACE_LIMIT, %rdx
    ja .Lgop_copy_denied
    lea -0x3c000000(%rdx), %rsi
    mov 0x10(%rbp), %rdi
    mov $FHD_H, %edx
    mov $FHD_W, %r10d
    xor %r9d, %r9d
    sub %r10d, %r8d
    call .Lgop_rows
    incl %gs:0x354
    ret

gop_fhd_region:
    cmp $FHD_SURFACE_LIMIT, %rdx
    ja gop_cursor_denied
    lea -0x3c000000(%rdx), %rsi
    mov $FHD_W, %r9d
    cmp $0x80000000, %r10d
    jne .Lfhd_cursor
    mov $120, %edx
    mov %r9d, %r10d
    jmp gop_region_copy
.Lfhd_cursor:
    movzwl %r10w, %eax
    shr $16, %r10d
    cmp $FHD_W, %eax
    jae gop_cursor_denied
    cmp $FHD_H, %r10d
    jae gop_cursor_denied

    imul $FHD_W, %r10d, %edx
    add %eax, %edx
    lea (%rsi,%rdx,4), %rsi
    mov %r10d, %edx
    imul %r8d, %edx
    add %eax, %edx
    lea (%rdi,%rdx,4), %rdi

    mov $FHD_H, %edx
    sub %r10d, %edx
    mov $17, %ecx
    cmp %ecx, %edx
    cmova %ecx, %edx
    mov %r9d, %r10d
    sub %eax, %r10d
    mov $12, %ecx
    cmp %ecx, %r10d
    cmova %ecx, %r10d
    jmp gop_region_copy
