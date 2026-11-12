.text
.globl desktop_complete
.type desktop_complete,@function
desktop_complete:
    mov %rdi, %r15
    mov $0x40002000, %esp
    movabs $0x2133524553554d42, %rax
    push %rax
    mov $0x100000, %ebx
    mov (%rbx), %ecx
    ud2
.size desktop_complete, .-desktop_complete
.section .note.GNU-stack,"",@progbits
