//! Search the flat Win64 package namespace.

use core::sync::atomic::{AtomicU64, Ordering::Relaxed};

use super::{CONTENT, ERROR_FILE_NOT_FOUND, ERROR_INVALID_HANDLE, ERROR_INVALID_PARAMETER, HANDLE_TAG,
            INVALID_HANDLE, PATH, ascii_lower, fail};

const FIND_DATA_BYTES: usize = 592;
const FILE_NAME_OFFSET: usize = 44;
const READONLY: u32 = 1;
const NORMAL: u32 = 0x80;
const ERROR_TOO_MANY_OPEN_FILES: u32 = 4;
const ERROR_NO_MORE_FILES: u32 = 18;
const ERROR_NOT_SUPPORTED: u32 = 50;
const INPUT_FILE: u64 = 1;
const OUTPUT_FILE: u64 = 2;
const ACTIVE: u64 = 4;
const FIND_HANDLE: u64 = 1; // Regular package handles have their low word clear.
const STATE_MASK: u64 = u32::MAX as u64;
const MAX_PATTERN: usize = 260;

static SEARCH: AtomicU64 = AtomicU64::new(HANDLE_TAG);

fn entry(which: u64) -> Option<(&'static [u16], usize, u32)> {
    if which == INPUT_FILE {
        return Some((&PATH, CONTENT.len(), READONLY));
    }
    if which == OUTPUT_FILE {
        return super::scratch::length().map(|size| (&super::OUTPUT_PATH[..], size, NORMAL));
    }
    None
}

unsafe fn read_pattern(path: *const u16) -> Option<usize> {
    for index in 0..MAX_PATTERN {
        match unsafe { path.add(index).read_unaligned() } {
            0 => return (index > 0).then_some(index),
            47 | 58 | 92 => return None, // Root-relative basenames only.
            _ => (),
        }
    }
    None
}

unsafe fn matches_pattern(path: *const u16, length: usize, name: &[u16], case_sensitive: bool) -> bool {
    let (mut pattern, mut text) = (0, 0);
    let mut star = None;
    let mut restart = 0;
    while let Some(&expected) = name.get(text).filter(|&&unit| unit != 0) {
        if pattern < length {
            let unit = unsafe { path.add(pattern).read_unaligned() };
            if unit == u16::from(b'*') {
                star = Some(pattern);
                restart = text;
                pattern += 1;
                continue;
            }
            let candidate = if case_sensitive { unit } else { ascii_lower(unit) };
            if unit == u16::from(b'?') || candidate == expected {
                text += 1;
                pattern += 1;
                continue;
            }
        }
        let Some(previous_star) = star else { return false };
        restart += 1;
        text = restart;
        pattern = previous_star + 1;
    }
    (pattern..length).all(|index| unsafe { path.add(index).read_unaligned() } == u16::from(b'*'))
}

unsafe fn find_next(state: u64, info: *mut u8) -> Option<u64> {
    let mut rest = state;
    for which in [INPUT_FILE, OUTPUT_FILE] {
        if rest & which == 0 {
            continue;
        }
        rest &= !which;
        if let Some((name, length, attributes)) = entry(which) {
            unsafe {
                for index in 0..FIND_DATA_BYTES {
                    info.add(index).write_volatile(0);
                }
                info.cast::<u32>().write_unaligned(attributes);
                info.add(28).cast::<u32>().write_unaligned((length as u64 >> 32) as u32);
                info.add(32).cast::<u32>().write_unaligned(length as u32);
                let filename = info.add(FILE_NAME_OFFSET).cast::<u16>();
                for (index, unit) in name.iter().enumerate() {
                    filename.add(index).write_unaligned(*unit);
                }
            }
            return Some(rest);
        }
    }
    None
}

#[unsafe(no_mangle)]
pub unsafe extern "win64" fn bmo_package_find_first(
    path: *const u16, level: u32, info: *mut u8, operation: u32, filter: usize, flags: u32,
) -> usize {
    if path.is_null() || info.is_null() || level > 1 || filter != 0 || flags & !3 != 0 {
        fail(ERROR_INVALID_PARAMETER);
        return INVALID_HANDLE;
    }
    if operation != 0 {
        fail(ERROR_NOT_SUPPORTED);
        return INVALID_HANDLE;
    }
    let Some(length) = (unsafe { read_pattern(path) }) else {
        fail(ERROR_FILE_NOT_FOUND);
        return INVALID_HANDLE;
    };
    let mut state = SEARCH.load(Relaxed);
    if state & ACTIVE != 0 || state == 0 {
        fail(ERROR_TOO_MANY_OPEN_FILES);
        return INVALID_HANDLE;
    }
    for which in [INPUT_FILE, OUTPUT_FILE] {
        if let Some((name, _, _)) = entry(which) {
            if unsafe { matches_pattern(path, length, name, flags & 1 != 0) } {
                state |= which;
            }
        }
    }
    let Some(remaining) = (unsafe { find_next(state, info) }) else {
        fail(ERROR_FILE_NOT_FOUND);
        return INVALID_HANDLE;
    };
    SEARCH.store(remaining | ACTIVE, Relaxed);
    ((state & !STATE_MASK) | FIND_HANDLE) as usize
}

fn active(handle: usize) -> Option<u64> {
    let state = SEARCH.load(Relaxed);
    if state & ACTIVE != 0 && ((state & !STATE_MASK) | FIND_HANDLE) == handle as u64 {
        Some(state)
    } else {
        fail(ERROR_INVALID_HANDLE);
        None
    }
}

#[unsafe(no_mangle)]
pub unsafe extern "win64" fn bmo_package_find_next(handle: usize, info: *mut u8) -> i32 {
    if info.is_null() {
        fail(ERROR_INVALID_PARAMETER);
        return 0;
    }
    let Some(state) = active(handle) else { return 0 };
    if let Some(remaining) = unsafe { find_next(state, info) } {
        SEARCH.store(remaining, Relaxed);
        return 1;
    }
    SEARCH.store(state & !(INPUT_FILE | OUTPUT_FILE), Relaxed);
    fail(ERROR_NO_MORE_FILES);
    0
}

#[unsafe(no_mangle)]
pub extern "win64" fn bmo_package_find_close(handle: usize) -> i32 {
    let Some(state) = active(handle) else { return 0 };
    SEARCH.store((state & !STATE_MASK).wrapping_add(HANDLE_TAG), Relaxed);
    1
}
