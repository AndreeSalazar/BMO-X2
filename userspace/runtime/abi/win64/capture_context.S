# Save the caller's Win64 CONTEXT without changing its live register state.
.text
.globl bmo_rtl_capture_context
bmo_rtl_capture_context:
    movq %rax, 120(%rcx)
    movq %rcx, 128(%rcx)
    movq %rdx, 136(%rcx)
    movq %rbx, 144(%rcx)
    leaq 8(%rsp), %rax
    movq %rax, 152(%rcx)
    movq %rbp, 160(%rcx)
    movq %rsi, 168(%rcx)
    movq %rdi, 176(%rcx)
    movq %r8, 184(%rcx)
    movq %r9, 192(%rcx)
    movq %r10, 200(%rcx)
    movq %r11, 208(%rcx)
    movq %r12, 216(%rcx)
    movq %r13, 224(%rcx)
    movq %r14, 232(%rcx)
    movq %r15, 240(%rcx)
    movq (%rsp), %rax
    movq %rax, 248(%rcx)
    pushfq
    popq %rax
    movl %eax, 68(%rcx)
    movl $0x10000f, 48(%rcx)  # AMD64 control, integer, segment and floating point state.
    stmxcsr 52(%rcx)
    movw %cs, 56(%rcx)
    movw %ds, 58(%rcx)
    movw %es, 60(%rcx)
    movw %fs, 62(%rcx)
    movw %gs, 64(%rcx)
    movw %ss, 66(%rcx)
    fxsave64 256(%rcx)
    movq 120(%rcx), %rax
    ret
