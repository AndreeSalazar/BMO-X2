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

fn check_desktop() -> Option<u64> {
    let red = Surface::new(1, 1, &[0x00ff5c82]).unwrap();
    let blue = Surface::new(1, 1, &[0x005ad8ff]).unwrap();
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
