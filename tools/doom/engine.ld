OUTPUT_FORMAT(elf64-x86-64)
ENTRY(_start)

PHDRS {
    text PT_LOAD FLAGS(5);
    rodata PT_LOAD FLAGS(4);
    data PT_LOAD FLAGS(6);
}
SECTIONS {
    .text 0x40000000 : { *(.text .text.*) } :text
    .rodata 0x40200000 : { *(.rodata .rodata.*) } :rodata
    .data 0x40400000 : { *(.data .data.*) } :data
    .bss : ALIGN(16) { *(.bss .bss.*) *(COMMON) } :data
    ASSERT(. <= 0x40e00000, "Doom arena overlaps the stack")
}
