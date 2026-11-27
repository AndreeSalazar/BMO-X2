//! Startup calls for the external single-process Win64 session.
#![no_std]

use core::arch::asm;

const COMMAND_BYTES: usize = include_bytes!(env!("BMO_WIN64_CMDLINE")).len();
const ANSI_BYTES: usize = include_bytes!(env!("BMO_WIN64_CMDLINE_A")).len();
const CP_UTF8: u32 = 65001;
const STARTUP_INFO_BYTES: usize = 104;
const _: () = assert!(COMMAND_BYTES >= 2 && COMMAND_BYTES % 2 == 0);

#[repr(align(2))]
pub struct CommandLine([u8; COMMAND_BYTES]);

#[unsafe(no_mangle)]
pub static BMO_WIN64_COMMAND_LINE: CommandLine = CommandLine(*include_bytes!(env!("BMO_WIN64_CMDLINE")));

#[unsafe(no_mangle)]
pub static BMO_WIN64_COMMAND_LINE_A: [u8; ANSI_BYTES] = *include_bytes!(env!("BMO_WIN64_CMDLINE_A"));

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
pub extern "win64" fn bmo_get_acp() -> u32 {
    CP_UTF8
}

#[unsafe(no_mangle)]
pub extern "win64" fn bmo_get_command_line_a() -> *const u8 {
    BMO_WIN64_COMMAND_LINE_A.as_ptr()
}

#[unsafe(no_mangle)]
pub unsafe extern "win64" fn bmo_get_startup_info_w(info: *mut u8) {
    // The bare session supplies no launcher overrides or inherited handles.
    unsafe { info.cast::<u32>().write_unaligned(STARTUP_INFO_BYTES as u32) };
    for offset in 4..STARTUP_INFO_BYTES {
        unsafe { info.add(offset).write_volatile(0) };
    }
}

#[repr(C, align(16))]
pub struct SListHeader([u64; 2]);

#[unsafe(no_mangle)]
pub unsafe extern "win64" fn bmo_initialize_slist_head(head: *mut SListHeader) {
    unsafe { head.write(SListHeader([0; 2])) };
}

#[unsafe(no_mangle)]
pub extern "win64" fn bmo_exit_process(code: u32) -> ! {
    unsafe {
        bmo_invoke(4, 2, u64::from(code), 0, 0);
        // The supervisor terminates the process. A returning gate is fatal.
        asm!("ud2", options(noreturn, nostack));
    }
}
