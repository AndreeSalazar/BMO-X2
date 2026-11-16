#pragma once
#include <stddef.h>
#include <stdint.h>
#ifdef _WIN32
#define BMO_UI_API extern "C" __declspec(dllexport)
#else
#define BMO_UI_API extern "C"
#endif
// Single UI thread, one live engine. Caller buffers are valid and immutable
// until close; frame target is exclusive and borrowed only during frame().
struct BmoUiBlob { const char* name; const uint8_t* data; size_t length; };
struct BmoUiStats {
    uint64_t time_ns, triangles, geometry_bytes, texture_bytes;
    uint64_t peak_geometry_bytes, peak_texture_bytes, open_files, denied_files;
    uint64_t click_events, action_accepted;
};
struct BmoUiOptimizationStats {
    uint64_t texture_rgba_equivalent_bytes, peak_texture_rgba_equivalent_bytes;
    uint64_t alpha_textures, rgba_textures, frames_rendered, frames_skipped;
};
static_assert(sizeof(size_t)==8 && sizeof(BmoUiBlob)==24 && sizeof(BmoUiStats)==80 && sizeof(BmoUiOptimizationStats)==48,
              "bmo-ui-memory-v1 requires the x86-64 profile");
using BmoUiAction = int(*)();
enum BmoUiStatus { UiOk=0, UiState=1, UiArgument=2, UiResources=3, UiEngine=4, UiTime=5 };
BMO_UI_API int bmo_ui_open(const BmoUiBlob*, size_t count, BmoUiAction);
BMO_UI_API int bmo_ui_frame(uint64_t monotonic_ns, uint32_t* xrgb, size_t pixel_count);
// preserved=1 promises the target still contains the last successful frame.
// No frame is cached/copied inside the engine. rendered=0 means target untouched.
BMO_UI_API int bmo_ui_frame_if_due(uint64_t monotonic_ns,uint32_t* xrgb,size_t count,
                                 uint32_t preserved,uint32_t* rendered);
// 0 move; 1 left down; 2 left up; 3 Enter down; 4 Enter up. DIRECTOR owns global shortcuts.
BMO_UI_API int bmo_ui_input(uint32_t kind, int32_t x, int32_t y);
BMO_UI_API int bmo_ui_box(const char* id, float* xywh);
BMO_UI_API int bmo_ui_motion(uint32_t enabled);
BMO_UI_API int bmo_ui_next_delay_ms(uint32_t* delay); // UINT32_MAX means no requested update.
BMO_UI_API int bmo_ui_stats(BmoUiStats*);
BMO_UI_API int bmo_ui_optimization_stats(BmoUiOptimizationStats*);
BMO_UI_API int bmo_ui_close();
BMO_UI_API const char* bmo_ui_error();
