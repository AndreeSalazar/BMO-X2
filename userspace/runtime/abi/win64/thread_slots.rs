//! Dynamic Win64 TLS for the external single-threaded process profile.
#![no_std]

use core::ffi::c_void;
use core::ptr::null_mut;
use core::sync::atomic::{AtomicPtr, AtomicU64, Ordering::Relaxed};

const SLOT_COUNT: usize = u64::BITS as usize;
const ERROR_INVALID_PARAMETER: u32 = 87;
const ERROR_NO_MORE_ITEMS: u32 = 259;

// The profile runs exactly one thread. Allocation lives at process scope,
// while the values belong to that one thread.
static ALLOCATED: AtomicU64 = AtomicU64::new(0);
static VALUES: [AtomicPtr<c_void>; SLOT_COUNT] =
    [const { AtomicPtr::new(null_mut()) }; SLOT_COUNT];

unsafe extern "win64" {
    fn bmo_set_last_error(error: u32);
}

#[unsafe(no_mangle)]
pub extern "win64" fn bmo_tls_alloc() -> u32 {
    let allocated = ALLOCATED.load(Relaxed);
    let index = (!allocated).trailing_zeros();
    if let Some(slot) = VALUES.get(index as usize) {
        slot.store(null_mut(), Relaxed);
        ALLOCATED.store(allocated | (1 << index), Relaxed);
        index
    } else {
        unsafe { bmo_set_last_error(ERROR_NO_MORE_ITEMS) };
        u32::MAX
    }
}

#[unsafe(no_mangle)]
pub extern "win64" fn bmo_tls_free(index: u32) -> i32 {
    let allocated = ALLOCATED.load(Relaxed);
    if let Some(slot) = VALUES.get(index as usize) {
        let bit = 1 << index;
        if allocated & bit != 0 {
            ALLOCATED.store(allocated & !bit, Relaxed);
            slot.store(null_mut(), Relaxed);
            return 1;
        }
    }
    unsafe { bmo_set_last_error(ERROR_INVALID_PARAMETER) };
    0
}

#[unsafe(no_mangle)]
pub extern "win64" fn bmo_tls_get_value(index: u32) -> *mut c_void {
    if let Some(slot) = VALUES.get(index as usize) {
        unsafe { bmo_set_last_error(0) };
        slot.load(Relaxed)
    } else {
        unsafe { bmo_set_last_error(ERROR_INVALID_PARAMETER) };
        null_mut()
    }
}

#[unsafe(no_mangle)]
pub extern "win64" fn bmo_tls_set_value(index: u32, value: *mut c_void) -> i32 {
    if let Some(slot) = VALUES.get(index as usize) {
        slot.store(value, Relaxed);
        1
    } else {
        unsafe { bmo_set_last_error(ERROR_INVALID_PARAMETER) };
        0
    }
}
