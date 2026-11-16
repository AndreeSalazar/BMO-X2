#pragma once
#include <cstddef>
#include <cstdint>
struct BmoUiVertex { float x,y,r,g,b,a,u,v; };
struct BmoUiRect { uint32_t left,top,right,bottom; };
static_assert(sizeof(BmoUiVertex)==32 && sizeof(BmoUiRect)==16);
// Trusted application buffers, owned by caller, borrowed only for this call.
extern "C" uint32_t bmo_ui_triangle(uint32_t*,size_t,uint32_t,uint32_t,
    const BmoUiVertex*,const uint8_t*,size_t,uint32_t,uint32_t,BmoUiRect);
extern "C" uint32_t bmo_ui_triangle_mask(uint32_t*,size_t,uint32_t,uint32_t,
    const BmoUiVertex*,const uint8_t*,size_t,uint32_t,uint32_t,BmoUiRect);
