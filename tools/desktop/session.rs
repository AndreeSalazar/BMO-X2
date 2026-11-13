#![no_std]
#![no_main]

use core::arch::asm;
use core::panic::PanicInfo;

mod cabina;

#[cfg(external_session)]
use core::sync::atomic::{AtomicU32, Ordering::Relaxed};
#[cfg(external_session)]
static DATA_COOKIE: AtomicU32 = AtomicU32::new(0x424d4f32);
#[cfg(external_session)]
static BSS_COOKIE: AtomicU32 = AtomicU32::new(0);

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

fn wait_input(ticks: u64) -> u32 {
    let reply: u64;
    unsafe {
        asm!("syscall", inlateout("rax") 1u64 => reply,
             inlateout("rdi") INPUT => _, inlateout("rsi") 0u64 => _,
             inlateout("rdx") ticks => _, lateout("rcx") _, lateout("r11") _,
             lateout("r8") _, lateout("r9") _, lateout("r10") _);
    }
    reply as u32
}

#[derive(Clone, Copy)]
struct Clip {
    left: u64,
    top: u64,
    right: u64,
    bottom: u64,
}

impl Clip {
    fn intersect(self, other: Self) -> Self {
        Self {
            left: self.left.max(other.left),
            top: self.top.max(other.top),
            right: self.right.min(other.right),
            bottom: self.bottom.min(other.bottom),
        }
    }

    fn fill(self, x: u64, y: u64, w: u64, h: u64, color: u32) {
        let left = x.max(self.left);
        let top = y.max(self.top);
        let right = (x + w).min(self.right);
        let bottom = (y + h).min(self.bottom);
        if left < right && top < bottom {
            fill(left, top, right - left, bottom - top, color);
        }
    }
}

const VIEWPORT: Clip = Clip {
    left: 0,
    top: 0,
    right: 640,
    bottom: 400,
};

fn digit(clip: Clip, x: u64, y: u64, index: usize, color: u32) {
    let pattern = DIGITS[index];
    for bit in 0..15 {
        if pattern & (1 << bit) != 0 {
            clip.fill(x + bit % 3 * 3, y + bit / 3 * 3, 3, 3, color);
        }
    }
}

fn paint(clip: Clip, space: usize, focus: usize) {
    if clip.left >= clip.right || clip.top >= clip.bottom {
        return;
    }
    let accent = ACCENTS[space];
    clip.fill(0, 0, 640, 400, 0x0d0e17);
    clip.fill(0, 0, 640, 44, 0x161722);
    for i in 0..4 {
        let x = 216 + i as u64 * 56;
        let color = if i == space { accent } else { 0x5d647b };
        digit(clip, x + 12, 10, i, color);
        clip.fill(x, 33, 32, 3, color);
    }
    for (i, x, y, w, h) in [(0, 52, 99, 315, 191), (1, 390, 147, 198, 151)] {
        let border = if i == focus { accent } else { 0x40465d };
        clip.fill(x, y, w, h, border);
        clip.fill(x + 2, y + 2, w - 4, h - 4, 0x171825);
        clip.fill(x + 2, y + 2, w - 4, 28, 0x232638);
        digit(clip, x + 14, y + 9, i, border);
        for line in 0..3 {
            clip.fill(x + 20, y + 58 + line * 17, w - 65 - line * 17, 2, 0x353c53);
        }
    }
}

fn cursor(x: i16, y: i16) {
    fill(x as u64, y as u64, 3, 10, 0xe7efff);
    fill(x as u64, y as u64, 7, 3, 0xe7efff);
}

