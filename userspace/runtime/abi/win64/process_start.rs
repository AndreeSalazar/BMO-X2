//! Startup calls for the external single-process Win64 session.
#![no_std]

use core::arch::asm;

const COMMAND_BYTES: usize = include_bytes!(env!("BMO_WIN64_CMDLINE")).len();
const _: () = assert!(COMMAND_BYTES >= 2 && COMMAND_BYTES % 2 == 0);

#[repr(align(2))]
pub struct CommandLine([u8; COMMAND_BYTES]);

#[unsafe(no_mangle)]
pub static BMO_WIN64_COMMAND_LINE: CommandLine = CommandLine(*include_bytes!(env!("BMO_WIN64_CMDLINE")));

#[repr(C)]
struct ResultWords {
    status: i64,
    value: u64,
}

unsafe extern "win64" {
    fn bmo_invoke(cap: u64, op: u64, arg0: u64, arg1: u64, arg2: u64) -> ResultWords;
}

#[unsafe(no_mangle)]
pub extern "win64" fn bmo_get_command_line_w() -> *const u16 {
    BMO_WIN64_COMMAND_LINE.0.as_ptr().cast()
}

#[unsafe(no_mangle)]
pub extern "win64" fn bmo_exit_process(code: u32) -> ! {
    unsafe {
        bmo_invoke(4, 2, u64::from(code), 0, 0);
        // The supervisor terminates the process. A returning gate is fatal.
        asm!("ud2", options(noreturn, nostack));
    }
}
