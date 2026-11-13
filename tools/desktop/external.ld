OUTPUT_FORMAT(elf64-x86-64)
ENTRY(_start)
PHDRS {
    text PT_LOAD FLAGS(5);
    rodata PT_LOAD FLAGS(4);
    data PT_LOAD FLAGS(6);
}
SECTIONS {
    . = 0x40000000;
    .text : { *(.text .text.*) } :text
    . = 0x40003000;
    .rodata : { *(.rodata .rodata.*) } :rodata
    . = 0x40004000;
    .data : { *(.data .data.*) } :data
    .bss : { *(.bss .bss.*) *(COMMON) } :data
    .unexpected : { *(.eh_frame*) } :NONE
    ASSERT(SIZEOF(.text) <= 8192, "External session text exceeds two pages")
    ASSERT(SIZEOF(.rodata) <= 4096, "External session constants exceed one page")
    ASSERT(. <= 0x40005000, "External session data and BSS exceed one page")
    ASSERT(SIZEOF(.unexpected) == 0, "External session excludes unwinding")
}
