# Ring 0 platform probe. The reader copies this code as one relocatable span.
.Lgop_stage:
    .byte 0xe9
    .long gop_cursor_region - . - 4
    .byte 0xe9
    .long present_frame - . - 4

#include "gop_region.inc"
#define GOP_COPY_STAGED
#include "frame_copy.inc"
#undef GOP_COPY_STAGED
.Lgop_stage_end:
