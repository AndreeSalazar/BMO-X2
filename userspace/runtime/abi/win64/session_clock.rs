//! Clock for the QEMU session profile, whose diagnostic exposes PIT ticks.
#![no_std]

use core::arch::asm;

#[unsafe(no_mangle)]
pub extern "win64" fn bmo_session_tick_ms() -> u64 {
    let ticks: u64;
    unsafe {
        asm!(
            "syscall",
            inlateout("rax") 0u64 => ticks,
            inlateout("rdi") 3u64 => _,
            inlateout("rsi") 3u64 => _,
            inlateout("rdx") 0u64 => _,
            inlateout("r10") 0u64 => _,
            lateout("rcx") _, lateout("r8") _, lateout("r9") _, lateout("r11") _,
        );
    }
    // The diagnostic returns the low 32 bits of a nominal 100 Hz clock.
    u64::from(ticks as u32) * 10
}
