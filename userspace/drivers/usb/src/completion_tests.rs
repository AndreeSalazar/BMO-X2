use crate::{activation::{Activation,Phase},completion::{Error,Expected,PendingActivation,PendingReport},
    descriptor::Kind,input::{InputService,Payload},xhci::Speed};
const KEYBOARD:&[u8]=include_bytes!("../fixtures/qemu-keyboard.bin");
const MOUSE:&[u8]=include_bytes!("../fixtures/qemu-mouse.bin");
fn event(ptr:u64,slot:u8,dci:u8,kind:u8,cc:u8,residual:u32)->[u8;16] {
    let mut e=[0;16];e[..8].copy_from_slice(&ptr.to_le_bytes());
    e[8..12].copy_from_slice(&(u32::from(cc)<<24|residual).to_le_bytes());
    e[12..].copy_from_slice(&(u32::from(slot)<<24|u32::from(dci)<<16|u32::from(kind)<<10|1).to_le_bytes());e
}
fn ready(kind:Kind,endpoint:u8,slot:u8)->Activation<1> {
    let source=if kind==Kind::Keyboard {KEYBOARD}else{MOUSE};
    let mut bytes=[0;128];bytes[..source.len()].copy_from_slice(source);let mut at=9;
    while at<source.len() {if bytes[at+1]==5 {bytes[at+2]=endpoint;}at+=usize::from(bytes[at]);}
    let mut a=Activation::<1>::new(&bytes[..source.len()],Speed::Full,slot,1).unwrap();
    while a.phase()!=Phase::Ready {let r=a.submit(0,100).unwrap();a.complete(r,1,1,0).unwrap();}a
}
#[test] fn event_cycle_pointer_slot_endpoint_type_and_ed_are_checked() {
    assert!(Expected::transfer(3,1,3).is_err());assert!(Expected::transfer(16,0,3).is_err());
    let x=Expected::transfer(0x1000,2,7).unwrap();let e=event(0x1000,2,7,32,1,0);
    assert_eq!(x.inspect(&e,false),Ok(None));assert_eq!(x.inspect(&e,true).unwrap().unwrap().code,1);
    for wrong in [event(0x1010,2,7,32,1,0),event(0x1000,3,7,32,1,0),event(0x1000,2,3,32,1,0),event(0x1000,2,7,34,1,0)] {
        assert_eq!(x.inspect(&wrong,true),Err(Error::Unrelated));
    }
    let mut data=e;data[12]|=4;assert_eq!(x.inspect(&data,true),Err(Error::EventData));
}
#[test] fn hardware_completion_advances_only_the_pending_activation_once() {
    let mut a=Activation::<1>::new(KEYBOARD,Speed::Full,2,10).unwrap();
    for expected in [Phase::Protocol,Phase::Endpoints,Phase::Ready] {
        let r=a.submit(0,100).unwrap();let mut pending=PendingActivation::new(r,0x1000).unwrap();
        let (kind,dci)=if r.phase==Phase::Endpoints {(33,0)}else{(32,1)};
        let e=event(0x1000,2,dci,kind,1,0);
        assert!(!pending.complete(&mut a,&e,false,1).unwrap());
        assert!(pending.complete(&mut a,&e,true,1).unwrap());assert_eq!(a.phase(),expected);
        assert_eq!(pending.complete(&mut a,&e,true,1),Err(Error::AlreadyConsumed));
    }
}
#[test] fn simultaneous_sources_and_backpressure_preserve_report_until_retry() {
    let mut service=InputService::<2,1>::default();let key=service.bind(Kind::Keyboard).unwrap();let mouse=service.bind(Kind::Mouse).unwrap();
    let ke=event(0x1000,1,3,32,1,0);let me=event(0x2000,2,7,32,13,0);
    let mut k=PendingReport::new(&ready(Kind::Keyboard,0x81,1),0x81,key,0x1000).unwrap();
    let mut m=PendingReport::new(&ready(Kind::Mouse,0x83,2),0x83,mouse,0x2000).unwrap();
    assert_eq!(k.deliver(&mut service,&me,true,&[0;8]),Err(Error::Unrelated));
    assert_eq!(k.deliver(&mut service,&ke,true,&[0,0,4,0,0,0,0,0]),Ok(Some(1)));
    assert_eq!(m.deliver(&mut service,&me,true,&[1,2,255]),Err(Error::Input(crate::input::Error::Backpressure)));
    assert!(matches!(service.poll().unwrap().payload,Payload::Key(_)));
    assert_eq!(m.deliver(&mut service,&me,true,&[1,2,255]),Ok(Some(1)));
    let Payload::Mouse(motion)=service.poll().unwrap().payload else{panic!()};assert_eq!((motion.dx,motion.dy,motion.buttons),(2,-1,1));
    assert_eq!(m.deliver(&mut service,&me,true,&[1,2,255]),Err(Error::AlreadyConsumed));
}
#[test] fn failed_short_or_stale_reports_never_publish_input() {
    for (cc,residual,len,error) in [(6,0,8,Error::Completion),(1,1,8,Error::Length),(1,0,7,Error::Length)] {
        let mut service=InputService::<1,20>::default();let token=service.bind(Kind::Keyboard).unwrap();
        let mut pending=PendingReport::new(&ready(Kind::Keyboard,0x81,1),0x81,token,0x1000).unwrap();
        assert_eq!(pending.deliver(&mut service,&event(0x1000,1,3,32,cc,residual),true,&[0;8][..len]),Err(error));
        assert_eq!(service.pending(),0);
    }
    let mut service=InputService::<1,20>::default();let token=service.bind(Kind::Keyboard).unwrap();
    let mut pending=PendingReport::new(&ready(Kind::Keyboard,0x81,1),0x81,token,0x1000).unwrap();
    service.detach(token).unwrap();while service.poll().is_some(){}
    let _new=service.bind(Kind::Keyboard).unwrap();
    assert_eq!(pending.deliver(&mut service,&event(0x1000,1,3,32,1,0),true,&[0;8]),Err(Error::Input(crate::input::Error::StaleSource)));
    assert_eq!(service.pending(),0);
}

#[test] fn reports_require_confirmed_activation_and_discovered_endpoint() {
    let mut service=InputService::<1,20>::default();let token=service.bind(Kind::Keyboard).unwrap();
    let a=Activation::<1>::new(KEYBOARD,Speed::Full,1,1).unwrap();
    assert!(matches!(PendingReport::new(&a,0x81,token,0x1000),Err(Error::Activation(crate::activation::Error::NotReady))));
    assert!(matches!(PendingReport::new(&ready(Kind::Keyboard,0x81,1),0x82,token,0x1000),Err(Error::Identity)));
}
