//! Package input and optional scratch output for the single-threaded Win64 fixture.
#![no_std]

use core::sync::atomic::{AtomicU64, Ordering::Relaxed};

const PATH: [u16; 10] = [105, 110, 112, 117, 116, 46, 98, 105, 110, 0];
const CONTENT: &[u8] = include_bytes!(env!("BMO_PACKAGE_INPUT"));
const INVALID_HANDLE: usize = usize::MAX;
const SESSION_STDOUT: usize = 4;
const LIVE: u64 = 1 << 31;
const OUTPUT: u64 = 1 << 30;
const WRITABLE: u64 = 1 << 29;
const HANDLE_TAG: u64 = 1 << 32;
const CURSOR_MASK: u64 = WRITABLE - 1;
const ERROR_FILE_NOT_FOUND: u32 = 2;
const ERROR_ACCESS_DENIED: u32 = 5;
const ERROR_INVALID_HANDLE: u32 = 6;
const ERROR_SHARING_VIOLATION: u32 = 32;
const ERROR_INVALID_PARAMETER: u32 = 87;
#[cfg(bmo_package_output)]
const ERROR_DISK_FULL: u32 = 112;

const _: () = assert!(CONTENT.len() <= CURSOR_MASK as usize);

// High bits identify an open generation. Low bits hold its cursor and live flag.
static SLOT: AtomicU64 = AtomicU64::new(HANDLE_TAG);
unsafe extern "win64" {
    fn bmo_set_last_error(error: u32);
}

#[cfg(bmo_package_argv)]
#[unsafe(no_mangle)]
pub unsafe extern "win64" fn bmo_package_argv(length: *mut usize) -> *const u8 {
    let args = include_bytes!(env!("BMO_PACKAGE_ARGV"));
    unsafe { length.write(args.len()) };
    args.as_ptr()
}

#[cfg(bmo_package_output)]
mod scratch {
    use core::ptr::addr_of_mut;
    use core::sync::atomic::{AtomicUsize, Ordering::Relaxed};

    pub const CAPACITY: usize = 4096;
    const MISSING: usize = usize::MAX;
    static LENGTH: AtomicUsize = AtomicUsize::new(MISSING);
    static mut DATA: [u8; CAPACITY] = [0; CAPACITY];

    pub fn length() -> Option<usize> {
        let size = LENGTH.load(Relaxed);
        (size != MISSING).then_some(size)
    }

    pub fn set_length(size: usize) {
        LENGTH.store(size, Relaxed);
    }

    pub fn buffer() -> *mut u8 {
        addr_of_mut!(DATA).cast()
    }
}

fn fail(error: u32) {
    unsafe { bmo_set_last_error(error) };
}

unsafe fn path_equals(path: *const u16, name: &[u16]) -> bool {
    name.iter().enumerate().all(|(index, expected)| {
        unsafe { path.add(index).read_unaligned() == *expected }
    })
}

fn open_mode(path: *const u16, access: u32, disposition: u32) -> Result<u64, u32> {
    #[cfg(bmo_package_output)]
    {
        const OUTPUT_PATH: [u16; 11] = [111, 117, 116, 112, 117, 116, 46, 98, 105, 110, 0];
        if unsafe { path_equals(path, &OUTPUT_PATH) } {
            return match (access, disposition) {
                (0x4000_0000, 2) => Ok(OUTPUT | WRITABLE),
                (0x8000_0000, 3) if scratch::length().is_some() => Ok(OUTPUT),
                (0x8000_0000, 3) => Err(ERROR_FILE_NOT_FOUND),
                _ => Err(ERROR_ACCESS_DENIED),
            };
        }
    }
    if access != 0x8000_0000 || disposition != 3 {
        return Err(ERROR_ACCESS_DENIED);
    }
    if unsafe { path_equals(path, &PATH) } {
        Ok(0)
    } else {
        Err(ERROR_FILE_NOT_FOUND)
    }
}

fn active(handle: usize) -> Option<u64> {
    let state = SLOT.load(Relaxed);
    if state & LIVE != 0 && state & !(LIVE | OUTPUT | WRITABLE | CURSOR_MASK) == handle as u64 {
        Some(state)
    } else {
        fail(ERROR_INVALID_HANDLE);
        None
    }
}

fn file_length(handle_state: u64) -> usize {
    if handle_state & OUTPUT != 0 {
        #[cfg(bmo_package_output)]
        return scratch::length().unwrap_or(0);
    }
    CONTENT.len()
}

#[unsafe(no_mangle)]
pub extern "win64" fn bmo_package_file_type(handle: usize) -> u32 {
    if handle == SESSION_STDOUT { 2 } else { u32::from(active(handle).is_some()) }
}

