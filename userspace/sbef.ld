OUTPUT_FORMAT(elf64-x86-64)
ENTRY(_start)

PHDRS {
    text PT_LOAD FLAGS(5);
    rodata PT_LOAD FLAGS(4);
    data PT_LOAD FLAGS(6);
}

SECTIONS {
    . = 0x40000000;
    .text : ALIGN(4096) { *(.text .text.*) } :text
    .rodata : ALIGN(4096) { *(.rodata .rodata.*) } :rodata
    .data : ALIGN(4096) { *(.data .data.*) } :data
    .bss : { *(.bss .bss.*) *(COMMON) } :data
    .unsupported : {
        *(.preinit_array* .init_array* .fini_array* .ctors* .dtors*)
        *(.tdata* .tbss* .eh_frame* .gcc_except_table*)
    } :NONE
    ASSERT(SIZEOF(.unsupported) == 0, "SBEF ABI 0 requires explicit startup and has no TLS or unwinding")
}
