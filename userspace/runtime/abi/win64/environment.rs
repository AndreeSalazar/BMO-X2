//! Bounded Win64 process environment for the external single-thread profile.
#![no_std]

use core::cmp::Ordering;
use core::ptr::{addr_of_mut, null_mut};

const CAPACITY: usize = 512;
const SNAPSHOTS: usize = 2;
const ERROR_NOT_ENOUGH_MEMORY: u32 = 8;
const ERROR_INVALID_PARAMETER: u32 = 87;

static mut ENVIRONMENT: [u16; CAPACITY] = [0; CAPACITY];
// Counts through the NUL of the last entry. An extra NUL terminates the block.
static mut USED: usize = 0;
static mut COPIES: [[u16; CAPACITY]; SNAPSHOTS] = [[0; CAPACITY]; SNAPSHOTS];
static mut ACTIVE: [bool; SNAPSHOTS] = [false; SNAPSHOTS];

unsafe extern "win64" {
    fn bmo_set_last_error(error: u32);
}

fn fail(error: u32) -> i32 {
    unsafe { bmo_set_last_error(error) };
    0
}

fn fold_ascii(unit: u16) -> u16 {
    if (u16::from(b'a')..=u16::from(b'z')).contains(&unit) { unit - 32 } else { unit }
}

unsafe fn string_len(data: *const u16) -> Option<usize> {
    (0..CAPACITY).find(|&index| unsafe { data.add(index).read() } == 0)
}

unsafe fn copy_units(target: *mut u16, source: *const u16, len: usize) {
    for index in 0..len {
        unsafe { target.add(index).write_volatile(source.add(index).read()) };
    }
}

#[unsafe(no_mangle)]
pub extern "win64" fn bmo_get_environment_strings_w() -> *mut u16 {
    let active = addr_of_mut!(ACTIVE).cast::<bool>();
    for index in 0..SNAPSHOTS {
        unsafe {
            if !active.add(index).read() {
                let target = addr_of_mut!(COPIES).cast::<u16>().add(index * CAPACITY);
                copy_units(target, addr_of_mut!(ENVIRONMENT).cast::<u16>(), (USED + 1).max(2));
                active.add(index).write(true);
                return target;
            }
        }
    }
    fail(ERROR_NOT_ENOUGH_MEMORY);
    null_mut()
}

#[unsafe(no_mangle)]
pub extern "win64" fn bmo_free_environment_strings_w(block: *mut u16) -> i32 {
    let active = addr_of_mut!(ACTIVE).cast::<bool>();
    for index in 0..SNAPSHOTS {
        unsafe {
            if block == addr_of_mut!(COPIES).cast::<u16>().add(index * CAPACITY) && active.add(index).read() {
                active.add(index).write(false);
                return 1;
            }
        }
    }
    fail(ERROR_INVALID_PARAMETER)
}

#[unsafe(no_mangle)]
pub unsafe extern "win64" fn bmo_set_environment_variable_w(name: *const u16, value: *const u16) -> i32 {
    if name.is_null() {
        return fail(ERROR_INVALID_PARAMETER);
    }
    let Some(name_len) = (unsafe { string_len(name) }) else {
        return fail(ERROR_NOT_ENOUGH_MEMORY);
    };
    if name_len == 0 || (0..name_len).any(|index| {
        let unit = unsafe { name.add(index).read() };
        unit == u16::from(b'=') || unit > 127
    }) {
        return fail(ERROR_INVALID_PARAMETER);
    }
    let value_len = if value.is_null() {
        0
    } else if let Some(len) = unsafe { string_len(value) } {
        len
    } else {
        return fail(ERROR_NOT_ENOUGH_MEMORY);
    };

    let data = addr_of_mut!(ENVIRONMENT).cast::<u16>();
    let used = unsafe { USED };
    let mut start = 0;
    let mut old_size = 0;
    while start < used {
        let entry = unsafe { data.add(start) };
        let old_name_len = (0..used - start)
            .take_while(|&index| unsafe { entry.add(index).read() } != u16::from(b'='))
            .count();
        let compare = (0..old_name_len)
            .map(|index| fold_ascii(unsafe { entry.add(index).read() }))
            .cmp((0..name_len).map(|index| fold_ascii(unsafe { name.add(index).read() })));
        if compare == Ordering::Greater {
            break;
        }
        let entry_size = (old_name_len + 1..used - start)
            .take_while(|&index| unsafe { entry.add(index).read() } != 0)
            .count() + old_name_len + 2;
        if compare == Ordering::Equal {
            old_size = entry_size;
            break;
        }
        start += entry_size;
    }

    let new_size = if value.is_null() { 0 } else { name_len + value_len + 2 };
    let new_used = used - old_size + new_size;
    if new_used >= CAPACITY {
        return fail(ERROR_NOT_ENOUGH_MEMORY);
    }
    unsafe {
        let tail = used - start - old_size;
        let source = data.add(start + old_size);
        let target = data.add(start + new_size);
        if new_size > old_size {
            for index in (0..tail).rev() {
                target.add(index).write_volatile(source.add(index).read());
            }
        } else if new_size < old_size {
            copy_units(target, source, tail);
        }
        if new_size != 0 {
            let entry = data.add(start);
            if old_size == 0 {
                copy_units(entry, name, name_len);
                entry.add(name_len).write(u16::from(b'='));
            }
            copy_units(entry.add(name_len + 1), value, value_len);
            entry.add(new_size - 1).write(0);
        }
        data.add(new_used).write(0);
        if new_used == 0 {
            data.add(1).write(0);
        }
        USED = new_used;
    }
    1
}