fn move_cursor(old: (i16, i16), new: (i16, i16), space: usize, focus: usize) {
    if old == new {
        return;
    }
    let (x, y) = (new.0 as u64, new.1 as u64);
    let (old_x, old_y) = (old.0 as u64, old.1 as u64);
    let old = Clip {
        left: old_x,
        top: old_y,
        right: old_x + 7,
        bottom: old_y + 10,
    };
    // Publish the new cursor first. Restore only the old area outside its L.
    cursor(new.0, new.1);
    for exposed in [
        Clip {
            bottom: y,
            ..VIEWPORT
        },
        Clip {
            top: y + 10,
            ..VIEWPORT
        },
        Clip {
            top: y,
            bottom: y + 10,
            right: x,
            ..VIEWPORT
        },
        Clip {
            top: y,
            bottom: y + 10,
            left: x + 7,
            ..VIEWPORT
        },
        Clip {
            left: x + 3,
            top: y + 3,
            right: x + 7,
            bottom: y + 10,
        },
    ] {
        paint(old.intersect(exposed), space, focus);
    }
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
    #[cfg(external_session)]
    {
        if DATA_COOKIE.load(Relaxed) != 0x424d4f32 || BSS_COOKIE.load(Relaxed) != 0 {
            panic!("session data");
        }
        DATA_COOKIE.store(0x52334441, Relaxed);
        BSS_COOKIE.store(0x52334253, Relaxed);
    }
    let mut space = 0;
    let mut focus = [0; 4];
    let mut prefix = false;
    let mut ctrl = false;
    let mut super_key = false;
    let (mut x, mut y) = (320i16, 200i16);
    let mut displayed = (x, y);
    let mut pending_motion = 0;
    let (mut flags, mut dx, mut index) = (0u8, 0u8, 0u8);
    let mut left = false;
    let mut console = false;
    let mut f2_down = false;
    let pixel = (1u64 << 32) | (1u64 << 48);
    if invoke(INPUT, FILL, pixel, 0xffffff) != DENIED
        || invoke(DISPLAY, READ_INPUT, 0, 0) != DENIED
        || invoke(0, FILL, pixel, 0xffffff) != DENIED
        || invoke(INPUT, 3, 0, 0) != DENIED
        || invoke(3, FILL, pixel, 0xffffff) != DENIED
        || invoke(3, 3, 3, 0) != DENIED
    {
        panic!("session permissions");
    }
    paint(VIEWPORT, space, focus[space]);
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
                    if console {
                        left = pressed;
                        continue;
                    }
                    let previous_focus = focus[space];
                    if pressed && !left {
                        if let Some(window) = window_at(next_x, next_y) {
                            focus[space] = window;
                        }
                    }
                    left = pressed;
                    x = next_x;
                    y = next_y;
                    if focus[space] != previous_focus {
                        paint(VIEWPORT, space, focus[space]);
                        cursor(x, y);
                        displayed = (x, y);
                        pending_motion = 0;
                    } else {
                        pending_motion += 1;
                        if pending_motion == 8 {
                            move_cursor(displayed, (x, y), space, focus[space]);
                            displayed = (x, y);
                            pending_motion = 0;
                        }
                    }
                }
                _ => {}
            }
            continue;
        }
        if pending_motion != 0 {
            move_cursor(displayed, (x, y), space, focus[space]);
            displayed = (x, y);
            pending_motion = 0;
        }
        if raw >= 256 {
            wait_input(100);
            continue;
        }
        let key = raw as u8;
        if key == 0xe0 {
            prefix = true;
            continue;
        }
        let extended = core::mem::replace(&mut prefix, false);
        let down = key & 0x80 == 0;
        if key & 0x7f == 0x3c && !extended {
            let toggle = down && !f2_down;
            f2_down = down;
            if !toggle {
                continue;
            }
            console = !console;
            if console {
                cabina::show();
            } else {
                paint(VIEWPORT, space, focus[space]);
                cursor(x, y);
            }
            continue;
        }
        if console {
            if down && !extended {
                cabina::command(key);
            }
            continue;
        }
        match key & 0x7f {
            0x1d => ctrl = down,
            0x5b | 0x5c if extended => super_key = down,
            2..=5 if down && !extended && (!super_key || ctrl) => {
                let selected = usize::from(key - 2);
                if selected != space {
                    space = selected;
                    paint(VIEWPORT, space, focus[space]);
                    cursor(x, y);
                }
            }
            2..=3 if down && super_key && !extended => {
                let selected = usize::from(key - 2);
                if selected != focus[space] {
                    focus[space] = selected;
                    paint(VIEWPORT, space, selected);
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
