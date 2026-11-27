#![no_std]
#![no_main]

use bmo_x2_desktop::{Desktop, Frame, KeyRoute, Keyboard, Surface};
use core::panic::PanicInfo;

#[repr(C)]
struct AbiResult {
    status: i64,
    value: u64,
}

unsafe extern "C" {
    fn bmo_invoke(capability: u64, operation: u64, arg0: u64, arg1: u64, arg2: u64) -> AbiResult;
    #[cfg(qemu_desktop)]
    fn bmo_wait(capability: u64, sequence: u64, deadline: u64) -> AbiResult;
    #[cfg(qemu_desktop)]
    fn desktop_complete(pixels: u64) -> !;
}

#[cfg(verrano_probe)]
fn desktop_colors() -> Option<[u32; 2]> {
    use bmo_x2_verrano::{Buffer, Draw, Limits, Rejection, Texture, TextureBinding, submit_textured};
    use core::{hint::black_box, num::NonZeroU64};

    let textures = [
        Some(Texture { owner: 1, generation: 7, resident: NonZeroU64::new(1) }),
        Some(Texture { owner: 1, generation: 7, resident: NonZeroU64::new(2) }),
        Some(Texture { owner: 2, generation: 7, resident: NonZeroU64::new(3) }),
        Some(Texture { owner: 1, generation: 7, resident: None }),
    ];
    let buffers = [Buffer { owner: 1, bytes: 48 }];
    let draws = [Draw { buffer: 0, offset: 0, stride: 16, vertices: 3 }];
    let submit = |slot, generation| {
        let binding = black_box(TextureBinding { slot, generation });
        submit_textured(1, &buffers, &draws, Limits { draws: 1, vertices: 3 },
                        &textures, binding, |_, _, handle| {
            // Software reference backend with two resident one-texel resources.
            let colors = [0x00ff5c82, 0x005ad8ff];
            colors.get(handle.get() as usize - 1).copied().unwrap_or(0)
        })
    };
    let red = submit(0, 7).ok()?;
    if submit(0, 6) != Err(Rejection::TextureGeneration)
        || submit(2, 7) != Err(Rejection::TextureOwner)
        || submit(3, 7) != Err(Rejection::TextureNotResident)
        || submit(4, 7) != Err(Rejection::TextureSlot)
    {
        return None;
    }
    Some([red, submit(1, 7).ok()?])
}

#[cfg(not(verrano_probe))]
fn desktop_colors() -> Option<[u32; 2]> {
    Some([0x00ff5c82, 0x005ad8ff])
}

fn check_desktop() -> Option<u64> {
    let [red, blue] = desktop_colors()?;
    let red_pixel = [red];
    let blue_pixel = [blue];
    let red = Surface::new(1, 1, &red_pixel).unwrap();
    let blue = Surface::new(1, 1, &blue_pixel).unwrap();
    let mut desktop = Desktop::<2>::new();
    let mut keyboard = Keyboard::default();
    desktop.open(1, 0, 0, red).unwrap();
    if keyboard.handle(&mut desktop, 0x303, 0x22) != Ok(Some(KeyRoute::Consumed)) {
        return None;
    }
    desktop.open(2, 0, 0, blue).unwrap();
    let mut pixels = [0; 2];
    desktop.compose(&mut Frame::new(2, 1, &mut pixels).unwrap(), 0);
    if pixels != [0x005ad8ff, 0] || desktop.focused() != Some(2) {
        return None;
    }
    let right = pixels[0];
    if keyboard.handle(&mut desktop, 0x302, 0x22) != Ok(Some(KeyRoute::Consumed)) {
        return None;
    }
    desktop.compose(&mut Frame::new(2, 1, &mut pixels).unwrap(), 0);
    (pixels == [0x00ff5c82, 0] && desktop.focused() == Some(1))
        .then_some(u64::from(pixels[0]) | (u64::from(right) << 32))
}

#[unsafe(no_mangle)]
extern "C" fn bmo_main() {
    let value = check_desktop().unwrap_or(0);
    // The ABI test grants capability 1 for ECHO. All arguments are scalars.
    let result = unsafe { bmo_invoke(1, 1, value, 0, 0) };
    if value == 0 || result.status != 0 || result.value != value {
        panic!("desktop probe failed");
    }
    #[cfg(qemu_desktop)]
    unsafe {
        let denied = bmo_invoke(0, 1, 0, 0, 0);
        let wait = bmo_wait(1, 0, 0);
        if denied.status != -2 || denied.value != 0 || wait.status != -4 || wait.value != 0 {
            panic!("desktop ABI failed");
        }
        desktop_complete(result.value);
    }
}

#[panic_handler]
fn panic(_info: &PanicInfo<'_>) -> ! {
    unsafe { core::arch::asm!("int3", options(noreturn, nostack)) }
}
