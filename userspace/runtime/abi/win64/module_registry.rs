//! Lookup of the main executable and the resident Kernel32 provider.
#![no_std]

use core::ptr::{addr_of, null};
use core::sync::atomic::{AtomicU32, Ordering::Relaxed};

const IMAGE_PATH: &[u8] = include_bytes!(env!("BMO_WIN64_IMAGE_PATH"));
const KERNEL32_PATH: &[u8] = include_bytes!(env!("BMO_WIN64_KERNEL32_PATH"));
const ERROR_INVALID_HANDLE: u32 = 6;
const ERROR_INVALID_PARAMETER: u32 = 87;
const ERROR_INSUFFICIENT_BUFFER: u32 = 122;
const ERROR_MOD_NOT_FOUND: u32 = 126;
const ERROR_PROC_NOT_FOUND: u32 = 127;
const ERROR_TOO_MANY_MODULES: u32 = 214;
const PIN: u32 = 1;
const UNCHANGED_REFCOUNT: u32 = 2;
const FROM_ADDRESS: u32 = 4;
const SEARCH_SYSTEM32: u32 = 0x800;
const PINNED: u32 = u32::MAX;

static IMAGE_REFS: AtomicU32 = AtomicU32::new(0);
static KERNEL32_REFS: AtomicU32 = AtomicU32::new(0);

#[derive(Clone, Copy, PartialEq, Eq)]
enum Module {
    Image,
    Kernel32,
}

impl Module {
    fn handle(self) -> usize {
        match self {
            Self::Image => bmo_win64_start as *const () as usize,
            Self::Kernel32 => addr_of!(bmo_win64_exports).addr(),
        }
    }

    fn path(self) -> &'static [u8] {
        match self {
            Self::Image => IMAGE_PATH,
            Self::Kernel32 => KERNEL32_PATH,
        }
    }

    fn references(self) -> &'static AtomicU32 {
        match self {
            Self::Image => &IMAGE_REFS,
            Self::Kernel32 => &KERNEL32_REFS,
        }
    }
}

#[repr(C)]
struct Export {
    name: *const u8,
    target: *const (),
}

unsafe extern "win64" {
    fn bmo_win64_start();
    fn bmo_set_last_error(error: u32);
    static bmo_win64_exports: Export;
    static bmo_win64_exports_end: Export;
}

fn fail(error: u32) {
    unsafe { bmo_set_last_error(error) };
}

fn from_handle(handle: usize) -> Option<Module> {
    [Module::Image, Module::Kernel32].into_iter().find(|module| module.handle() == handle)
}

fn exports() -> impl Iterator<Item = *const Export> {
    let start = addr_of!(bmo_win64_exports);
    let bytes = addr_of!(bmo_win64_exports_end).addr() - start.addr();
    (0..bytes / core::mem::size_of::<Export>()).map(move |index| start.wrapping_add(index))
}

fn from_address(address: usize) -> Option<Module> {
    // The fixture registers entry points. A general image mapper will supply module ranges.
    from_handle(address).or_else(|| {
        exports().any(|entry| unsafe { (*entry).target.addr() } == address).then_some(Module::Kernel32)
    })
}

fn fold_ascii(value: u16) -> u16 {
    if (65..=90).contains(&value) { value + 32 } else { value }
}

unsafe fn matches_wide(name: *const u16, expected: impl Iterator<Item = u16>) -> bool {
    for (index, unit) in expected.enumerate() {
        if fold_ascii(unsafe { name.add(index).read_unaligned() }) != fold_ascii(unit) {
            return false;
        }
    }
    true
}

unsafe fn by_name(name: *const u16) -> Option<Module> {
    if name.is_null() {
        return Some(Module::Image);
    }
    for module in [Module::Image, Module::Kernel32] {
        let units = module.path().chunks_exact(2).map(|pair| u16::from_le_bytes([pair[0], pair[1]]));
        let basename = units.clone().rposition(|unit| unit == u16::from(b'\\')).map_or(0, |i| i + 1);
        if unsafe { matches_wide(name, units.clone()) || matches_wide(name, units.skip(basename)) } {
            return Some(module);
        }
    }
    unsafe { matches_wide(name, "kernel32\0".bytes().map(u16::from)) }.then_some(Module::Kernel32)
}

fn acquire(module: Module, flags: u32) -> bool {
    let refs = module.references();
    let current = refs.load(Relaxed);
    if current == PINNED || flags & UNCHANGED_REFCOUNT != 0 {
        return true;
    }
    if flags & PIN != 0 {
        refs.store(PINNED, Relaxed);
        return true;
    }
    if current == PINNED - 1 {
        fail(ERROR_TOO_MANY_MODULES);
        return false;
    }
    refs.store(current + 1, Relaxed);
    true
}

