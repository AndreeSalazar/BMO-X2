#![no_std]
#![no_main]
#[path="../../../userspace/services/desktop/src/rmlui.rs"] mod raster;
mod probe_scene;
use core::arch::asm;
fn fill(x:u64,y:u64,w:u64,h:u64,color:u32) {
    unsafe {asm!("syscall",inlateout("rax") 0u64=>_,inlateout("rdi") 1u64=>_,
        inlateout("rsi") 1u64=>_,inlateout("rdx") (x|y<<16|w<<32|h<<48)=>_,
        inlateout("r10") u64::from(color)=>_,lateout("rcx") _,lateout("r11") _,lateout("r8") _,lateout("r9") _);}
}
#[unsafe(no_mangle)]
extern "C" fn bmo_main()->! {
    let pixels=probe_scene::scene();
    fill(0,0,640,400,0x0b1019);
    for y in 0..16 { for x in 0..16 { fill(256+x*8,120+y*8,8,8,pixels[(y*16+x) as usize]); }}
    fill(240,104,8,8,0x7de3d2); // Completion marker after all borrowed pixels were presented.
    loop { unsafe {asm!("pause");} } // Bounded QEMU capture fixture, not the desktop event loop.
}
#[panic_handler]
fn panic(_: &core::panic::PanicInfo<'_>)->! { unsafe{asm!("ud2",options(noreturn))} }
