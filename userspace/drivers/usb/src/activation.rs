//! Single-owner Ring 3 HID activation. A request is not a completion.
//! Transport must supply authorized device ownership and matched completions.
//! This module alone does not program a controller or grant DMA access.
use crate::descriptor::{Configuration, Error as DescriptorError};
use crate::xhci::{InterruptPlan, Speed};

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum Phase { Configuration, Protocol, Endpoints, Ready, Failed }

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum Error { Descriptor(DescriptorError), Endpoint(crate::xhci::Error), Empty,
    Identity, Deadline, Busy, StaleCompletion, Completion, Expired, NotReady }

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct Request {
    pub generation: u64,
    pub sequence: u32,
    pub slot: u8,
    pub phase: Phase,
    /// None means Configure Endpoint, using the validated plans and mask.
    pub setup: Option<[u8;8]>,
}

pub struct Activation<const N: usize> {
    plans: [Option<InterruptPlan>;N],
    len: usize,
    protocol: usize,
    slot: u8,
    generation: u64,
    sequence: u32,
    phase: Phase,
    pending: Option<(Request,u64)>,
}

impl<const N: usize> Activation<N> {
    pub fn new(bytes: &[u8], speed: Speed, slot: u8, generation: u64) -> Result<Self,Error> {
        if slot == 0 || generation == 0 {return Err(Error::Identity);}
        let config=Configuration::<N>::parse(bytes).map_err(Error::Descriptor)?;
        let mut plans=[None;N]; let mut len=0;
        for interface in config.interfaces() {
            plans[len]=Some(InterruptPlan::new(*interface,speed).map_err(Error::Endpoint)?);
            len+=1;
        }
        if len==0 {return Err(Error::Empty);}
        Ok(Self {plans,len,protocol:0,slot,generation,sequence:0,
            phase:Phase::Configuration,pending:None})
    }
    pub fn phase(&self)->Phase {self.phase}
    pub fn plans(&self)->impl Iterator<Item=&InterruptPlan> {
        self.plans[..self.len].iter().flatten()
    }
    /// Slot context plus each discovered endpoint; never assume endpoint 0x81.
    pub fn add_context_flags(&self)->u32 {
        self.plans().fold(1,|mask,plan|mask | (1u32<<plan.dci))
    }
    pub fn context_entries(&self)->u8 {
        self.plans().map(|p|p.dci).max().unwrap_or(1)
    }
    pub fn submit(&mut self, now_us:u64, timeout_us:u64)->Result<Request,Error> {
        if self.pending.is_some(){return Err(Error::Busy);}
        if matches!(self.phase,Phase::Ready|Phase::Failed){return Err(Error::NotReady);}
        if timeout_us==0{return Err(Error::Deadline);}
        let deadline=now_us.checked_add(timeout_us).ok_or(Error::Deadline)?;
        let setup=match self.phase {
            Phase::Configuration=>Some(self.plans[0].unwrap().interface.configuration_request()),
            Phase::Protocol=>Some(self.plans[self.protocol].unwrap().interface.boot_protocol_request()),
            Phase::Endpoints=>None,
            _=>return Err(Error::NotReady),
        };
        self.sequence=self.sequence.checked_add(1).ok_or(Error::Identity)?;
        let request=Request{generation:self.generation,sequence:self.sequence,slot:self.slot,phase:self.phase,setup};
        self.pending=Some((request,deadline)); Ok(request)
    }
    /// CC=1 and zero residual are required for these no-data operations.
    /// The transport must first match event TRB pointer, slot and endpoint.
    pub fn complete(&mut self,request:Request,now_us:u64,cc:u8,residual:u32)->Result<(),Error> {
        let Some((expected,deadline))=self.pending else{return Err(Error::StaleCompletion);};
        if request!=expected{return Err(Error::StaleCompletion);}
        if now_us>=deadline {self.phase=Phase::Failed;self.pending=None;return Err(Error::Expired);}
        if cc!=1 || residual!=0 {self.phase=Phase::Failed;self.pending=None;return Err(Error::Completion);}
        self.pending=None;
        self.phase=match self.phase {
            Phase::Configuration=>Phase::Protocol,
            Phase::Protocol=>{self.protocol+=1;if self.protocol==self.len {Phase::Endpoints}else{Phase::Protocol}},
            Phase::Endpoints=>Phase::Ready,
            _=>return Err(Error::NotReady),
        }; Ok(())
    }
    /// Expiry blocks further submission; it does not free or reuse transport DMA.
    /// Quiescence/revocation must be confirmed separately by the owner.
    pub fn expire(&mut self,now_us:u64)->bool {
        if self.pending.is_some_and(|(_,deadline)|now_us>=deadline) {
            self.pending=None;self.phase=Phase::Failed;true
        } else {false}
    }
}
