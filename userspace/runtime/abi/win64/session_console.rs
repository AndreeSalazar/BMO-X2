//! Synchronous stdout subset for the three-region QEMU session.
#![no_std]

use core::arch::asm;

const STDOUT: usize = 1;
const USER_READ_BEGIN: usize = 0x40200000;
const USER_RW_BEGIN: usize = 0x40400000;
const USER_DATA_END: usize = 0x40600000;

#[unsafe(no_mangle)]
pub extern "win64" fn bmo_session_stdout(selector: u32) -> usize {
    if selector == (-11i32) as u32 { STDOUT } else { usize::MAX }
}

#[unsafe(no_mangle)]
pub unsafe extern "win64" fn bmo_session_write(
    handle: usize, buffer: *const u8, count: u32, written: *mut u32, overlapped: usize,
) -> i32 {
    let output = written as usize;
    if !(USER_RW_BEGIN..=USER_DATA_END - 4).contains(&output) || output % 4 != 0 {
        return 0;
    }
    unsafe { written.write(0); }
    let start = buffer as usize;
    let len = count as usize;
    if handle != STDOUT || overlapped != 0 || len > 4096
        || !(USER_READ_BEGIN..USER_DATA_END).contains(&start) || len > USER_DATA_END - start {
        return 0;
    }
    for n in 0..len {
        let result: u64;
        let byte = unsafe { buffer.add(n).read() };
        unsafe {
            asm!(
                "syscall",
                inlateout("rax") 0u64 => result,
                inlateout("rdi") 5u64 => _, inlateout("rsi") 7u64 => _,
                inlateout("rdx") u64::from(byte) => _, inlateout("r10") 0u64 => _,
                lateout("rcx") _, lateout("r8") _, lateout("r9") _, lateout("r11") _,
            );
            written.write(if result == 0 { n as u32 + 1 } else { n as u32 });
        }
        if result != 0 { return 0; }
    }
    1
}