#[unsafe(no_mangle)]
pub unsafe extern "win64" fn bmo_package_file_size(handle: usize, size: *mut i64) -> i32 {
    if size.is_null() {
        fail(ERROR_INVALID_PARAMETER);
        return 0;
    }
    let Some(state) = active(handle) else { return 0 };
    unsafe { size.write_unaligned(file_length(state) as i64) };
    1
}

#[unsafe(no_mangle)]
pub unsafe extern "win64" fn bmo_package_open(
    path: *const u16, access: u32, share: u32, security: usize, disposition: u32,
    attributes: u32, template: usize,
) -> usize {
    if path.is_null() || share & !1 != 0 || security != 0 || template != 0
        || !matches!(attributes, 0 | 0x80)
    {
        fail(ERROR_INVALID_PARAMETER);
        return INVALID_HANDLE;
    }
    let mode = match open_mode(path, access, disposition) {
        Ok(mode) => mode,
        Err(error) => {
            fail(error);
            return INVALID_HANDLE;
        }
    };
    let state = SLOT.load(Relaxed);
    if state != 0 && state & LIVE == 0
        && SLOT.compare_exchange(state, state | LIVE | mode, Relaxed, Relaxed).is_ok()
    {
        #[cfg(bmo_package_output)]
        if mode & WRITABLE != 0 {
            scratch::set_length(0);
        }
        return state as usize;
    }
    fail(ERROR_SHARING_VIOLATION);
    INVALID_HANDLE
}

#[unsafe(no_mangle)]
pub unsafe extern "win64" fn bmo_package_read(
    handle: usize, destination: *mut u8, bytes: u32, read: *mut u32, overlapped: usize,
) -> i32 {
    if read.is_null() {
        fail(ERROR_INVALID_PARAMETER);
        return 0;
    }
    unsafe { read.write_unaligned(0) };
    if (destination.is_null() && bytes != 0) || overlapped != 0 {
        fail(ERROR_INVALID_PARAMETER);
        return 0;
    }
    let Some(current) = active(handle) else { return 0 };
    if current & WRITABLE != 0 {
        fail(ERROR_ACCESS_DENIED);
        return 0;
    }
    #[cfg(bmo_package_output)]
    let source = if current & OUTPUT != 0 {
        scratch::buffer() as *const u8
    } else {
        CONTENT.as_ptr()
    };
    #[cfg(not(bmo_package_output))]
    let source = CONTENT.as_ptr();
    let start = (current & CURSOR_MASK) as usize;
    let count = (bytes as usize).min(file_length(current) - start);
    for offset in 0..count {
        unsafe { destination.add(offset).write_volatile(source.add(start + offset).read()) };
    }
    SLOT.store(current + count as u64, Relaxed);
    unsafe { read.write_unaligned(count as u32) };
    1
}

#[cfg(bmo_package_output)]
unsafe extern "win64" {
    fn bmo_session_write(handle: usize, buffer: *const u8, count: u32, written: *mut u32,
                         overlapped: usize) -> i32;
}

#[cfg(bmo_package_output)]
#[unsafe(no_mangle)]
pub unsafe extern "win64" fn bmo_package_write(
    handle: usize, source: *const u8, bytes: u32, written: *mut u32, overlapped: usize,
) -> i32 {
    // Existing stdout handle for this fixture.
    if handle == SESSION_STDOUT {
        return unsafe { bmo_session_write(handle, source, bytes, written, overlapped) };
    }
    if written.is_null() {
        fail(ERROR_INVALID_PARAMETER);
        return 0;
    }
    unsafe { written.write_unaligned(0) };
    if (source.is_null() && bytes != 0) || overlapped != 0 {
        fail(ERROR_INVALID_PARAMETER);
        return 0;
    }
    let Some(current) = active(handle) else { return 0 };
    if current & WRITABLE == 0 {
        fail(ERROR_ACCESS_DENIED);
        return 0;
    }
    let start = (current & CURSOR_MASK) as usize;
    let count = bytes as usize;
    if count > scratch::CAPACITY - start {
        fail(ERROR_DISK_FULL);
        return 0;
    }
    for offset in 0..count {
        unsafe { scratch::buffer().add(start + offset).write_volatile(source.add(offset).read()) };
    }
    scratch::set_length(start + count);
    SLOT.store(current + count as u64, Relaxed);
    unsafe { written.write_unaligned(bytes) };
    1
}

#[unsafe(no_mangle)]
pub extern "win64" fn bmo_package_close(handle: usize) -> i32 {
    let Some(current) = active(handle) else { return 0 };
    let generation = (current >> 32) as u32;
    SLOT.store(u64::from(generation.wrapping_add(1)) << 32, Relaxed);
    1
}
