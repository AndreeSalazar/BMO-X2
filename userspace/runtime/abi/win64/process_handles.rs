//! Standard handle slots of the external Win64 process.
#![no_std]

use core::sync::atomic::{AtomicUsize, Ordering::Relaxed};

// The supervisor exposes one redirected output stream as ABI capability 4.
static INPUT: AtomicUsize = AtomicUsize::new(0);
static OUTPUT: AtomicUsize = AtomicUsize::new(4);
static ERROR: AtomicUsize = AtomicUsize::new(4);

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
