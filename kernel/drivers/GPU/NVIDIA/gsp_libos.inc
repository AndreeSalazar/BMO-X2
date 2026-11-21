# GA10x LIBOS 3 release logging regions and RMARGS descriptor. R9 is
# the validated reservation. This only extends the detached DMA tree.
nvidia_gsp_init_libos:
    lea GSP_LIBOS_AREA_OFFSET(%r9), %rdi
    lea .Lgsp_libos_descriptors(%rip), %rsi
    mov $(.Lgsp_libos_end-.Lgsp_libos_descriptors)/8, %ecx
    rep movsq

    lea (GSP_LIBOS_AREA_OFFSET+4096)(%r9), %rdx
    lea .Lgsp_libos_descriptors(%rip), %rsi
    mov $(.Lgsp_libos_rmargs-.Lgsp_libos_descriptors)/32, %ecx
.Lgsp_libos_seed_log:
    mov 8(%rsi), %rax
    mov %rax, 8(%rdx)                      # Self IOVA after producer pointer.
    add 16(%rsi), %rdx
    add $32, %rsi
    loop .Lgsp_libos_seed_log

    lea (GSP_QUEUE_LEAF_OFFSET+GSP_LIBOS_PAGE_INDEX*8)(%r9), %rdi
    lea GSP_LIBOS_AREA_OFFSET(%r9), %rax
    movabs $0x2000000000000001, %rsi
    or %rsi, %rax
    stosq                                   # Arguments are read-only to the GPU.
    add $4096, %rax
    movabs $0x4000000000000000, %rsi
    or %rsi, %rax
    mov $GSP_LIBOS_LOG_PAGES, %ecx
.Lgsp_libos_map_log:
    stosq
    add $4096, %rax
    loop .Lgsp_libos_map_log
    movq $GSP_LIBOS_IOVA, GSP_POST_LIBOS(%rbp)
    ret

.balign 8
.Lgsp_libos_descriptors:
.macro gsp_libos_region tag, first, pages
    .quad \tag, GSP_LIBOS_IOVA+4096*(1+\first), 4096*\pages, 0x101
.endm
    gsp_libos_region 0x4c4f47494e4954,  0, 16 # LOGINIT
    gsp_libos_region 0x4c4f47494e5452, 16, 16 # LOGINTR
    gsp_libos_region 0x4c4f47524d,     32, 16 # LOGRM
    gsp_libos_region 0x4c4f474d4e4f43, 48, 16 # LOGMNOC
    gsp_libos_region 0x4c4f47444247,   64, 16 # LOGDBG
    gsp_libos_region 0x4c4f47524f4f54, 80,  1 # LOGROOT
    gsp_libos_region 0x4c4f47524d4f4e, 81,  1 # LOGRMON
    gsp_libos_region 0x4c4f474b524e4c, 82, 16 # LOGKRNL
.Lgsp_libos_rmargs:
    .quad 0x524d41524753, GSP_QUEUE_IOVA, 4096, 0x101
.Lgsp_libos_end:
