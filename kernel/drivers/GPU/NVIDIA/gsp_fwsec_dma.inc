# Finalize the verified FWSEC V3 payload in its detached DMA reservation.
# R9 is the LoaderData base. The only writable target is this reservation.
nvidia_fwsec_finalize:
    lea GSP_FWSEC_AREA_OFFSET(%r9), %r8
    cmpl $GSP_POST_WPR_READY, GSP_POST_STATUS(%rbp)
    jne .Lfwsec_erase
    cmpl $12288, (GSP_WPR_SAMPLE+8)(%rbp)
    jne .Lfwsec_erase
    mov GSP_FWSEC_FUSE(%rbp), %rdx
    bt $32, %rdx
    jnc .Lfwsec_erase

    xor %ecx, %ecx
    test %edx, %edx
    jz .Lfwsec_version
    bsr %edx, %ecx
    inc %ecx                         # Fuse mask bit length is the version.
.Lfwsec_version:
    cmp $16, %ecx
    jae .Lfwsec_erase
    mov $BMO_FWSEC_SIGNATURE_VERSIONS, %edx
    xor %eax, %eax
.Lfwsec_rank:
    test %ecx, %ecx
    jz .Lfwsec_ranked
    shr %edx
    adc $0, %eax                     # Count supported versions below this one.
    dec %ecx
    jmp .Lfwsec_rank
.Lfwsec_ranked:
    test $1, %edx
    jz .Lfwsec_erase
    cmp $BMO_FWSEC_SIGNATURE_CANDIDATES, %eax
    jae .Lfwsec_erase

    # Patch FRTS from the just-validated WPR, and copy the original RSA signature.
    lea GSP_WPR_AREA_OFFSET(%r9), %rsi
    mov 152(%rsi), %rdx
    shr $12, %rdx
    mov %edx, BMO_FWSEC_FRTS_REGION_OFFSET(%r8)
    mov 160(%rsi), %rdx
    shr $12, %rdx
    mov %edx, (BMO_FWSEC_FRTS_REGION_OFFSET+4)(%r8)
    imul $384, %eax, %eax
    lea BMO_FWSEC_IMAGE_BYTES(%r8,%rax), %rsi
    lea BMO_FWSEC_SIGNATURE_SLOT(%r8), %rdi
    mov $48, %ecx
    cld
    rep movsq

    # Erase the candidates and tail before publishing the firmware read-only.
    lea BMO_FWSEC_IMAGE_BYTES(%r8), %rdi
    mov $((BMO_FWSEC_PAGES*4096-BMO_FWSEC_IMAGE_BYTES)/8), %ecx
    xor %eax, %eax
    rep stosq
    lea (GSP_QUEUE_LEAF_OFFSET+GSP_FWSEC_PAGE_INDEX*8)(%r9), %rdi
    movabs $0x2000000000000001, %rax
    or %r8, %rax
    mov $BMO_FWSEC_PAGES, %ecx
.Lfwsec_map:
    stosq
    add $4096, %rax
    loop .Lfwsec_map
    movq $GSP_FWSEC_IOVA, GSP_POST_FWSEC(%rbp)
    movl $GSP_POST_FWSEC_READY, GSP_POST_STATUS(%rbp)
    ret
.Lfwsec_erase:
    mov %r8, %rdi
    mov $(BMO_FWSEC_PAGES*512), %ecx
    xor %eax, %eax
    cld
    rep stosq
    ret
