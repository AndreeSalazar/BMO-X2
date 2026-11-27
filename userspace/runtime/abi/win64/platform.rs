//! Platform services exposed by the external Win64 process profile.
#![no_std]

use core::arch::x86_64::{__cpuid, __cpuid_count, _xgetbv};

const COUNTER_FREQUENCY: i64 = 1_000_000_000;
const ERROR_INVALID_PARAMETER: u32 = 87;
const ERROR_GEN_FAILURE: u32 = 31;

#[repr(C)]
struct ResultWords {
    status: i64,
    value: u64,
}

unsafe extern "win64" {
    fn bmo_invoke(cap: u64, op: u64, arg0: u64, arg1: u64, arg2: u64) -> ResultWords;
    fn bmo_set_last_error(error: u32);
}

fn fail(error: u32) -> i32 {
    unsafe { bmo_set_last_error(error) };
    0
}

#[unsafe(no_mangle)]
pub unsafe extern "win64" fn bmo_query_performance_counter(counter: *mut i64) -> i32 {
    if counter.is_null() {
        return fail(ERROR_INVALID_PARAMETER);
    }
    let now = unsafe { bmo_invoke(2, 2, 0, 0, 0) };
    if now.status != 0 || now.value > i64::MAX as u64 {
        return fail(ERROR_GEN_FAILURE);
    }
    unsafe { counter.write_unaligned(now.value as i64) };
    1
}

#[unsafe(no_mangle)]
pub unsafe extern "win64" fn bmo_query_performance_frequency(frequency: *mut i64) -> i32 {
    if frequency.is_null() {
        return fail(ERROR_INVALID_PARAMETER);
    }
    unsafe { frequency.write_unaligned(COUNTER_FREQUENCY) };
    1
}

#[unsafe(no_mangle)]
pub extern "win64" fn bmo_is_debugger_present() -> i32 {
    // This profile has no Win64 debug object or debugger attach mechanism.
    0
}

fn bit(register: u32, index: u32) -> bool {
    register & (1 << index) != 0
}

fn vector_feature(feature: u32, ecx: u32) -> bool {
    const OSXSAVE: u32 = 1 << 27;
    const AVX: u32 = 1 << 28;
    if ecx & (OSXSAVE | AVX) != OSXSAVE | AVX {
        return false;
    }
    // CPUID.OSXSAVE confirms the OS enabled XGETBV for user code.
    let xcr0 = unsafe { _xgetbv(0) };
    if xcr0 & 6 != 6 {
        return false;
    }
    if feature == 39 { // PF_AVX_INSTRUCTIONS_AVAILABLE
        return true;
    }
    if __cpuid(0).eax < 7 {
        return false;
    }
    let leaf = __cpuid_count(7, 0);
    if feature == 40 { // PF_AVX2_INSTRUCTIONS_AVAILABLE
        bit(leaf.ebx, 5)
    } else { // PF_AVX512F_INSTRUCTIONS_AVAILABLE
        xcr0 & 0xe6 == 0xe6 && bit(leaf.ebx, 16)
    }
}

#[unsafe(no_mangle)]
pub extern "win64" fn bmo_is_processor_feature_present(feature: u32) -> i32 {
    let leaf = __cpuid(1);
    let supported = match feature {
        2 => bit(leaf.edx, 8),    // PF_COMPARE_EXCHANGE_DOUBLE
        3 => bit(leaf.edx, 23),   // PF_MMX_INSTRUCTIONS_AVAILABLE
        6 => bit(leaf.edx, 25),   // PF_XMMI_INSTRUCTIONS_AVAILABLE
        9 | 12 => true,          // PAE and NX are required by the supervisor map.
        10 => bit(leaf.edx, 26),  // PF_XMMI64_INSTRUCTIONS_AVAILABLE
        13 => bit(leaf.ecx, 0),   // PF_SSE3_INSTRUCTIONS_AVAILABLE
        14 => bit(leaf.ecx, 13),  // PF_COMPARE_EXCHANGE128
        17 => bit(leaf.ecx, 27),  // PF_XSAVE_ENABLED (OSXSAVE)
        36 => bit(leaf.ecx, 9),   // PF_SSSE3_INSTRUCTIONS_AVAILABLE
        37 => bit(leaf.ecx, 19),  // PF_SSE4_1_INSTRUCTIONS_AVAILABLE
        38 => bit(leaf.ecx, 20),  // PF_SSE4_2_INSTRUCTIONS_AVAILABLE
        39..=41 => vector_feature(feature, leaf.ecx),
        _ => false,
    };
    i32::from(supported)
}
