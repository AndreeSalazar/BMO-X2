OUTPUT_FORMAT(elf64-x86-64)
ENTRY(_start)
PHDRS { text PT_LOAD FLAGS(5); rodata PT_LOAD FLAGS(4); data PT_LOAD FLAGS(6); }
SECTIONS {
    .text 0x40000000 : {
        *(.text.startup) *(.text .text.*)
        __start___lcxx_override = .; KEEP(*(__lcxx_override)) __stop___lcxx_override = .;
    } :text
    ASSERT(. <= 0x40200000, "UI code exceeds RX range")
    .rodata 0x40200000 : {
        *(.rodata .rodata.*)
        . = ALIGN(8); __init_array_start = .;
        KEEP(*(SORT_BY_INIT_PRIORITY(.init_array.*))) KEEP(*(.init_array))
        __init_array_end = .;
    } :rodata
    ASSERT(. <= 0x40400000, "UI resources exceed R range")
    .data 0x40400000 : { *(.data .data.*) *(.got .got.*) } :data
    .bss : ALIGN(64) { *(.bss .bss.*) *(COMMON) } :data
    PROVIDE(bmo_ui_data_end = 0x40e00000);
    ASSERT(. <= bmo_ui_data_end, "UI heap/framebuffer overlaps stack")
    /DISCARD/ : { *(.eh_frame*) *(.comment) *(.note*) }
}
