//! Present the 320x200 surface of the QEMU Win64 session fixture.
#![no_std]

use core::arch::asm;
use core::ffi::c_void;
use core::ptr::{addr_of_mut, read_volatile, write_volatile};

use bmo_director::{Desktop, Frame, Keyboard, KeyEvent, Surface};

const WIDTH: usize = 320;
const HEIGHT: usize = 200;
const PANEL_X: usize = 24;
const PANEL_Y: usize = 44;
const PANEL_W: usize = 273;
const PANEL_H: usize = 119;

#[unsafe(no_mangle)]
static mut director_pixels: [u32; WIDTH * HEIGHT] = [0; WIDTH * HEIGHT];
#[unsafe(no_mangle)]
static mut director_state: u64 = 0;
static mut PANEL: [u32; PANEL_W * PANEL_H] = [0; PANEL_W * PANEL_H];

#[unsafe(no_mangle)]
pub unsafe extern "win64" fn bmo_director_window(source: *mut u32) -> ! {
    let source = unsafe { core::slice::from_raw_parts_mut(source, WIDTH * HEIGHT) };
    let panel = unsafe { &mut *addr_of_mut!(PANEL) };
    for row in 0..PANEL_H {
        let at = (row + PANEL_Y) * WIDTH + PANEL_X;
        let segment = &mut source[at..at + PANEL_W];
        panel[row*PANEL_W..(row+1)*PANEL_W].copy_from_slice(segment);
        segment.fill(0x0b101f + ((row + PANEL_Y) as u32 / 14) * 0x010102);
    }
    let panel = Surface::new(PANEL_W, PANEL_H, panel).unwrap();
    let backdrop = Surface::new(WIDTH, HEIGHT, source).unwrap();
    let mut desktop = Desktop::<2>::new();
    desktop.open(1, 0, 0, backdrop).unwrap();
    desktop.open(2, PANEL_X as i32, PANEL_Y as i32, panel).unwrap();
    let mut keyboard = Keyboard::default();
    let (mut extended, mut super_down, mut generation) = (false, 0u8, 0u64);
    let pixels = unsafe { &mut *addr_of_mut!(director_pixels) };
    let mut dirty = true;
    loop {
        if dirty {
            desktop.compose(&mut Frame::new(WIDTH, HEIGHT, pixels).unwrap(), 0x0b101f);
            if gate(0, 1, 6, pixels.as_ptr() as u64) != 0 { stop(); }
            generation += 1;
            let visible = u64::from(desktop.focused() == Some(2));
            unsafe { write_volatile(addr_of_mut!(director_state), (generation << 1) | visible); }
            dirty = false;
        }
        let scan = gate(0, 2, 2, 0);
        if scan > 255 {
            gate(1, 2, 0, 1);
            continue;
        }
        let byte = scan as u8;
        if byte == 0xe0 {
            extended = true;
            continue;
        }
        let pressed = byte & 0x80 == 0;
        let code = byte & 0x7f;
        if core::mem::take(&mut extended) {
            if matches!(code, 0x5b | 0x5c) {
                let mask = 1 << (code - 0x5b);
                if pressed { super_down |= mask; } else { super_down &= !mask; }
            }
            continue;
        }
        if pressed && code == 0x3b && desktop.focused() != Some(2) {
            dirty = desktop.open(2, PANEL_X as i32, PANEL_Y as i32, panel).is_ok();
        } else if code == 0x10 {
            let had_panel = desktop.focused() == Some(2);
            keyboard.route(&mut desktop, KeyEvent {scancode: code, pressed},
                           if had_panel && super_down != 0 { 32 } else { 0 });
            dirty = had_panel && desktop.focused() != Some(2);
        }
    }
}

fn gate(service: u64, cap: u64, op: u64, arg: u64) -> u64 {
    let result;
    unsafe {
        asm!(
            "syscall",
            inlateout("rax") service => result,
            inlateout("rdi") cap => _, inlateout("rsi") op => _,
            inlateout("rdx") arg => _, inlateout("r10") 0u64 => _,
            lateout("rcx") _, lateout("r8") _, lateout("r9") _, lateout("r11") _,
        );
    }
    result
}

#[panic_handler]
fn panic(_: &core::panic::PanicInfo<'_>) -> ! { stop() }

fn stop() -> ! {
    loop { core::hint::spin_loop(); }
}

// The freestanding MSVC link supplies no CRT.
#[unsafe(no_mangle)]
unsafe extern "C" fn memcpy(dst: *mut c_void, src: *const c_void, len: usize) -> *mut c_void {
    for i in 0..len { unsafe { write_volatile(dst.cast::<u8>().add(i), read_volatile(src.cast::<u8>().add(i))); } }
    dst
}

#[unsafe(no_mangle)]
unsafe extern "C" fn memset(dst: *mut c_void, value: i32, len: usize) -> *mut c_void {
    for i in 0..len { unsafe { write_volatile(dst.cast::<u8>().add(i), value as u8); } }
    dst
}

#[unsafe(no_mangle)]
unsafe extern "C" fn memmove(dst: *mut c_void, src: *const c_void, len: usize) -> *mut c_void {
    if dst.addr() <= src.addr() {
        return unsafe { memcpy(dst, src, len) };
    }
    for i in (0..len).rev() {
        unsafe { write_volatile(dst.cast::<u8>().add(i), read_volatile(src.cast::<u8>().add(i))); }
    }
    dst
}
