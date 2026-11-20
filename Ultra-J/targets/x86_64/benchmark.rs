#![no_std]

use core::{arch::asm, ptr};

const SAMPLES: usize = 31;
const ACTIONS: usize = 2048;
const MAGIC: u64 = u64::from_le_bytes(*b"UJBM0001");

type Action = unsafe extern "C" fn(*mut u64) -> u32;

extern "C" {
    fn run_action(arena: *mut u64) -> u32;
}

// Match the demo's object sizes, tags, methods, result and arena scrub.
#[inline(never)]
unsafe extern "C" fn rust_action(arena: *mut u64) -> u32 {
    let window = arena.cast::<u8>();
    let button = arena.add(4).cast::<u8>();
    ptr::write_volatile(window, 1);
    ptr::write_volatile(button, 2);
    ptr::write_volatile(window.add(1), 1);
    ptr::write_volatile(button.add(1), 1);
    let result = ptr::read_volatile(button.add(1));
    for word in 0..6 {
        ptr::write_volatile(arena.add(word), 0);
    }
    u32::from(result)
}

#[inline(always)]
fn ticks() -> u64 {
    let (lo, hi): (u32, u32);
    unsafe {
        asm!("lfence", "rdtsc", "lfence",
             out("eax") lo, out("edx") hi, options(nostack, preserves_flags));
    }
    u64::from(hi) << 32 | u64::from(lo)
}

#[inline(never)]
unsafe fn batch(action: Action, arena: *mut u64) -> (u64, u32) {
    let start = ticks();
    let mut mismatch = 0;
    for _ in 0..ACTIONS {
        mismatch |= action(arena) ^ 1;
    }
    (ticks().wrapping_sub(start), mismatch)
}

unsafe fn measure(action: Action, arena: *mut u64, slot: *mut u64) -> bool {
    let (elapsed, mismatch) = batch(action, arena);
    if elapsed == 0 || mismatch != 0 {
        return false;
    }
    for word in 0..32 {
        if ptr::read_volatile(arena.add(word)) != 0 {
            return false;
        }
    }
    ptr::write_volatile(slot, elapsed);
    true
}

#[no_mangle]
pub unsafe extern "C" fn ultra_j_benchmark(arena: *mut u64, output: *mut u64) {
    ptr::write_volatile(output, 0);
    let samples = output.add(3);
    if !measure(run_action, arena, samples) || !measure(rust_action, arena, samples) {
        return;
    }
    for i in 0..SAMPLES {
        let uj = samples.add(2 * i);
        let rust = uj.add(1);
        let ok = if i % 2 == 0 {
            measure(run_action, arena, uj) && measure(rust_action, arena, rust)
        } else {
            measure(rust_action, arena, rust) && measure(run_action, arena, uj)
        };
        if !ok {
            return;
        }
    }
    ptr::write_volatile(output.add(1), SAMPLES as u64);
    ptr::write_volatile(output.add(2), ACTIONS as u64);
    ptr::write_volatile(output, MAGIC);
}
