//! Win64 code-page services for the UTF-8 process profile.
#![no_std]

use core::ptr::addr_of_mut;

const UTF8: u32 = 65001;
const REPLACEMENT: u32 = 0xfffd;
const MB_ERR_INVALID_CHARS: u32 = 8;
const WC_ERR_INVALID_CHARS: u32 = 0x80;
const ERROR_INVALID_PARAMETER: u32 = 87;
const ERROR_INSUFFICIENT_BUFFER: u32 = 122;
const ERROR_INVALID_FLAGS: u32 = 1004;
const ERROR_NO_UNICODE_TRANSLATION: u32 = 1113;

#[repr(C)]
pub struct CodePageInfo {
    max_char_size: u32,
    default_char: [u8; 2],
    lead_bytes: [u8; 12],
}

unsafe extern "win64" {
    fn bmo_set_last_error(error: u32);
}

fn fail(error: u32) -> i32 {
    unsafe { bmo_set_last_error(error) };
    0
}

fn utf8_page(page: u32) -> bool {
    matches!(page, 0 | 1 | 3 | UTF8)
}

#[unsafe(no_mangle)]
pub extern "win64" fn bmo_get_acp() -> u32 {
    UTF8
}

#[unsafe(no_mangle)]
pub extern "win64" fn bmo_get_oem_cp() -> u32 {
    UTF8
}

#[unsafe(no_mangle)]
pub extern "win64" fn bmo_is_valid_code_page(page: u32) -> i32 {
    i32::from(page == UTF8)
}

#[unsafe(no_mangle)]
pub unsafe extern "win64" fn bmo_get_cp_info(page: u32, info: *mut CodePageInfo) -> i32 {
    if !utf8_page(page) || info.is_null() {
        return fail(ERROR_INVALID_PARAMETER);
    }
    unsafe {
        addr_of_mut!((*info).max_char_size).write_unaligned(4);
        addr_of_mut!((*info).default_char).write([b'?', 0]);
        addr_of_mut!((*info).lead_bytes).write([0; 12]);
    }
    1
}

unsafe fn input_length<T: Copy + PartialEq>(data: *const T, count: i32, nul: T) -> Option<usize> {
    if data.is_null() || count == 0 {
        return None;
    }
    if count > 0 {
        return Some(count as usize);
    }
    for index in 0..i32::MAX as usize {
        if unsafe { data.add(index).read_unaligned() } == nul {
            return Some(index + 1);
        }
    }
    None
}

fn output_valid<S, D>(source: *const S, length: usize, output: *mut D, capacity: i32) -> bool {
    if capacity == 0 {
        return true;
    }
    if capacity < 0 || output.is_null() {
        return false;
    }
    let start = source.addr();
    let out = output.addr();
    let end = start.checked_add(length * core::mem::size_of::<S>());
    let out_end = out.checked_add(capacity as usize * core::mem::size_of::<D>());
    match (end, out_end) {
        (Some(end), Some(out_end)) => out >= end || start >= out_end,
        _ => false,
    }
}

unsafe fn next_utf8(source: *const u8, remaining: usize) -> (u32, usize, bool) {
    let first = unsafe { source.read() };
    let (mut scalar, length, second_min, second_max) = match first {
        0x00..=0x7f => return (u32::from(first), 1, true),
        0xc2..=0xdf => (u32::from(first & 0x1f), 2, 0x80, 0xbf),
        0xe0 => (0, 3, 0xa0, 0xbf),
        0xed => (0xd, 3, 0x80, 0x9f),
        0xe1..=0xef => (u32::from(first & 0xf), 3, 0x80, 0xbf),
        0xf0 => (0, 4, 0x90, 0xbf),
        0xf4 => (4, 4, 0x80, 0x8f),
        0xf1..=0xf3 => (u32::from(first & 7), 4, 0x80, 0xbf),
        _ => return (REPLACEMENT, 1, false),
    };
    for index in 1..length {
        if index == remaining {
            return (REPLACEMENT, index, false);
        }
        let byte = unsafe { source.add(index).read() };
        if !(0x80..=0xbf).contains(&byte) {
            return (REPLACEMENT, index, false);
        }
        if index == 1 && !(second_min..=second_max).contains(&byte) {
            return (REPLACEMENT, 2, false);
        }
        scalar = (scalar << 6) | u32::from(byte & 0x3f);
    }
    (scalar, length, true)
}

