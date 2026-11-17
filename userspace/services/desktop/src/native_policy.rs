//! Native C boundary for the existing DIRECTOR policy. One UI owner/thread.
#![no_std]
#[allow(unused_attributes)]
#[path="lib.rs"] mod model;
pub use model::{Desktop, Workspace};
use model::{Keyboard, KeyEvent, KeyRoute, Surface};
use core::cell::UnsafeCell;
struct Policy { desktop: Desktop<'static,9>, keyboard:Keyboard, modifiers:u8, extended:bool }
impl Policy {
    fn new()->Self {Self{desktop:Desktop::new(),keyboard:Keyboard::default(),modifiers:0,extended:false}}
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
        let mask=match (self.extended,code) {
            (false,0x2a)=>1, (false,0x36)=>2,
            (false,0x1d)=>4, (true,0x1d)=>8,
            (true,0x5b)=>16, (true,0x5c)=>32,
            _=>0,
        };
        self.extended=false;
        if mask!=0 {if pressed {self.modifiers|=mask;}else{self.modifiers&=!mask;}return 1;}
        let before=self.snapshot();
        let modifiers=u8::from(self.modifiers&3!=0) |
            (u8::from(self.modifiers&12!=0)<<1) | (u8::from(self.modifiers&48!=0)<<5);
        let consumed=matches!(self.keyboard.route(&mut self.desktop,KeyEvent{scancode:code,pressed},modifiers),KeyRoute::Consumed);
        u32::from(consumed) | (u32::from(self.snapshot()!=before)<<1)
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
#[cfg(not(any(test,bmo_embedded)))]
#[panic_handler] fn panic(_: &core::panic::PanicInfo<'_>)->! {unsafe{core::arch::asm!("ud2",options(noreturn))}}
#[cfg(test)] mod native_tests {
    use super::*;
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
