//! Bounded, process-local Win64 heap for the external SBEF session.
#![no_std]

use core::ptr::{addr_of_mut, null_mut};
use core::sync::atomic::{AtomicBool, Ordering};

const ALIGNMENT: usize = 16;
const CELLS: usize = 4096;
const CAPACITY: usize = CELLS * ALIGNMENT;
const PROCESS_HEAP: usize = 0x424d_4845;
const NO_SERIALIZE: u32 = 1;
const ZERO_MEMORY: u32 = 8;
const IN_PLACE_ONLY: u32 = 16;
const CONTINUATION: u32 = u32::MAX;

#[repr(align(16))]
struct Storage([u8; CAPACITY]);

static LOCKED: AtomicBool = AtomicBool::new(false);
static mut STORAGE: Storage = Storage([0; CAPACITY]);
static mut MARKS: [u32; CELLS] = [0; CELLS];

struct HeapGuard;

impl HeapGuard {
    fn acquire() -> Self {
        while LOCKED.swap(true, Ordering::Acquire) {
            core::hint::spin_loop();
        }
        Self
    }
}

impl Drop for HeapGuard {
    fn drop(&mut self) {
        LOCKED.store(false, Ordering::Release);
    }
}

fn cells(size: usize) -> usize {
    size.div_ceil(ALIGNMENT)
}

fn storage() -> *mut u8 {
    unsafe { addr_of_mut!(STORAGE.0).cast() }
}

fn mark_at(index: usize, _guard: &HeapGuard) -> *mut u32 {
    unsafe { addr_of_mut!(MARKS).cast::<u32>().add(index) }
}

fn find_block(ptr: *mut u8, guard: &HeapGuard) -> Option<(usize, usize)> {
    let offset = (ptr as usize).checked_sub(storage() as usize)?;
    if offset >= CAPACITY || offset % ALIGNMENT != 0 {
        return None;
    }
    let index = offset / ALIGNMENT;
    match unsafe { mark_at(index, guard).read() } {
        0 | CONTINUATION => None,
        size => Some((index, size as usize)),
    }
}

fn reserve(index: usize, size: usize, guard: &HeapGuard) {
    unsafe { mark_at(index, guard).write(size as u32) };
    for next in index + 1..index + cells(size) {
        unsafe { mark_at(next, guard).write_volatile(CONTINUATION) };
    }
}

fn release(from: usize, until: usize, guard: &HeapGuard) {
    for index in from..until {
        unsafe { mark_at(index, guard).write_volatile(0) };
    }
}

fn zero(ptr: *mut u8, from: usize, until: usize) {
    for index in from..until {
        unsafe { ptr.add(index).write_volatile(0) };
    }
}

fn allocate(size: usize, flags: u32, guard: &HeapGuard) -> *mut u8 {
    let need = cells(size);
    let mut consecutive = 0;
    for index in 0..CELLS {
        if unsafe { mark_at(index, guard).read() } == 0 {
            consecutive += 1;
        } else {
            consecutive = 0;
        }
        if consecutive == need {
            let start = index + 1 - need;
            reserve(start, size, guard);
            let ptr = unsafe { storage().add(start * ALIGNMENT) };
            if flags & ZERO_MEMORY != 0 {
                zero(ptr, 0, size);
            }
            return ptr;
        }
    }
    null_mut()
}

#[unsafe(no_mangle)]
pub extern "win64" fn bmo_get_process_heap() -> usize {
    PROCESS_HEAP
}

#[unsafe(no_mangle)]
pub extern "win64" fn bmo_heap_alloc(heap: usize, flags: u32, size: usize) -> *mut u8 {
    if heap != PROCESS_HEAP || flags & !(NO_SERIALIZE | ZERO_MEMORY) != 0 || size > CAPACITY {
        return null_mut();
    }
    allocate(size.max(1), flags, &HeapGuard::acquire())
}

#[unsafe(no_mangle)]
pub extern "win64" fn bmo_heap_free(heap: usize, flags: u32, ptr: *mut u8) -> i32 {
    if heap != PROCESS_HEAP || flags & !NO_SERIALIZE != 0 {
        return 0;
    }
    if ptr.is_null() {
        return 1;
    }
    let guard = HeapGuard::acquire();
    let Some((index, size)) = find_block(ptr, &guard) else {
        return 0;
    };
    release(index, index + cells(size), &guard);
    1
}

#[unsafe(no_mangle)]
pub extern "win64" fn bmo_heap_realloc(
    heap: usize, flags: u32, ptr: *mut u8, size: usize,
) -> *mut u8 {
    if heap != PROCESS_HEAP || flags & !(NO_SERIALIZE | ZERO_MEMORY | IN_PLACE_ONLY) != 0
        || size > CAPACITY
    {
        return null_mut();
    }
    let guard = HeapGuard::acquire();
    let Some((index, old_size)) = find_block(ptr, &guard) else {
        return null_mut();
    };
    let ptr = unsafe { storage().add(index * ALIGNMENT) };
    let size = size.max(1);
    let old_end = index + cells(old_size);
    let new_end = index + cells(size);
    if new_end <= CELLS && (old_end..new_end).all(|cell| unsafe {
        mark_at(cell, &guard).read() == 0
    }) {
        reserve(index, size, &guard);
        release(new_end, old_end, &guard);
        if flags & ZERO_MEMORY != 0 {
            zero(ptr, old_size, size);
        }
        return ptr;
    }
    if flags & IN_PLACE_ONLY != 0 {
        return null_mut();
    }
    let new = allocate(size, flags, &guard);
    if !new.is_null() {
        for byte in 0..old_size {
            unsafe { new.add(byte).write_volatile(ptr.add(byte).read()) };
        }
        release(index, old_end, &guard);
    }
    new
}