#[unsafe(no_mangle)]
pub unsafe extern "win64" fn bmo_multi_byte_to_wide_char(
    page: u32, flags: u32, source: *const u8, count: i32, output: *mut u16, capacity: i32,
) -> i32 {
    if !utf8_page(page) {
        return fail(ERROR_INVALID_PARAMETER);
    }
    if flags & !MB_ERR_INVALID_CHARS != 0 {
        return fail(ERROR_INVALID_FLAGS);
    }
    let Some(length) = (unsafe { input_length(source, count, 0) }) else {
        return fail(ERROR_INVALID_PARAMETER);
    };
    if !output_valid(source, length, output, capacity) {
        return fail(ERROR_INVALID_PARAMETER);
    }

    let (mut read, mut written) = (0, 0);
    while read < length {
        let (scalar, consumed, valid) = unsafe { next_utf8(source.add(read), length - read) };
        if !valid && flags == MB_ERR_INVALID_CHARS {
            return fail(ERROR_NO_UNICODE_TRANSLATION);
        }
        let units = if scalar <= 0xffff { 1 } else { 2 };
        if capacity != 0 {
            if written + units > capacity as usize {
                return fail(ERROR_INSUFFICIENT_BUFFER);
            }
            unsafe {
                if units == 1 {
                    output.add(written).write_unaligned(scalar as u16);
                } else {
                    let pair = scalar - 0x10000;
                    output.add(written).write_unaligned(0xd800 | (pair >> 10) as u16);
                    output.add(written + 1).write_unaligned(0xdc00 | (pair & 0x3ff) as u16);
                }
            }
        }
        read += consumed;
        written += units;
    }
    written as i32
}

unsafe fn next_utf16(source: *const u16, remaining: usize) -> (u32, usize, bool) {
    let first = u32::from(unsafe { source.read_unaligned() });
    if !(0xd800..0xe000).contains(&first) {
        return (first, 1, true);
    }
    if first < 0xdc00 && remaining >= 2 {
        let second = u32::from(unsafe { source.add(1).read_unaligned() });
        if (0xdc00..0xe000).contains(&second) {
            return (0x10000 + ((first - 0xd800) << 10) + second - 0xdc00, 2, true);
        }
    }
    (REPLACEMENT, 1, false)
}

#[unsafe(no_mangle)]
pub unsafe extern "win64" fn bmo_wide_char_to_multi_byte(
    page: u32, flags: u32, source: *const u16, count: i32, output: *mut u8, capacity: i32,
    default_char: *const u8, used_default: *mut i32,
) -> i32 {
    if !utf8_page(page) || !default_char.is_null() || !used_default.is_null() {
        return fail(ERROR_INVALID_PARAMETER);
    }
    if flags & !WC_ERR_INVALID_CHARS != 0 {
        return fail(ERROR_INVALID_FLAGS);
    }
    let Some(length) = (unsafe { input_length(source, count, 0) }) else {
        return fail(ERROR_INVALID_PARAMETER);
    };
    if !output_valid(source, length, output, capacity) {
        return fail(ERROR_INVALID_PARAMETER);
    }

    let (mut read, mut written) = (0, 0);
    while read < length {
        let (scalar, consumed, valid) = unsafe { next_utf16(source.add(read), length - read) };
        if !valid && flags == WC_ERR_INVALID_CHARS {
            return fail(ERROR_NO_UNICODE_TRANSLATION);
        }
        let (bytes, prefix) = match scalar {
            0..=0x7f => (1, 0),
            0x80..=0x7ff => (2, 0xc0),
            0x800..=0xffff => (3, 0xe0),
            _ => (4, 0xf0),
        };
        let next = written + bytes;
        if next > i32::MAX as usize || (capacity != 0 && next > capacity as usize) {
            return fail(ERROR_INSUFFICIENT_BUFFER);
        }
        if capacity != 0 {
            unsafe {
                output.add(written).write(prefix | (scalar >> (6 * (bytes - 1))) as u8);
                for index in 1..bytes {
                    let bits = scalar >> (6 * (bytes - index - 1));
                    output.add(written + index).write(0x80 | (bits & 0x3f) as u8);
                }
            }
        }
        read += consumed;
        written = next;
    }
    written as i32
}
