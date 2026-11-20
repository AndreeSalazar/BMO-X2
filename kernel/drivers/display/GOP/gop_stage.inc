# Ring 0 platform probe. The reader copies this code as one relocatable span.
.Lgop_stage:
#ifdef BMO_AMDVI_POST
gop_stage_begin:
#endif
    .byte 0xe9
    .long gop_cursor_region - . - 4
    .byte 0xe9
    .long present_frame - . - 4

#include "gop_region.inc"
#define GOP_COPY_STAGED
#include "frame_copy.inc"
#undef GOP_COPY_STAGED
#ifdef BMO_FULL_HD
#include "full_hd.inc"
#endif
.Lgop_stage_end:
#ifdef BMO_AMDVI_POST
gop_stage_end:
#endif
