#![no_std]
#![no_main]

use core::{hint::black_box, panic::PanicInfo};

struct Window(u8);
impl Window {
    fn show(&mut self) -> u8 {
        let old = black_box(self.0);
        self.0 = 1;
        old
    }
}

struct Button(u8);
impl Button {
    fn activate(&mut self) -> u8 {
        let old = black_box(self.0);
        self.0 = 1;
        old
    }
}

#[no_mangle]
pub extern "C" fn _start() -> ! {
    let mut panel = Window(0);
    let mut enter = Button(0);
    black_box((panel.show(), enter.activate(), panel.show()));
    loop {
        core::hint::spin_loop();
    }
}

#[panic_handler]
fn panic(_: &PanicInfo) -> ! {
    loop {
        core::hint::spin_loop();
    }
}
