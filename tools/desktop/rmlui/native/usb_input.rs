//! Native UI adapter for the existing bounded, supervisor-mediated USB probe.
//! No device MMIO or DMA pointer crosses into this Ring 3 application.
use bmo_x2_usb::{descriptor::Kind,input::{InputService,Payload,Token}};
use core::cell::UnsafeCell;
struct Input {service:InputService<1,20>,source:Token,kind:Kind,prefix:Option<u8>}
struct Owner(UnsafeCell<Option<Input>>);
// The native UI has one synchronous input owner; C receives only scalar values.
unsafe impl Sync for Owner {}
static OWNER:Owner=Owner(UnsafeCell::new(None));
#[unsafe(no_mangle)] pub extern "C" fn bmo_usb_init(mouse:u32) {
    let kind=if mouse==0 {Kind::Keyboard}else{Kind::Mouse};
    let mut service=InputService::default();let source=service.bind(kind).unwrap();
    unsafe{*OWNER.0.get()=Some(Input{service,source,kind,prefix:None});}
}
#[unsafe(no_mangle)] pub extern "C" fn bmo_usb_report(raw:u64)->u32 {
    let input=unsafe{(*OWNER.0.get()).as_mut().unwrap()};
    let bytes=raw.to_le_bytes();
    let bytes=if input.kind==Kind::Mouse {&bytes[..3]}else{&bytes[..]};
    match input.service.report(input.source,bytes) {Ok(_)=>0,Err(_)=>1}
}
#[unsafe(no_mangle)] pub extern "C" fn bmo_usb_event()->u64 {
    let input=unsafe{(*OWNER.0.get()).as_mut().unwrap()};
    if let Some(byte)=input.prefix.take(){return u64::from(byte);}
    match input.service.poll().map(|event|event.payload) {
        Some(Payload::Key(key))=>{
            let byte=key.scancode | if key.pressed {0}else{0x80};
            if key.extended {input.prefix=Some(byte);0xe0}else{u64::from(byte)}
        },
        Some(Payload::Mouse(mouse))=>1u64<<63 | u64::from(mouse.buttons) |
            (u64::from(mouse.dx as u8)<<8) | (u64::from(mouse.dy as u8)<<16),
        _=>256,
    }
}

#[cfg(test)] mod tests {
    use super::*;
    #[test] fn scalar_adapter_keeps_prefix_release_and_signed_mouse_motion() {
        bmo_usb_init(0);assert_eq!(bmo_usb_event(),256);
        assert_eq!(bmo_usb_report(u64::from_le_bytes([8,0,0x14,0,0,0,0,0])),0);
        assert_eq!([bmo_usb_event(),bmo_usb_event(),bmo_usb_event()],[0xe0,0x5b,0x10]);
        assert_eq!(bmo_usb_event(),256);
        assert_eq!(bmo_usb_report(0),0);
        assert_eq!([bmo_usb_event(),bmo_usb_event(),bmo_usb_event()],[0x90,0xe0,0xdb]);
        assert_eq!(bmo_usb_report(u64::from_le_bytes([0,0,1,0,0,0,0,0])),1);
        assert_eq!(bmo_usb_event(),256);
        bmo_usb_init(1);
        assert_eq!(bmo_usb_report(u64::from_le_bytes([1,2,255,0,0,0,0,0])),0);
        assert_eq!(bmo_usb_event(),1u64<<63|1|2<<8|255<<16);
        assert_eq!(bmo_usb_event(),256);
        assert_eq!(bmo_usb_report(0),0);assert_eq!(bmo_usb_event(),1u64<<63);
        assert_eq!(bmo_usb_report(0),0);assert_eq!(bmo_usb_event(),256);
    }
}
