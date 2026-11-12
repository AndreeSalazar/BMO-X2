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
}

fn check_desktop() -> bool {
    let red = Surface::new(1, 1, &[0x00ff0000]).unwrap();
    let blue = Surface::new(1, 1, &[0x000000ff]).unwrap();
    let mut desktop = Desktop::<2>::new();
    let mut keyboard = Keyboard::default();
    desktop.open(1, 0, 0, red).unwrap();
    if keyboard.handle(&mut desktop, 0x303, 0x22) != Ok(Some(KeyRoute::Consumed)) {
        return false;
    }
    desktop.open(2, 0, 0, blue).unwrap();
    let mut pixels = [0; 2];
    desktop.compose(&mut Frame::new(2, 1, &mut pixels).unwrap(), 0);
    if pixels != [0x000000ff, 0] || desktop.focused() != Some(2) {
        return false;
    }
    if keyboard.handle(&mut desktop, 0x302, 0x22) != Ok(Some(KeyRoute::Consumed)) {
        return false;
    }
    desktop.compose(&mut Frame::new(2, 1, &mut pixels).unwrap(), 0);
    pixels == [0x00ff0000, 0] && desktop.focused() == Some(1)
}

#[unsafe(no_mangle)]
extern "C" fn bmo_main() {
    let value = if check_desktop() { 0x324f4d42 } else { 0 };
    // The ABI test grants capability 1 for ECHO. All arguments are scalars.
    let result = unsafe { bmo_invoke(1, 1, value, 0, 0) };
    if value == 0 || result.status != 0 || result.value != value {
        panic!("desktop probe failed");
    }
    // The startup stub traps on return until the process exit ABI exists.
}

#[panic_handler]
fn panic(_info: &PanicInfo<'_>) -> ! {
    unsafe { core::arch::asm!("int3", options(noreturn, nostack)) }
}
