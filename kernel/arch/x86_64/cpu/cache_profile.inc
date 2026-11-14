# Cold boot inventory. Context D0-D3 holds the CPUID leaf; D4-EB holds
# three pairs of raw EBX/ECX values in data, instruction, unified order.
# EC-EF holds the presence bitmap for those pairs.
cache_profile:
    push %rbx
    mov $0x80000000, %eax
    cpuid
    cmp $0x8000001d, %eax
    jb cache_basic
    mov $0x80000001, %eax
    cpuid
    bt $22, %ecx
    jc cache_extended
cache_basic:
    xor %eax, %eax
    cpuid
    cmp $4, %eax
    jb cache_done
    mov $4, %r8d
    jmp cache_scan
cache_extended:
    mov $0x8000001d, %r8d
cache_scan:
    mov %r8d, 0xd0(%rbp)
    xor %r9d, %r9d
cache_next:
    mov %r8d, %eax
    mov %r9d, %ecx
    cpuid
    test $31, %al
    jz cache_done
    and $0xff, %eax
    sub $0x21, %eax
    cmp $2, %eax
    ja cache_skip
    mov %ebx, 0xd4(%rbp,%rax,8)
    mov %ecx, 0xd8(%rbp,%rax,8)
    bts %eax, 0xec(%rbp)
cache_skip:
    inc %r9d
    cmp $32, %r9d
    jb cache_next
cache_done:
    pop %rbx
    ret
