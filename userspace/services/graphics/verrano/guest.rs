#![no_std]
#![no_main]

use bmo_bsf::What;
use bmo_x2_verrano::{Buffer, Draw, Limits, Texture, TextureBinding, submit_textured};
use core::{arch::asm, hint::black_box, num::NonZeroU64};
use core::sync::atomic::{AtomicU32, Ordering::Relaxed};

mod bsf;

static PRESENTED_TEXTURES: AtomicU32 = AtomicU32::new(0);

fn fill(x: u64, y: u64, width: u64, height: u64, color: u32) {
    unsafe {
        asm!("syscall", inlateout("rax") 0u64 => _, inlateout("rdi") 1u64 => _,
             inlateout("rsi") 1u64 => _, inlateout("rdx") (x | y << 16 | width << 32 | height << 48) => _,
             inlateout("r10") u64::from(color) => _, lateout("rcx") _, lateout("r11") _,
             lateout("r8") _, lateout("r9") _);
    }
}

#[unsafe(no_mangle)]
extern "C" fn bmo_main() -> ! {
    let package = black_box(include_bytes!(env!("VERRANO_BSF")).as_slice());
    fill(0, 0, 640, 400, 0x0b1019);
    match bsf::load(package) {
        Ok([vertex, fragment]) => {
            // Consume both verified modules before admitting either texture.
            black_box((vertex, fragment));
            let buffers = [Buffer { owner: 1, bytes: 48 }];
            let draws = [Draw { buffer: 0, offset: 0, stride: 16, vertices: 3 }];
            let colors = [0x00ff5c82, 0x005ad8ff];
            let textures = [1u64, 2].map(|handle| Some(Texture {
                owner: 1, generation: 7, resident: NonZeroU64::new(handle),
            }));
            for slot in 0..2 {
                // The software reference consumes the admitted handle and presents its texel.
                let binding = black_box(TextureBinding { slot, generation: 7 });
                submit_textured(1, &buffers, &draws, Limits { draws: 1, vertices: 3 },
                                &textures, binding, |_, _, handle| {
                    fill(256 + slot as u64 * 64, 120, 64, 128, colors[handle.get() as usize - 1]);
                    PRESENTED_TEXTURES.fetch_or(1 << slot, Relaxed);
                }).unwrap_or_else(|_| trap());
            }
            if PRESENTED_TEXTURES.load(Relaxed) != 3 {
                trap();
            }
        }
        Err(bsf::Rejection::Container(error)) if error.what == What::SpirvHash => {
            if PRESENTED_TEXTURES.load(Relaxed) != 0 {
                trap();
            }
            fill(256, 120, 128, 128, 0x00ba382e);
        }
        Err(_) => trap(),
    }
    fill(240, 104, 8, 8, 0x7de3d2);
    loop { unsafe { asm!("pause") } }
}

fn trap() -> ! {
    unsafe { asm!("ud2", options(noreturn)) }
}

#[panic_handler]
fn panic(_: &core::panic::PanicInfo<'_>) -> ! {
    trap()
}
