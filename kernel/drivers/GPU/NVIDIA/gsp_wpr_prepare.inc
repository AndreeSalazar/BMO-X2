# GA106, cold boot, 615.78.08. Build WPR V1 in the reserved DMA page.
# R9 is the validated LoaderData base. No VRAM, MMIO or PCI writes here.
nvidia_gsp_prepare_wpr:
    lea GSP_WPR_SAMPLE(%rbp), %rsi
    testb $1, (%rsi)                      # GFW scratch readable at level 0.
    jz .Lwpr_skip
    cmpb $0xff, 4(%rsi)                  # GFW initialization complete.
    jne .Lwpr_skip
    cmpl $16, 28(%rsi)                    # WPR2 high address (31:4) is zero.
    jae .Lwpr_skip
    mov $4, %ecx
.Lwpr_pri_check:
    mov -4(%rsi,%rcx,4), %eax
    cmp $-1, %eax
    je .Lwpr_skip
    shr $20, %eax
    cmp $0xbad, %eax
    je .Lwpr_skip
    loop .Lwpr_pri_check
    cmpl $256, 8(%rsi)
    jb .Lwpr_skip

    push %r10
    push %r11
    push %r12
    push %r13
    push %r14
    mov 8(%rsi), %r10d
    shl $20, %r10                        # Usable VRAM from VBIOS.
    lea -0x100000(%r10), %r11            # NV_PRAMIN size when VGA is invalid.
    mov 12(%rsi), %eax
    test $8, %al
    jz .Lwpr_workspace
    shr $8, %eax
    shl $16, %rax
    cmp %r10, %rax
    jae .Lwpr_restore
    cmp %r11, %rax
    lea -0x20000(%r10), %rsi             # Relocate a low VGA workspace.
    cmovae %rax, %r11
    cmovb %rsi, %r11
.Lwpr_workspace:
    # The 615.78.08 GA106 HAL reports no VBIOS MMU-lock constraint.
    mov %r11, %r12
    and $-0x20000, %r12                   # End of WPR, aligned to 128 KiB.
    lea -0x100000(%r12), %r8             # FRTS is one MiB.
    lea -BMO_GSP_MONITOR_BYTES(%r8), %rdx
    and $-4096, %rdx                     # Signed monitor in VRAM.
    lea -BMO_GSP_IMAGE_BYTES(%rdx), %r13
    and $-0x10000, %r13                  # Firmware ELF, 64 KiB aligned.

    lea 0x3fffffff(%r10), %rax
    shr $30, %rax
    imul $98304, %rax, %rax              # Heap bytes per GiB, round up to MiB.
    add $0x0fffff, %rax
    and $-0x100000, %rax
    add $0x7e00000, %rax                  # OS 22 MiB + RM 8 MiB + client 96 MiB.
    mov %r13, %r14
    sub %rax, %r14
    and $-0x100000, %r14                 # WPR heap start.
    lea -0x200000(%r14), %rcx            # Metadata MiB and non-WPR heap MiB.
    lea -0x10000000(%r10), %rsi          # GA106 top 256 MiB pre-scrubbed.
    cmp %rsi, %rcx
    jl .Lwpr_restore

    lea GSP_WPR_AREA_OFFSET(%r9), %rdi
    movabs $0xdc3aae21371a60b3, %rsi
    mov %rsi, (%rdi)
    movq $1, 8(%rdi)
    movq $(GSP_DMA_FIRST_IOVA+GSP_RADIX_OFFSET), 16(%rdi)
    movq $BMO_GSP_IMAGE_BYTES, 24(%rdi)
    movq $GSP_BOOT_IOVA, 32(%rdi)
    movq $BMO_GSP_MONITOR_BYTES, 40(%rdi)
    movq $BMO_GSP_MONITOR_CODE, 48(%rdi)
    movq $BMO_GSP_MONITOR_DATA, 56(%rdi)
    movq $BMO_GSP_MONITOR_MANIFEST, 64(%rdi)
    movq $(GSP_DMA_FIRST_IOVA+BMO_GSP_IMAGE_BYTES), 72(%rdi)
    movq $4096, 80(%rdi)
    mov %rcx, 88(%rdi)
    mov %rcx, 96(%rdi)
    movq $0x100000, 104(%rdi)
    lea 0x100000(%rcx), %rsi
    mov %rsi, 112(%rdi)
    mov %r14, 120(%rdi)
    mov %rax, 128(%rdi)
    mov %r13, 136(%rdi)
    mov %rdx, 144(%rdi)
    mov %r8, 152(%rdi)
    movq $0x100000, 160(%rdi)
    mov %r12, 168(%rdi)
    mov %r10, 176(%rdi)
    mov %r11, 184(%rdi)
    sub %r11, %r10
    mov %r10, 192(%rdi)

    # SEC2 will write the verification result in this page. The other
    # signed boot pages remain read-only and the domain stays detached.
    movabs $0x6000000000000001, %rsi
    or %rsi, %rdi
    mov %rdi, (GSP_QUEUE_LEAF_OFFSET+GSP_WPR_PAGE_INDEX*8)(%r9)
    movq $GSP_WPR_IOVA, GSP_POST_WPR(%rbp)
    movl $GSP_POST_WPR_READY, GSP_POST_STATUS(%rbp)
.Lwpr_restore:
    pop %r14
    pop %r13
    pop %r12
    pop %r11
    pop %r10
.Lwpr_skip:
    ret
