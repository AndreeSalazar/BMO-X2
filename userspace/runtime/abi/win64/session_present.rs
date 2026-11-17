//! Present the 320x200 surface of the QEMU Win64 session fixture.
#![no_std]

use core::arch::asm;

#[unsafe(no_mangle)]
pub extern "win64" fn bmo_session_present(pixels: *const u32) -> u64 {
    let result;
    unsafe {
        asm!(
            "syscall",
            inlateout("rax") 0u64 => result,
            inlateout("rdi") 1u64 => _, inlateout("rsi") 6u64 => _,
            inlateout("rdx") pixels => _, inlateout("r10") 0u64 => _,
            lateout("rcx") _, lateout("r8") _, lateout("r9") _, lateout("r11") _,
        );
    }
    result
}
