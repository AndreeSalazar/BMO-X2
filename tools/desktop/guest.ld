OUTPUT_FORMAT(elf64-x86-64)
ENTRY(_start)
PHDRS { probe PT_LOAD FLAGS(5); }
SECTIONS {
    . = 0x40000000;
    .text : { *(.text .text.*) *(.rodata .rodata.*) } :probe
    .unexpected : { *(.data .data.* .bss .bss.* .eh_frame*) } :NONE
    ASSERT(SIZEOF(.unexpected) == 0, "Desktop probe requires one immutable page")
}
