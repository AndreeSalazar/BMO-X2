#![no_std]
#![no_main]

use core::arch::asm;
use core::panic::PanicInfo;

const ACCENTS: [u32; 4] = [0x5ad8ff, 0xad92ff, 0x6ee7b7, 0xff7c98];
const DIGITS: [u16; 4] = [0x749a, 0x73e7, 0x79e7, 0x49ed];

fn invoke(operation: u64, rect: u64, color: u32) -> u32 {
    let reply: u64;
    unsafe {
        asm!("syscall", inlateout("rax") 0u64 => reply,
             inlateout("rdi") 1u64 => _, inlateout("rsi") operation => _,
             inlateout("rdx") rect => _, inlateout("r10") u64::from(color) => _,
             lateout("rcx") _, lateout("r11") _, lateout("r8") _, lateout("r9") _);
    }
    reply as u32
}

fn fill(x: u64, y: u64, w: u64, h: u64, color: u32) {
    invoke(1, x | y << 16 | w << 32 | h << 48, color);
}

fn digit(x: u64, y: u64, index: usize, color: u32) {
    let pattern = DIGITS[index];
    for bit in 0..15 {
        if pattern & (1 << bit) != 0 {
            fill(x + bit % 3 * 3, y + bit / 3 * 3, 3, 3, color);
        }
    }
}

fn paint(space: usize, focus: usize) {
    let accent = ACCENTS[space];
    fill(0, 0, 640, 400, 0x0d0e17);
    fill(0, 0, 640, 44, 0x161722);
    for i in 0..4 {
        let x = 216 + i as u64 * 56;
        let color = if i == space { accent } else { 0x5d647b };
        digit(x + 12, 10, i, color);
        fill(x, 33, 32, 3, color);
    }
    for (i, x, y, w, h) in [(0, 52, 99, 315, 191), (1, 390, 147, 198, 151)] {
        let border = if i == focus { accent } else { 0x40465d };
        fill(x, y, w, h, border);
        fill(x + 2, y + 2, w - 4, h - 4, 0x171825);
        fill(x + 2, y + 2, w - 4, 28, 0x232638);
        digit(x + 14, y + 9, i, border);
        for line in 0..3 {
            fill(x + 20, y + 58 + line * 17, w - 65 - line * 17, 2, 0x353c53);
        }
    }
}

#[unsafe(no_mangle)]
extern "C" fn bmo_main() -> ! {
    let mut space = 0;
    let mut focus = [0; 4];
    let mut prefix = false;
    let mut ctrl = false;
    let mut super_key = false;
    paint(space, focus[space]);
    loop {
        let raw = invoke(2, 0, 0);
        if raw >= 256 {
            for _ in 0..128 {
                core::hint::spin_loop();
            }
            continue;
        }
        let key = raw as u8;
        if key == 0xe0 {
            prefix = true;
            continue;
        }
        let extended = core::mem::replace(&mut prefix, false);
        let down = key & 0x80 == 0;
        match key & 0x7f {
            0x1d => ctrl = down,
            0x5b | 0x5c if extended => super_key = down,
            2..=5 if down && !extended && (!super_key || ctrl) => {
                let selected = usize::from(key - 2);
                if selected != space {
                    space = selected;
                    paint(space, focus[space]);
                }
            }
            2..=3 if down && super_key && !extended => {
                let selected = usize::from(key - 2);
                if selected != focus[space] {
                    focus[space] = selected;
                    paint(space, selected);
                }
            }
            _ => {}
        }
    }
}

#[panic_handler]
fn panic(_: &PanicInfo<'_>) -> ! {
    unsafe { asm!("ud2", options(noreturn)) }
}
