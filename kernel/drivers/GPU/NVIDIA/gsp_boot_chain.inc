# Install read-only entries for the staged monitor and SEC2 files. R9
# is the validated reservation. The DMA tree still has no requester.
nvidia_gsp_map_boot_chain:
    lea (GSP_QUEUE_LEAF_OFFSET+GSP_SHARED_AREA_PAGES*8)(%r9), %rdi
    lea GSP_BOOT_AREA_OFFSET(%r9), %rax
    movabs $0x2000000000000001, %rsi
    or %rsi, %rax
    mov $BMO_GSP_BOOT_PAGES, %ecx
.Lgsp_map_signed_page:
    stosq
    add $4096, %rax
    loop .Lgsp_map_signed_page
    movq $GSP_BOOT_IOVA, GSP_POST_BOOT_CHAIN(%rbp)
    ret
