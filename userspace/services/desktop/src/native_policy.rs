//! Native C boundary for the existing DIRECTOR policy. One UI owner/thread.
#![no_std]
#[allow(unused_attributes)]
#[path="lib.rs"] mod model;
pub use model::{Desktop, Workspace};
use model::{Keyboard, KeyEvent, KeyRoute, Surface};
use core::cell::UnsafeCell;
struct Policy {
    desktop: Desktop<'static,9>, keyboard:Keyboard, modifiers:u8, extended:bool,
    space_down:bool, space_captured:bool,
    locks:u8, locks_down:u8,
}
impl Policy {
    fn new()->Self {Self{desktop:Desktop::new(),keyboard:Keyboard::default(),modifiers:0,extended:false,
        space_down:false,space_captured:false,locks:0,locks_down:0}}
    fn snapshot(&self)->u64 {u64::from(self.desktop.active().number()) | (u64::from(self.desktop.focused().unwrap_or(0))<<8)}
    fn open(&mut self) {
        static PIXEL:[u32;1]=[0];
        // Metadata-only surface: RmlUi owns the actual pixels, never aliased here.
        let current=self.desktop.active();
        if self.desktop.open(1,0,0,Surface::new(1,1,&PIXEL).unwrap()).is_err() {
            for n in 1..=4 {self.desktop.switch(Workspace::new(n).unwrap());if self.desktop.focus(1){self.desktop.move_focused(current);break;}}
            self.desktop.switch(current);self.desktop.focus(1);
        }
    }
    fn key(&mut self,byte:u8)->u32 {
        if byte==0xe0 {self.extended=true;return 1;}
        let code=byte&0x7f;let pressed=byte&0x80==0;
        let extended=core::mem::take(&mut self.extended);
        let mask=match (extended,code) {
            (false,0x2a)=>1, (false,0x36)=>2,
            (false,0x1d)=>4, (true,0x1d)=>8,
            (true,0x5b)=>16, (true,0x5c)=>32,
            (false,0x38)=>64, (true,0x38)=>128,
            _=>0,
        };
        if mask!=0 {if pressed {self.modifiers|=mask;}else{self.modifiers&=!mask;}return 1;}
        let before=self.snapshot();
        let modifiers=u8::from(self.modifiers&3!=0) |
            (u8::from(self.modifiers&12!=0)<<1) | (u8::from(self.modifiers&192!=0)<<2) |
            (u8::from(self.modifiers&48!=0)<<5);
        // Extended navigation shares codes with the keypad, never with shortcuts.
        if extended {return 0;}
        let lock=match code {0x45=>1,0x3a=>2,0x46=>4,_=>0};
        if lock!=0 {
            if !pressed {
                self.locks_down&=!lock;
                return 1;
            }
            if self.locks_down&lock!=0 {return 1;}
            self.locks_down|=lock;
            self.locks^=lock;
            return 9; // Consume the edge and update only the lock indicators.
        }
        if code==0x39 {
            if !pressed {
                self.space_down=false;
                return u32::from(core::mem::take(&mut self.space_captured));
            }
            if self.space_down {return u32::from(self.space_captured);}
            self.space_down=true;
            if modifiers==32 {
                self.space_captured=true;
                self.open();
                return 1 | (u32::from(self.snapshot()!=before)<<1) | 4;
            }
        }
        let consumed=matches!(self.keyboard.route(&mut self.desktop,KeyEvent{scancode:code,pressed},modifiers),KeyRoute::Consumed);
        let focus=consumed && pressed && modifiers==32 && (2..=10).contains(&code) &&
            self.desktop.focused_shortcut()==Some(code-1);
        u32::from(consumed) | (u32::from(self.snapshot()!=before)<<1) | (u32::from(focus)<<2)
    }
}
struct Owner(UnsafeCell<Option<Policy>>);
// Calls are synchronous from the single UI thread; no reference crosses C.
unsafe impl Sync for Owner {}
static OWNER:Owner=Owner(UnsafeCell::new(None));
#[unsafe(no_mangle)] pub extern "C" fn bmo_director_init() {unsafe{*OWNER.0.get()=Some(Policy::new());}}
#[unsafe(no_mangle)] pub extern "C" fn bmo_director_open()->u64 {unsafe{let p=(*OWNER.0.get()).as_mut().unwrap();p.open();p.snapshot()}}
#[unsafe(no_mangle)] pub extern "C" fn bmo_director_key(byte:u32)->u32 {if byte>255{return 1;}unsafe{(*OWNER.0.get()).as_mut().unwrap().key(byte as u8)}}
#[unsafe(no_mangle)] pub extern "C" fn bmo_director_state()->u64 {unsafe{(*OWNER.0.get()).as_ref().unwrap().snapshot()}}
#[unsafe(no_mangle)] pub extern "C" fn bmo_director_locks()->u32 {unsafe{u32::from((*OWNER.0.get()).as_ref().unwrap().locks)}}
#[cfg(not(any(test,bmo_embedded)))]
#[panic_handler] fn panic(_: &core::panic::PanicInfo<'_>)->! {unsafe{core::arch::asm!("ud2",options(noreturn))}}
#[cfg(test)] mod native_tests {
    use super::*;
    #[test] fn lock_keys_toggle_once_and_leave_super_chords_available() {
        let mut p=Policy::new();
        p.open();
        for b in [0x45,0x45,0xc5,0x3a,0xba,0x46,0xc6] {p.key(b);}
        assert_eq!(p.locks,7);
        for b in [0xe0,0x5b,2,0x82,0xe0,0xdb,0x45,0xc5] {p.key(b);}
        assert_eq!(p.snapshot(),0x101);
        assert_eq!(p.locks,6);
    }
    #[test] fn native_super_shortcuts_preserve_space_and_focus_semantics() {
        let mut p=Policy::new();
        p.open();
        for b in [0xe0,0x5b,0x10,0x90] {p.key(b);}
        assert_eq!(p.snapshot(),1);
        assert_eq!(p.key(2),1); // Super+1 never opens a missing slot.
        p.key(0x82);
        assert_eq!(p.key(0x39),7);
        assert_eq!(p.key(0x39),1);
        assert_eq!(p.key(0xb9),1);
        assert_eq!(p.key(2),5);
        p.key(0x82);
        p.key(0x38);
        assert_eq!(p.key(2),0); // Super+Alt+1 is a distinct chord.
        assert_eq!(p.snapshot(),0x101);
    }
    #[test] fn releasing_left_control_keeps_right_control_active() {
        let mut p=Policy::new();
        p.open();
        for b in [0x1d,0xe0,0x1d,0x9d,0xe0,0x5c,3] { p.key(b); }
        assert_eq!(p.snapshot(),2);
        for b in [0x83,0xe0,0x9d,2] { p.key(b); }
        assert_eq!(p.snapshot(),2);
    }
    #[test] fn policy_preserves_window_ownership_and_global_shortcuts() {
        let mut p=Policy::new();p.open();assert_eq!(p.snapshot(),0x101);
        for b in [0xe0,0x5b,0x1d,3] {p.key(b);}
        assert_eq!(p.snapshot(),2);
        for b in [0x83,0x9d,0xe0,0xdb] {p.key(b);}
        p.open();assert_eq!(p.snapshot(),0x102);
        for b in [0xe0,0x5b,0x10] {p.key(b);}
        assert_eq!(p.snapshot(),2);
        for b in [0x90,0xe0,0xdb] {p.key(b);}
        p.open();assert_eq!(p.snapshot(),0x102);
    }
}
