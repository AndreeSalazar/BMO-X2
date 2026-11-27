//! Win64 FLS for the single execution context of the process profile.
#![no_std]

use core::ffi::c_void;
use core::ptr::{addr_of_mut, null_mut};
use core::sync::atomic::{AtomicBool, Ordering::Relaxed};

const SLOT_COUNT: usize = 128;
const ERROR_INVALID_PARAMETER: u32 = 87;
const ERROR_NO_MORE_ITEMS: u32 = 259;
type Callback = unsafe extern "win64" fn(*mut c_void);

#[derive(Clone, Copy, PartialEq)]
enum SlotState {
    Free,
    Live,
    Releasing,
}

#[derive(Clone, Copy)]
struct Slot {
    state: SlotState,
    value: *mut c_void,
    callback: Option<Callback>,
}

const EMPTY: Slot = Slot { state: SlotState::Free, value: null_mut(), callback: None };
static mut SLOTS: [Slot; SLOT_COUNT] = [EMPTY; SLOT_COUNT];
static EXITING: AtomicBool = AtomicBool::new(false);

unsafe extern "win64" {
    fn bmo_set_last_error(error: u32);
}

fn slot_at(index: u32) -> Option<*mut Slot> {
    (index < SLOT_COUNT as u32)
        .then(|| unsafe { addr_of_mut!(SLOTS).cast::<Slot>().add(index as usize) })
}

fn release(slot: *mut Slot, exiting: bool) {
    // Keep the index reserved across the callback. It may call FLS again.
    // Never keep a Rust reference to a slot while executing guest code.
    let saved = unsafe { slot.read() };
    unsafe {
        (*slot).state = SlotState::Releasing;
        if !exiting {
            (*slot).value = null_mut();
        }
        if let Some(callback) = saved.callback.filter(|_| !saved.value.is_null()) {
            callback(saved.value);
        }
        slot.write(EMPTY);
    }
}

#[unsafe(no_mangle)]
pub extern "win64" fn bmo_fls_alloc(callback: Option<Callback>) -> u32 {
    if !EXITING.load(Relaxed) {
        for index in 0..SLOT_COUNT {
            let slot = unsafe { addr_of_mut!(SLOTS).cast::<Slot>().add(index) };
            if unsafe { (*slot).state } == SlotState::Free {
                unsafe { slot.write(Slot { state: SlotState::Live, callback, ..EMPTY }) };
                return index as u32;
            }
        }
    }
    unsafe { bmo_set_last_error(ERROR_NO_MORE_ITEMS) };
    u32::MAX
}

#[unsafe(no_mangle)]
pub extern "win64" fn bmo_fls_free(index: u32) -> i32 {
    if let Some(slot) = slot_at(index).filter(|&slot| unsafe { (*slot).state } == SlotState::Live) {
        release(slot, false);
        return 1;
    }
    unsafe { bmo_set_last_error(ERROR_INVALID_PARAMETER) };
    0
}

#[unsafe(no_mangle)]
pub extern "win64" fn bmo_fls_get_value(index: u32) -> *mut c_void {
    if let Some(slot) = slot_at(index) {
        unsafe { bmo_set_last_error(0) };
        unsafe { (*slot).value }
    } else {
        unsafe { bmo_set_last_error(ERROR_INVALID_PARAMETER) };
        null_mut()
    }
}

#[unsafe(no_mangle)]
pub extern "win64" fn bmo_fls_set_value(index: u32, value: *mut c_void) -> i32 {
    if let Some(slot) = slot_at(index) {
        unsafe { (*slot).value = value };
        1
    } else {
        unsafe { bmo_set_last_error(ERROR_INVALID_PARAMETER) };
        0
    }
}

#[unsafe(no_mangle)]
pub extern "win64" fn bmo_fls_shutdown() {
    if EXITING.swap(true, Relaxed) {
        return;
    }
    for index in 0..SLOT_COUNT {
        let slot = unsafe { addr_of_mut!(SLOTS).cast::<Slot>().add(index) };
        if unsafe { (*slot).state } == SlotState::Live {
            release(slot, true);
        }
    }
}
