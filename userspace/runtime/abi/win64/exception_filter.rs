//! Top-level exception filter for the single-threaded Win64 process.
#![no_std]

use core::ffi::c_void;
use core::ptr::addr_of_mut;

type Filter = unsafe extern "win64" fn(*mut c_void) -> i32;
const CONTINUE_SEARCH: i32 = 0;
const EXECUTE_HANDLER: i32 = 1;

static mut FILTER: Option<Filter> = None;

#[unsafe(no_mangle)]
pub extern "win64" fn bmo_set_unhandled_exception_filter(filter: Option<Filter>) -> Option<Filter> {
    unsafe { addr_of_mut!(FILTER).replace(filter) }
}

#[unsafe(no_mangle)]
pub unsafe extern "win64" fn bmo_unhandled_exception_filter(pointers: *mut c_void) -> i32 {
    // Copy the callback before invoking it. It can replace or clear itself.
    if let Some(filter) = unsafe { addr_of_mut!(FILTER).read() } {
        let disposition = unsafe { filter(pointers) };
        if disposition != CONTINUE_SEARCH {
            return disposition;
        }
    }
    EXECUTE_HANDLER
}
