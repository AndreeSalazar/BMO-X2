//! Match copied xHCI events before advancing activation or delivering reports.
//! This is Ring 3 logic, not an Event Ring MMIO reader or DMA grant.
//! Transport must snapshot a published event coherently, preserve other events,
//! and never reuse a transfer address until quiescence/completion is proven.
use crate::{activation::{Activation,Phase,Request},input::{InputService,Token}};

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum Error {
    Identity, Unrelated, EventData, Completion, Length, AlreadyConsumed,
    Activation(crate::activation::Error), Input(crate::input::Error),
}

#[derive(Clone, Copy)]
pub struct Expected {
    pointer:u64, slot:u8, dci:u8, kind:u8,
}

impl Expected {
    fn new(pointer:u64,slot:u8,dci:u8,kind:u8)->Result<Self,Error> {
        if pointer==0 || pointer&15!=0 || slot==0 || dci>31 {return Err(Error::Identity);}
        Ok(Self{pointer,slot,dci,kind})
    }
    pub fn transfer(pointer:u64,slot:u8,dci:u8)->Result<Self,Error> {
        if dci==0 {return Err(Error::Identity);}
        Self::new(pointer,slot,dci,32)
    }
    pub fn command(pointer:u64,slot:u8)->Result<Self,Error> {Self::new(pointer,slot,0,33)}
    /// None is a not-yet-published cycle. Unrelated belongs to another queue
    /// consumer; it must not be discarded by a single endpoint's caller.
    pub fn inspect(self,event:&[u8;16],cycle:bool)->Result<Option<Status>,Error> {
        let flags=u32::from_le_bytes(event[12..16].try_into().unwrap());
        if (flags&1!=0)!=cycle {return Ok(None);}
        let pointer=u64::from_le_bytes(event[..8].try_into().unwrap());
        if pointer!=self.pointer || flags>>24!=u32::from(self.slot) ||
            (flags>>10)&63!=u32::from(self.kind) || (flags>>16)&255!=u32::from(self.dci) {
            return Err(Error::Unrelated);
        }
        // ED=1 carries an opaque value, not a physical transfer pointer.
        if flags&4!=0 {return Err(Error::EventData);}
        let status=u32::from_le_bytes(event[8..12].try_into().unwrap());
        Ok(Some(Status{code:(status>>24) as u8,residual:status&0xffffff}))
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct Status {pub code:u8,pub residual:u32}

pub struct PendingActivation { request:Request,expected:Expected,consumed:bool }
impl PendingActivation {
    /// Pointer must belong to the authorized transport's submitted command or
    /// control Status Stage. It is not accepted as a grant to arbitrary memory.
    pub fn new(request:Request,pointer:u64)->Result<Self,Error> {
        let expected=match request.phase {
            Phase::Configuration|Phase::Protocol=>Expected::transfer(pointer,request.slot,1)?,
            Phase::Endpoints=>Expected::command(pointer,request.slot)?,
            _=>return Err(Error::Identity),
        };
        Ok(Self{request,expected,consumed:false})
    }
    pub fn complete<const N:usize>(&mut self,activation:&mut Activation<N>,event:&[u8;16],
        cycle:bool,now_us:u64)->Result<bool,Error> {
        if self.consumed {return Err(Error::AlreadyConsumed);}
        let Some(status)=self.expected.inspect(event,cycle)? else{return Ok(false);};
        let result=activation.complete(self.request,now_us,status.code,status.residual);
        // A stale software ticket has not completed the operation in activation.
        if result!=Err(crate::activation::Error::StaleCompletion) {self.consumed=true;}
        result.map_err(Error::Activation)?;Ok(true)
    }
}

pub struct PendingReport {expected:Expected,source:Token,bytes:u8,consumed:bool}
impl PendingReport {
    /// Request exactly one boot report (keyboard 8 B, mouse 3 B).
    pub fn new<const N:usize>(activation:&Activation<N>,endpoint:u8,source:Token,pointer:u64)->Result<Self,Error> {
        if activation.phase()!=Phase::Ready {return Err(Error::Activation(crate::activation::Error::NotReady));}
        let plan=activation.plans().find(|plan|plan.interface.endpoint==endpoint).ok_or(Error::Identity)?;
        Ok(Self{expected:Expected::transfer(pointer,activation.slot(),plan.dci)?,source,
            bytes:plan.report_bytes,consumed:false})
    }
    pub fn deliver<const D:usize,const E:usize>(&mut self,service:&mut InputService<D,E>,
        event:&[u8;16],cycle:bool,report:&[u8])->Result<Option<usize>,Error> {
        if self.consumed {return Err(Error::AlreadyConsumed);}
        let Some(status)=self.expected.inspect(event,cycle)? else{return Ok(None);};
        if !matches!(status.code,1|13) {
            self.consumed=true;return Err(Error::Completion);
        }
        if status.residual!=0 || report.len()!=usize::from(self.bytes) {
            self.consumed=true;return Err(Error::Length);
        }
        match service.report(self.source,report) {
            Ok(count)=>{self.consumed=true;Ok(Some(count))},
            // Keep the copied event/report and ticket until the queue drains.
            Err(crate::input::Error::Backpressure)=>Err(Error::Input(crate::input::Error::Backpressure)),
            Err(error)=>{self.consumed=true;Err(Error::Input(error))},
        }
    }
}
