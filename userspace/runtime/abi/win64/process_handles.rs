//! Standard handle slots of the external Win64 process.
#![no_std]

use core::sync::atomic::{AtomicUsize, Ordering::Relaxed};

// The supervisor exposes one redirected output stream as ABI capability 4.
static INPUT: AtomicUsize = AtomicUsize::new(0);
static OUTPUT: AtomicUsize = AtomicUsize::new(4);
static ERROR: AtomicUsize = AtomicUsize::new(4);
const ERROR_INVALID_HANDLE: u32 = 6;

unsafe extern "win64" {
    fn bmo_set_last_error(error: u32);
}

fn standard_slot(selector: u32) -> Option<&'static AtomicUsize> {
    match selector as i32 {
        -10 => Some(&INPUT),
        -11 => Some(&OUTPUT),
        -12 => Some(&ERROR),
        _ => None,
    }
}

fn no_console() -> i32 {
    // The session has redirected streams and has no attached console device.
    unsafe { bmo_set_last_error(ERROR_INVALID_HANDLE) };
    0
}

#[unsafe(no_mangle)]
pub extern "win64" fn bmo_get_console_mode(_handle: usize, _mode: *mut u32) -> i32 {
    no_console()
}

#[unsafe(no_mangle)]
pub extern "win64" fn bmo_get_console_output_cp() -> u32 {
    no_console() as u32
}

#[unsafe(no_mangle)]
pub extern "win64" fn bmo_read_console_w(
    _handle: usize, _buffer: *mut u16, _count: u32, _read: *mut u32, _control: usize,
) -> i32 {
    no_console()
}

#[unsafe(no_mangle)]
pub extern "win64" fn bmo_write_console_w(
    _handle: usize, _buffer: *const u16, _count: u32, _written: *mut u32, _reserved: usize,
) -> i32 {
    no_console()
}

#[unsafe(no_mangle)]
pub extern "win64" fn bmo_get_std_handle(selector: u32) -> usize {
    if let Some(slot) = standard_slot(selector) {
        return slot.load(Relaxed);
    }
    unsafe { bmo_set_last_error(87) };
    usize::MAX
}

#[unsafe(no_mangle)]
pub extern "win64" fn bmo_set_std_handle(selector: u32, handle: usize) -> i32 {
    if let Some(slot) = standard_slot(selector) {
        slot.store(handle, Relaxed);
        return 1;
    }
    unsafe { bmo_set_last_error(87) };
    0
}
