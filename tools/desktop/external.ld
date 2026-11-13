OUTPUT_FORMAT(elf64-x86-64)
ENTRY(_start)
PHDRS {
    text PT_LOAD FLAGS(5);
    rodata PT_LOAD FLAGS(4);
}
SECTIONS {
    . = 0x40000000;
    .text : { *(.text .text.*) } :text
    . = 0x40003000;
    .rodata : { *(.rodata .rodata.*) } :rodata
    .unexpected : { *(.data .data.* .bss .bss.* .eh_frame*) } :NONE
    ASSERT(SIZEOF(.text) <= 8192, "External session text exceeds two pages")
    ASSERT(SIZEOF(.rodata) <= 4096, "External session constants exceed one page")
    ASSERT(SIZEOF(.unexpected) == 0, "External session requires immutable regions")
}
