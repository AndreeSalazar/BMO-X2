//! USB2 interrupt-IN endpoint admission. No MMIO, pointers or DMA grants.
//! xHCI 1.2, sections 6.2.3 and 6.2.3.6. Root ports only in this profile.
use crate::descriptor::{BootInterface, Kind};

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum Speed { Low, Full, High }

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum Error { Address, Packet, Interval }

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct InterruptPlan {
    pub interface: BootInterface,
    pub dci: u8,
    pub interval_exponent: u8,
    pub report_bytes: u8,
}

impl InterruptPlan {
    pub fn new(interface: BootInterface, speed: Speed) -> Result<Self, Error> {
        if interface.endpoint & 0xf0 != 0x80 || interface.endpoint & 15 == 0 {
            return Err(Error::Address);
        }
        let report_bytes = match interface.kind { Kind::Keyboard => 8, Kind::Mouse => 3 };
        let max = if speed == Speed::Low { 8 } else { 64 };
        if interface.packet_bytes < u16::from(report_bytes) || interface.packet_bytes > max {
            return Err(Error::Packet);
        }
        if interface.interval == 0 { return Err(Error::Interval); }
        let interval_exponent = if speed == Speed::High {
            if interface.interval > 16 { return Err(Error::Interval); }
            interface.interval - 1
        } else {
            (7 - interface.interval.leading_zeros() as u8) + 3
        };
        Ok(Self { interface, dci: (interface.endpoint & 15)*2+1,
                  interval_exponent, report_bytes })
    }

    /// Dequeue address/cycle are deliberately zero. Only an authorized transport
    /// may fill them from its own reserved transfer ring before submission.
    pub fn context_fields(self) -> [u32; 8] {
        [u32::from(self.interval_exponent)<<16,
         u32::from(self.interface.packet_bytes)<<16 | 0x3e, 0, 0,
         u32::from(self.interface.packet_bytes)<<16 | u32::from(self.report_bytes),
         0, 0, 0]
    }
}
