# Fixed PE32+ TLS directory. MSVC's generated TLS data sits between these markers.
.section .tls,"dw"
.p2align 3
.Ltemplate_begin:
    .quad 0

.section .tls$ZZZ,"dw"
.p2align 3
.globl tls_tail
tls_tail:
    .quad 0

.data
.p2align 2
.globl _tls_index
_tls_index:
    .long 0

.section .rdata,"dr"
.p2align 3
.globl _tls_used
_tls_used:
    .quad .Ltemplate_begin, tls_tail, _tls_index, 0
    .long 8, 0