#[unsafe(no_mangle)]
pub unsafe extern "win64" fn bmo_get_module_handle_w(name: *const u16) -> usize {
    if let Some(module) = unsafe { by_name(name) } {
        module.handle()
    } else {
        fail(ERROR_MOD_NOT_FOUND);
        0
    }
}

#[unsafe(no_mangle)]
pub unsafe extern "win64" fn bmo_get_module_handle_ex_w(
    flags: u32, argument: *const u16, output: *mut usize,
) -> i32 {
    if output.is_null() {
        fail(ERROR_INVALID_PARAMETER);
        return 0;
    }
    unsafe { output.write_unaligned(0) };
    if flags & !(PIN | UNCHANGED_REFCOUNT | FROM_ADDRESS) != 0
        || flags & (PIN | UNCHANGED_REFCOUNT) == PIN | UNCHANGED_REFCOUNT
        || (flags & FROM_ADDRESS != 0 && argument.is_null())
    {
        fail(ERROR_INVALID_PARAMETER);
        return 0;
    }
    let module = if flags & FROM_ADDRESS != 0 {
        from_address(argument.addr())
    } else {
        unsafe { by_name(argument) }
    };
    let Some(module) = module else {
        fail(ERROR_MOD_NOT_FOUND);
        return 0;
    };
    if !acquire(module, flags) {
        return 0;
    }
    unsafe { output.write_unaligned(module.handle()) };
    1
}

#[unsafe(no_mangle)]
pub unsafe extern "win64" fn bmo_load_library_ex_w(name: *const u16, file: usize, flags: u32) -> usize {
    if name.is_null() || file != 0 || !matches!(flags, 0 | SEARCH_SYSTEM32) {
        fail(ERROR_INVALID_PARAMETER);
        return 0;
    }
    let Some(Module::Kernel32) = (unsafe { by_name(name) }) else {
        fail(ERROR_MOD_NOT_FOUND);
        return 0;
    };
    if acquire(Module::Kernel32, 0) { Module::Kernel32.handle() } else { 0 }
}

#[unsafe(no_mangle)]
pub extern "win64" fn bmo_free_library(handle: usize) -> i32 {
    if let Some(module) = from_handle(handle) {
        let refs = module.references();
        match refs.load(Relaxed) {
            PINNED => return 1,
            0 => (),
            count => {
                refs.store(count - 1, Relaxed);
                return 1;
            }
        }
    }
    fail(ERROR_INVALID_HANDLE);
    0
}

unsafe fn export_name_equals(actual: *const u8, expected: *const u8) -> bool {
    let mut index = 0;
    loop {
        let unit = unsafe { expected.add(index).read() };
        if unsafe { actual.add(index).read() } != unit {
            return false;
        }
        if unit == 0 {
            return true;
        }
        index += 1;
    }
}

#[unsafe(no_mangle)]
pub unsafe extern "win64" fn bmo_get_proc_address(handle: usize, name: *const u8) -> *const () {
    let Some(module) = from_handle(handle) else {
        fail(ERROR_INVALID_HANDLE);
        return null();
    };
    if module == Module::Kernel32 && name.addr() > u16::MAX as usize {
        for entry in exports() {
            unsafe {
                if export_name_equals(name, (*entry).name) {
                    return (*entry).target;
                }
            }
        }
    }
    fail(ERROR_PROC_NOT_FOUND);
    null()
}

#[unsafe(no_mangle)]
pub unsafe extern "win64" fn bmo_get_module_file_name_w(
    handle: usize, filename: *mut u16, capacity: u32,
) -> u32 {
    let module = if handle == 0 { Some(Module::Image) } else { from_handle(handle) };
    let Some(module) = module else {
        fail(ERROR_MOD_NOT_FOUND);
        return 0;
    };
    if capacity == 0 {
        fail(ERROR_INSUFFICIENT_BUFFER);
        return 0;
    }
    if filename.is_null() {
        fail(ERROR_INVALID_PARAMETER);
        return 0;
    }
    let path = module.path();
    let units = (path.len() / 2 - 1) as u32;
    let copied = units.min(capacity - 1);
    for index in 0..copied as usize {
        unsafe {
            // Keep this copy independent of the CRT that calls it during startup.
            let bytes = path.as_ptr().add(index * 2);
            let unit = u16::from_le_bytes([bytes.read_volatile(), bytes.add(1).read_volatile()]);
            filename.add(index).write_unaligned(unit);
        }
    }
    unsafe { filename.add(copied as usize).write_unaligned(0) };
    if copied != units {
        fail(ERROR_INSUFFICIENT_BUFFER);
        return capacity;
    }
    copied
}
