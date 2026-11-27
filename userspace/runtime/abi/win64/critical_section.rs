//! In-process critical sections for the single-threaded Win64 session.
#![no_std]

const NO_DEBUG_INFO: u32 = 0x0100_0000;
const INVALID_PARAMETER: u32 = 87;
const SESSION_THREAD_ID: u32 = 1;

#[repr(C)]
pub struct CriticalSection {
    debug_info: usize,
    lock_count: i32,
    recursion_count: i32,
    owning_thread: usize,
    semaphore: usize,
    spin_count: usize,
}

const _: () = assert!(core::mem::size_of::<CriticalSection>() == 40);

unsafe extern "win64" {
    fn bmo_set_last_error(error: u32);
}

#[unsafe(no_mangle)]
pub extern "win64" fn bmo_get_current_thread_id() -> u32 {
    SESSION_THREAD_ID
}

#[unsafe(no_mangle)]
pub unsafe extern "win64" fn bmo_initialize_critical_section_ex(
    section: *mut CriticalSection, _spin: u32, flags: u32,
) -> i32 {
    if section.is_null() || flags & !NO_DEBUG_INFO != 0 {
        unsafe { bmo_set_last_error(INVALID_PARAMETER) };
        return 0;
    }
    // There is no other runnable thread in this profile, so spinning is disabled.
    unsafe {
        section.write(CriticalSection {
            debug_info: usize::MAX,
            lock_count: -1,
            recursion_count: 0,
            owning_thread: 0,
            semaphore: 0,
            spin_count: 0,
        })
    };
    1
}

#[unsafe(no_mangle)]
pub unsafe extern "win64" fn bmo_initialize_critical_section_and_spin_count(
    section: *mut CriticalSection, spin: u32,
) -> i32 {
    unsafe { bmo_initialize_critical_section_ex(section, spin, 0) }
}

#[unsafe(no_mangle)]
pub unsafe extern "win64" fn bmo_enter_critical_section(section: *mut CriticalSection) {
    let section = unsafe { &mut *section };
    section.recursion_count += 1;
    section.lock_count = -2;
    section.owning_thread = SESSION_THREAD_ID as usize;
}

#[unsafe(no_mangle)]
pub unsafe extern "win64" fn bmo_leave_critical_section(section: *mut CriticalSection) {
    let section = unsafe { &mut *section };
    section.recursion_count -= 1;
    if section.recursion_count == 0 {
        section.lock_count = -1;
        section.owning_thread = 0;
    }
}

#[unsafe(no_mangle)]
pub unsafe extern "win64" fn bmo_delete_critical_section(section: *mut CriticalSection) {
    unsafe { section.write_bytes(0, 1) };
}
