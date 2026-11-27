//! Last-error state for the single-threaded external Win64 session.
#![no_std]

use core::sync::atomic::{AtomicU32, Ordering::Relaxed};

static LAST_ERROR: AtomicU32 = AtomicU32::new(0);

#[unsafe(no_mangle)]
pub extern "win64" fn bmo_get_last_error() -> u32 {
    LAST_ERROR.load(Relaxed)
}

#[unsafe(no_mangle)]
pub extern "win64" fn bmo_set_last_error(error: u32) {
    LAST_ERROR.store(error, Relaxed);
}
