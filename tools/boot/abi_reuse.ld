OUTPUT_FORMAT(elf64-x86-64)
ENTRY(_start)
PHDRS { probe PT_LOAD FLAGS(5); }
SECTIONS {
    .text 0x40000000 : { *(.text .text.*) *(.rodata .rodata.*) } :probe
    .abi_complete 0x40000100 : { KEEP(*(.abi_complete)) } :probe
    .unexpected : { *(.data .data.* .bss .bss.* .eh_frame*) } :NONE
    ASSERT(SIZEOF(.unexpected) == 0, "ABI reuse requires one immutable page")
}
