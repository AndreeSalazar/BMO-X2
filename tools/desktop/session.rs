#![no_std]
#![no_main]

use core::arch::asm;
use core::panic::PanicInfo;

const ACCENTS: [u32; 4] = [0x5ad8ff, 0xad92ff, 0x6ee7b7, 0xff7c98];
const DIGITS: [u16; 4] = [0x749a, 0x73e7, 0x79e7, 0x49ed];
const DISPLAY: u64 = 1;
const INPUT: u64 = 2;
const FILL: u64 = 1;
const READ_INPUT: u64 = 2;
const DENIED: u32 = 257;

fn invoke(capability: u64, operation: u64, rect: u64, color: u32) -> u32 {
    let reply: u64;
    unsafe {
        asm!("syscall", inlateout("rax") 0u64 => reply,
             inlateout("rdi") capability => _, inlateout("rsi") operation => _,
             inlateout("rdx") rect => _, inlateout("r10") u64::from(color) => _,
             lateout("rcx") _, lateout("r11") _, lateout("r8") _, lateout("r9") _);
    }
    reply as u32
}

fn fill(x: u64, y: u64, w: u64, h: u64, color: u32) {
    invoke(DISPLAY, FILL, x | y << 16 | w << 32 | h << 48, color);
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

fn cursor(x: i16, y: i16) {
    fill(x as u64, y as u64, 3, 10, 0xe7efff);
    fill(x as u64, y as u64, 7, 3, 0xe7efff);
}

fn window_at(x: i16, y: i16) -> Option<usize> {
    if (52..367).contains(&x) && (99..290).contains(&y) {
        Some(0)
    } else if (390..588).contains(&x) && (147..298).contains(&y) {
        Some(1)
    } else {
        None
    }
}

#[unsafe(no_mangle)]
extern "C" fn bmo_main() -> ! {
    let mut space = 0;
    let mut focus = [0; 4];
    let mut prefix = false;
    let mut ctrl = false;
    let mut super_key = false;
    let (mut x, mut y) = (320i16, 200i16);
    let (mut flags, mut dx, mut index) = (0u8, 0u8, 0u8);
    let mut left = false;
    let pixel = (1u64 << 32) | (1u64 << 48);
    if invoke(INPUT, FILL, pixel, 0xffffff) != DENIED
        || invoke(DISPLAY, READ_INPUT, 0, 0) != DENIED
        || invoke(0, FILL, pixel, 0xffffff) != DENIED
        || invoke(INPUT, 3, 0, 0) != DENIED
    {
        panic!("session permissions");
    }
    paint(space, focus[space]);
    cursor(x, y);
    loop {
        let raw = invoke(INPUT, READ_INPUT, 0, 0);
        if raw & 512 != 0 {
            let byte = raw as u8;
            match index {
                0 if byte & 8 != 0 && byte != 0xfa => {
                    flags = byte;
                    index = 1;
                }
                1 => {
                    dx = byte;
                    index = 2;
                }
                2 => {
                    index = 0;
                    if flags & 0xc0 != 0 {
                        continue;
                    }
                    let delta_x = i16::from(dx) - i16::from(flags & 0x10) * 16;
                    let delta_y = i16::from(byte) - i16::from(flags & 0x20) * 8;
                    let next_x = (x + delta_x).clamp(0, 633);
                    let next_y = (y - delta_y).clamp(0, 390);
                    let pressed = flags & 1 != 0;
                    let previous_focus = focus[space];
                    if pressed && !left {
                        if let Some(window) = window_at(next_x, next_y) {
                            focus[space] = window;
                        }
                    }
                    left = pressed;
                    if (next_x, next_y, focus[space]) != (x, y, previous_focus) {
                        x = next_x;
                        y = next_y;
                        paint(space, focus[space]);
                        cursor(x, y);
                    }
                }
                _ => {}
            }
            continue;
        }
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
                    cursor(x, y);
                }
            }
            2..=3 if down && super_key && !extended => {
                let selected = usize::from(key - 2);
                if selected != focus[space] {
                    focus[space] = selected;
                    paint(space, selected);
                    cursor(x, y);
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
