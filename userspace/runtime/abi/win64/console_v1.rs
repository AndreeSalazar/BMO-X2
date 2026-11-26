//! Win64 imports backed by the external BMO console profile.
#![no_std]

#[repr(C)]
struct BmoResult {
    status: i64,
    value: u64,
}

unsafe extern "win64" {
    fn bmo_invoke(cap: u64, op: u64, arg0: u64, arg1: u64, arg2: u64) -> BmoResult;
}

const STDOUT: usize = 4;

#[unsafe(no_mangle)]
pub extern "win64" fn bmo_session_tick_ms() -> u64 {
    unsafe { bmo_invoke(2, 2, 0, 0, 0).value / 1_000_000 }
}

#[unsafe(no_mangle)]
pub extern "win64" fn bmo_session_stdout(selector: u32) -> usize {
    if selector == (-11i32) as u32 { STDOUT } else { usize::MAX }
}

#[unsafe(no_mangle)]
pub unsafe extern "win64" fn bmo_session_write(
    handle: usize, buffer: *const u8, count: u32, written: *mut u32, overlapped: usize,
) -> i32 {
    if written.is_null() {
        return 0;
    }
    unsafe { written.write_unaligned(0); }
    if handle != STDOUT || overlapped != 0 || buffer.is_null() || count > 4096 {
        return 0;
    }
    let mut sent = 0;
    while sent < count {
        let len = (count - sent).min(8);
        let mut payload = 0u64;
        for index in 0..len {
            let byte = unsafe { buffer.add((sent + index) as usize).read() };
            payload |= u64::from(byte) << (8 * index);
        }
        let result = unsafe { bmo_invoke(STDOUT as u64, 1, payload, u64::from(len), 0) };
        if result.status != 0 || result.value != u64::from(len) {
            return 0;
        }
        sent += len;
        unsafe { written.write_unaligned(sent); }
    }
    1
}
