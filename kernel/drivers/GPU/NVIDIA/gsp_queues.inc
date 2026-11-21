# Encode the 615.78.08 RMARGS and MSGQ 2.0 layout in zeroed LoaderData.
# R9 = validated image base, RBP = supervisor context.
# The queue IOVA aperture is disjoint from the read-only firmware.
nvidia_gsp_init_queues:
    lea GSP_QUEUE_AREA_OFFSET(%r9), %rdi
    movl $0x20505347, (%rdi)             # "GSP ".
    movw $184, 4(%rdi)                  # GSP_ARGUMENTS_CACHED.
    movq $2, 8(%rdi)                    # Stack in DMEM.
    movq $(GSP_QUEUE_IOVA+4096), 24(%rdi)
    movq $4096, 32(%rdi)                # GspMem command queue offset.
    movq $(4096+GSP_QUEUE_BYTES), 40(%rdi)
    movl $24, 48(%rdi)
    movl $4096, 52(%rdi)
    movl $65536, 56(%rdi)
    movl $4, 60(%rdi)
    movl $12, 64(%rdi)
    movl $GSP_SHARED_QUEUE_PAGES, 68(%rdi)

    add $4096, %rdi
    mov $(GSP_QUEUE_IOVA+4096), %eax
    mov $GSP_SHARED_QUEUE_PAGES, %ecx
.Lgsp_queue_address:
    stosq
    add $4096, %rax
    loop .Lgsp_queue_address
    lea (GSP_QUEUE_AREA_OFFSET+8192)(%r9), %rdi
    movw $2, (%rdi)
    movl $GSP_QUEUE_BYTES, 4(%rdi)
    movl $4096, 8(%rdi)
    movl $(GSP_QUEUE_PAGE_COUNT-1), 12(%rdi)
    movl $4096, 16(%rdi)

    # The metadata pages are read-only. Both message queues can be
    # written by the GSP. The IOMMU leaf itself has no device mapping.
    lea GSP_QUEUE_LEAF_OFFSET(%r9), %rdi
    movabs $0x2000000000000001, %rsi
    lea GSP_QUEUE_AREA_OFFSET(%r9), %rax
    or %rsi, %rax
    stosq
    add $4096, %rax
    stosq
    add $4096, %rax
    movabs $0x4000000000000000, %rsi
    or %rsi, %rax
    mov $(GSP_QUEUE_AREA_PAGES-2), %ecx
.Lgsp_queue_page:
    stosq
    add $4096, %rax
    loop .Lgsp_queue_page
    lea (GSP_QUEUE_LEAF_OFFSET+0x201)(%r9), %rax
    movabs $0x6000000000000000, %rsi
    or %rsi, %rax
    mov %rax, (GSP_DMA_TABLE_OFFSET+(GSP_QUEUE_IOVA >> 21)*8)(%r9)
    movq $GSP_QUEUE_IOVA, GSP_POST_RMARGS(%rbp)
    ret
