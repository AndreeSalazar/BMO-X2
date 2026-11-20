#ifndef BMO_GOP_LAYOUT_INC
#define BMO_GOP_LAYOUT_INC

#if !defined(RMLUI_MEDIA) || !defined(RMLUI_NATIVE)
#error GOP region code requires the native FAT32 desktop profile
#endif

// The CASM fixture clears [0x13000, 0x1b000) and uses 0x1b000 as
// the top of its downward-growing Ring 0 stack. The large SBEF
// profile also puts its user stack outside this context.
// The small SBEF profile uses this page for its user stack.
#define GOP_CODE_OFFSET 0x1b000
#define GOP_REGION_ENTRY GOP_CODE_OFFSET
#define GOP_FRAME_ENTRY (GOP_CODE_OFFSET + 5)

#endif
