OUTPUT_FORMAT(elf64-x86-64)
ENTRY(_start)
PHDRS { text PT_LOAD FLAGS(5); rodata PT_LOAD FLAGS(4); }
SECTIONS {
    . = 0x40000000;
    .text : { *(.text .text.*) } :text
    . = 0x40003000;
    .rodata : { *(.rodata .rodata.*) *(.got .got.*) } :rodata
    .unexpected : { *(.data .data.* .bss .bss.*) *(COMMON) *(.eh_frame*) } :NONE
    ASSERT(SIZEOF(.text) <= 8192, "Raster probe text exceeds two pages")
    ASSERT(SIZEOF(.rodata) <= 4096, "Raster probe constants exceed one page")
    ASSERT(SIZEOF(.unexpected) == 0, "Raster probe has no mutable globals or unwinding")
}
