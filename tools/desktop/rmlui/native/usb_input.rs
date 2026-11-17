//! Single-owner native HID adapter; Ring0 retains MMIO and DMA ownership.
use bmo_x2_usb::{descriptor::Kind,input::{InputService,Payload,Token}};
use core::cell::UnsafeCell;
struct Input {service:InputService<2,40>,keyboard:Option<Token>,mouse:Option<Token>,mode:u32,prefix:Option<u8>}
struct Owner(UnsafeCell<Option<Input>>);
// Only the synchronous UI thread enters this ABI; no reference crosses C.
unsafe impl Sync for Owner {}
static OWNER:Owner=Owner(UnsafeCell::new(None));
#[unsafe(no_mangle)] pub extern "C" fn bmo_usb_init(mode:u32) {
    let mut service=InputService::default();
    let keyboard=if mode!=1 {Some(service.bind(Kind::Keyboard).unwrap())}else{None};
    let mouse=if mode!=0 {Some(service.bind(Kind::Mouse).unwrap())}else{None};
    unsafe{*OWNER.0.get()=Some(Input{service,keyboard,mouse,mode,prefix:None});}
}
#[unsafe(no_mangle)] pub extern "C" fn bmo_usb_report_kind(raw:u64,kind:u32)->u32 {
    let input=unsafe{(*OWNER.0.get()).as_mut().unwrap()};
    let (source,len)=match kind {1=>(input.keyboard,8),2=>(input.mouse,3),_=>return 1};
    let Some(source)=source else{return 1;};
    let bytes=raw.to_le_bytes();
    match input.service.report(source,&bytes[..len]) {Ok(_)=>0,Err(_)=>1}
}
#[unsafe(no_mangle)] pub extern "C" fn bmo_usb_report(raw:u64)->u32 {
    let mode=unsafe{(*OWNER.0.get()).as_ref().unwrap().mode};
    if mode>1 {return 1;}
    bmo_usb_report_kind(raw,if mode==0 {1}else{2})
}
#[unsafe(no_mangle)] pub extern "C" fn bmo_usb_disconnect()->u32 {
    let input=unsafe{(*OWNER.0.get()).as_mut().unwrap()};
    if let Some(token)=input.keyboard {if input.service.detach(token).is_ok(){input.keyboard=None;}}
    if let Some(token)=input.mouse {if input.service.detach(token).is_ok(){input.mouse=None;}}
    u32::from(input.keyboard.is_some() || input.mouse.is_some())
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
        bmo_usb_init(2);
        assert_eq!(bmo_usb_report(0),1);
        assert_eq!(bmo_usb_report_kind(u64::from_le_bytes([8,0,0x14,0,0,0,0,0]),1),0);
        assert_eq!(bmo_usb_report_kind(u64::from_le_bytes([1,2,255,0,0,0,0,0]),2),0);
        assert_eq!([bmo_usb_event(),bmo_usb_event(),bmo_usb_event()],[0xe0,0x5b,0x10]);
        assert_eq!(bmo_usb_event(),1u64<<63|1|2<<8|255<<16);
        assert_eq!(bmo_usb_disconnect(),0);
        assert_eq!([bmo_usb_event(),bmo_usb_event(),bmo_usb_event()],[0x90,0xe0,0xdb]);
        assert_eq!(bmo_usb_event(),256); // Keyboard Detached.
        assert_eq!(bmo_usb_event(),1u64<<63); // Mouse button release.
        assert_eq!(bmo_usb_event(),256); // Mouse Detached.
        assert_eq!(bmo_usb_report_kind(0,1),1);
        assert_eq!(bmo_usb_report_kind(0,2),1);
    }
}
