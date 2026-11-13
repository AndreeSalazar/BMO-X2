#![no_std]
#![no_main]

#[repr(C)]
struct Reply {
    status: i64,
    value: u64,
}

unsafe extern "C" {
    fn bmo_invoke(cap: u64, op: u64, a: u64, b: u64, c: u64) -> Reply;
    fn bmo_wait(cap: u64, sequence: u64, deadline: u64) -> Reply;
    fn doom_probe_complete() -> !;
}

#[unsafe(no_mangle)]
extern "C" fn bmo_main() -> ! {
    let echo = unsafe { bmo_invoke(1, 1, 0x324f4d42, 0, 0) };
    let wait = unsafe { bmo_wait(1, 0, 0) };
    let denied = unsafe { bmo_invoke(0, 1, 0, 0, 0) };
    if (echo.status, echo.value, wait.status, wait.value, denied.status, denied.value)
        == (0, 0x324f4d42, -4, 0, -2, 0)
    {
        unsafe { doom_probe_complete() };
    }
    stop()
}

#[panic_handler]
fn panic(_: &core::panic::PanicInfo<'_>) -> ! {
    stop()
}

fn stop() -> ! {
    loop { core::hint::spin_loop(); }
}
