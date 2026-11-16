extern crate std;
use crate::{activation::{Activation,Error,Phase},descriptor::{BootInterface,Kind},xhci::{InterruptPlan,Speed}};
use std::vec::Vec;
const KEYBOARD:&[u8]=include_bytes!("../fixtures/qemu-keyboard.bin");
const MOUSE:&[u8]=include_bytes!("../fixtures/qemu-mouse.bin");

fn composite()->Vec<u8> {
    let mut bytes=KEYBOARD.to_vec();
    let mut mouse=MOUSE[9..].to_vec();
    let mut offset=0;
    while offset<mouse.len() {
        let len=usize::from(mouse[offset]);
        if mouse[offset+1]==4 {mouse[offset+2]=5;}
        if mouse[offset+1]==5 {mouse[offset+2]=0x83;}
        offset+=len;
    }
    bytes.extend(mouse);let len=bytes.len() as u16;
    bytes[2..4].copy_from_slice(&len.to_le_bytes());bytes[4]=2;bytes
}

#[test] fn configuration_protocol_each_interface_then_endpoints() {
    let mut activation=Activation::<2>::new(&composite(),Speed::Full,2,7).unwrap();
    assert_eq!(activation.add_context_flags(),1|(1<<3)|(1<<7));
    assert_eq!(activation.context_entries(),7);
    let expected=[Some([0,9,1,0,0,0,0,0]),Some([0x21,11,0,0,0,0,0,0]),Some([0x21,11,0,0,5,0,0,0]),None];
    for setup in expected {
        let request=activation.submit(100,1000).unwrap();assert_eq!(request.setup,setup);
        assert_ne!(activation.phase(),Phase::Ready);
        assert_eq!(activation.submit(100,1000),Err(Error::Busy));
        activation.complete(request,101,1,0).unwrap();
    }
    assert_eq!(activation.phase(),Phase::Ready);
    assert_eq!(activation.submit(200,100),Err(Error::NotReady));
}

#[test] fn completion_requires_matching_owner_sequence_and_phase() {
    let mut a=Activation::<1>::new(KEYBOARD,Speed::Full,1,1).unwrap();
    let r=a.submit(0,10).unwrap();
    for wrong in [crate::activation::Request{generation:2,..r},crate::activation::Request{slot:2,..r},
        crate::activation::Request{sequence:2,..r},crate::activation::Request{phase:Phase::Endpoints,..r}] {
        assert_eq!(a.complete(wrong,1,1,0),Err(Error::StaleCompletion));
    }
    assert_eq!(a.phase(),Phase::Configuration);
    a.complete(r,1,1,0).unwrap();
    assert_eq!(a.complete(r,2,1,0),Err(Error::StaleCompletion));
}

#[test] fn failure_and_expiry_block_submission_without_dma_reuse() {
    for (time,cc,residual,error) in [(1,6,0,Error::Completion),(1,1,1,Error::Completion),(10,1,0,Error::Expired)] {
        let mut a=Activation::<1>::new(KEYBOARD,Speed::Full,1,1).unwrap();
        let r=a.submit(0,10).unwrap();assert_eq!(a.complete(r,time,cc,residual),Err(error));
        assert_eq!(a.phase(),Phase::Failed);assert_eq!(a.submit(20,10),Err(Error::NotReady));
    }
    let mut a=Activation::<1>::new(KEYBOARD,Speed::Full,1,1).unwrap();
    assert_eq!(a.submit(u64::MAX,1),Err(Error::Deadline));
    assert_eq!(a.submit(0,0),Err(Error::Deadline));
    a.submit(0,10).unwrap();assert!(!a.expire(9));assert!(a.expire(10));assert!(!a.expire(11));
}

#[test] fn usb2_interval_and_dynamic_endpoint_context_fields() {
    let interface=BootInterface{configuration:1,interface:4,kind:Kind::Keyboard,endpoint:0x8f,packet_bytes:8,interval:10};
    let p=InterruptPlan::new(interface,Speed::Low).unwrap();
    assert_eq!((p.dci,p.interval_exponent,p.report_bytes),(31,6,8));
    assert_eq!(p.context_fields(),[6<<16,(8<<16)|0x3e,0,0,(8<<16)|8,0,0,0]);
    for interval in 1..=255 {
        let p=InterruptPlan::new(BootInterface{interval,..interface},Speed::Full).unwrap();
        assert!(1u32<<p.interval_exponent<=u32::from(interval)*8);
        assert!(1u32<<(p.interval_exponent+1)>u32::from(interval)*8);
    }
    for interval in 1..=16 {
        assert_eq!(InterruptPlan::new(BootInterface{interval,..interface},Speed::High).unwrap().interval_exponent,interval-1);
    }
    assert!(InterruptPlan::new(BootInterface{interval:17,..interface},Speed::High).is_err());
    for endpoint in [0,0x80,1,0x91,0xff] {
        assert!(InterruptPlan::new(BootInterface{endpoint,..interface},Speed::Full).is_err());
    }
    assert!(InterruptPlan::new(BootInterface{packet_bytes:64,..interface},Speed::Low).is_err());
    assert!(InterruptPlan::new(BootInterface{interval:0,..interface},Speed::Full).is_err());
}
