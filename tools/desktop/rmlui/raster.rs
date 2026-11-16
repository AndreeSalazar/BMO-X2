//! HOST-only C ABI wrapper. The drawing implementation is safe no_std Ring 3 code.
#![no_std]
#[path="../../../userspace/services/desktop/src/rmlui.rs"]
mod raster;
use raster::{Vertex, Rect, Texture, Texels};

/// Caller owns non-overlapping, aligned buffers for the complete synchronous call.
/// No pointer is retained. A null texture is accepted only with zero dimensions/length.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn bmo_ui_triangle(pixels:*mut u32, length:usize, width:u32,height:u32,
    vertices:*const Vertex, texels:*const u8, texlen:usize, tw:u32,th:u32, clip:Rect)->u32 {
    unsafe { render(pixels,length,width,height,vertices,texels,texlen,tw,th,clip,false) }
}

#[unsafe(no_mangle)]
pub unsafe extern "C" fn bmo_ui_triangle_mask(pixels:*mut u32, length:usize, width:u32,height:u32,
    vertices:*const Vertex, texels:*const u8, texlen:usize, tw:u32,th:u32, clip:Rect)->u32 {
    unsafe { render(pixels,length,width,height,vertices,texels,texlen,tw,th,clip,true) }
}

unsafe fn render(pixels:*mut u32, length:usize, width:u32,height:u32,
    vertices:*const Vertex, texels:*const u8, texlen:usize, tw:u32,th:u32, clip:Rect, alpha_only:bool)->u32 {
    if pixels.is_null() || vertices.is_null() || length>4096*4096
        || (pixels as usize)%core::mem::align_of::<u32>()!=0
        || (vertices as usize)%core::mem::align_of::<Vertex>()!=0 { return 1; }
    let texture=if texels.is_null() {
        if texlen!=0 || tw!=0 || th!=0 {return 2;} None
    } else {
        if texlen>4096*4096*4 { return 2; }
        let bytes=unsafe{core::slice::from_raw_parts(texels,texlen)};
        Some(Texture{width:tw,height:th,texels:if alpha_only {Texels::Alpha(bytes)} else {Texels::Rgba(bytes)}})
    };
    let input=unsafe{[vertices.read(),vertices.add(1).read(),vertices.add(2).read()]};
    let output=unsafe{core::slice::from_raw_parts_mut(pixels,length)};
    match raster::triangle(output,width,height,input,texture,clip) {Ok(())=>0,Err(_)=>3}
}

#[panic_handler]
fn panic(_: &core::panic::PanicInfo<'_>)->! { unsafe{core::arch::asm!("ud2",options(noreturn))} }
