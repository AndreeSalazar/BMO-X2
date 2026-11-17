//! Microsoft x64 entry points for a freestanding BMO-X2 client.
//! These execute the BMO-X2 syscall ABI and require a BMO-X2 process.
#![no_std]

use core::arch::asm;

#[repr(C)]
pub struct ResultWords {
    status: i64,
    value: u64,
}

#[inline(always)]
unsafe fn portal(service: i64, cap: u64, op: u64, arg0: u64, arg1: u64, arg2: u64) -> ResultWords {
    let status;
    let value;
    unsafe {
        asm!(
            "syscall",
            inlateout("rax") service => status,
            inlateout("rdx") arg0 => value,
            inlateout("rdi") cap => _,
            inlateout("rsi") op => _,
            inlateout("r10") arg1 => _,
            inlateout("r8") arg2 => _,
            inlateout("r9") 0u64 => _,
            lateout("rcx") _,
            lateout("r11") _,
        );
    }
    ResultWords { status, value }
}

#[unsafe(no_mangle)]
pub unsafe extern "win64" fn bmo_invoke(cap: u64, op: u64, arg0: u64, arg1: u64, arg2: u64) -> ResultWords {
    unsafe { portal(0, cap, op, arg0, arg1, arg2) }
}

#[unsafe(no_mangle)]
pub unsafe extern "win64" fn bmo_wait(cap: u64, sequence: u64, deadline: u64) -> ResultWords {
    unsafe { portal(1, cap, sequence, deadline, 0, 0) }
}
