//! PC and unwind-table lookups for the fixed Win64 process image.
#![no_std]

use core::ptr::{addr_of, null};

#[repr(C)]
pub struct RuntimeFunction {
    begin: u32,
    end: u32,
    unwind: u32,
}

#[repr(C)]
struct ImageRange {
    start: u64,
    end: u64,
}

#[repr(C)]
struct ImageMetadata {
    base: u64,
    functions: *const RuntimeFunction,
    function_count: u64,
    ranges: [ImageRange; 3],
}

const _: () = assert!(core::mem::size_of::<ImageMetadata>() == 72);

unsafe extern "C" {
    static bmo_win64_function_table: ImageMetadata;
}

#[unsafe(no_mangle)]
pub extern "win64" fn bmo_win64_image_base() -> usize {
    unsafe { (*addr_of!(bmo_win64_function_table)).base as usize }
}

#[unsafe(no_mangle)]
pub unsafe extern "win64" fn bmo_rtl_pc_to_file_header(pc: u64, image_base: *mut u64) -> u64 {
    let image = unsafe { &*addr_of!(bmo_win64_function_table) };
    let found = image.ranges.iter().any(|range| (range.start..range.end).contains(&pc));
    let result = if found { image.base } else { 0 };
    if !image_base.is_null() {
        unsafe { image_base.write_unaligned(result) };
    }
    result
}

#[unsafe(no_mangle)]
pub unsafe extern "win64" fn bmo_rtl_lookup_function_entry(
    pc: u64, image_base: *mut u64, _history_table: usize,
) -> *const RuntimeFunction {
    let image = unsafe { &*addr_of!(bmo_win64_function_table) };
    let Some(relative_pc) = pc.checked_sub(image.base).and_then(|rva| u32::try_from(rva).ok()) else {
        return null();
    };
    let (mut low, mut high) = (0, image.function_count as usize);
    while low < high {
        let middle = low + (high - low) / 2;
        let entry = image.functions.wrapping_add(middle);
        let function = unsafe { &*entry };
        if relative_pc < function.begin {
            high = middle;
        } else if relative_pc >= function.end {
            low = middle + 1;
        } else {
            if !image_base.is_null() {
                unsafe { image_base.write_unaligned(image.base) };
            }
            return entry;
        }
    }
    null()
}
