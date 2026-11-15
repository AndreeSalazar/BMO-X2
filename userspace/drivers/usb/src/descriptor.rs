//! Bounded USB configuration discovery for the Ring 3 boot HID profile.
//! This module neither grants access to hardware nor assumes configuration
//! or SET_PROTOCOL succeeded. Those steps require a transport completion.

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum Kind {
    Keyboard,
    Mouse,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct BootInterface {
    pub configuration: u8,
    pub interface: u8,
    pub kind: Kind,
    pub endpoint: u8,
    pub packet_bytes: u16,
    pub interval: u8,
}

impl BootInterface {
    pub fn configuration_request(self) -> [u8; 8] {
        [0, 9, self.configuration, 0, 0, 0, 0, 0]
    }

    pub fn boot_protocol_request(self) -> [u8; 8] {
        [0x21, 11, 0, 0, self.interface, 0, 0, 0]
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ErrorKind {
    Header,
    Length,
    Interface,
    Hid,
    Endpoint,
    EndpointCount,
    AmbiguousInput,
    ProfileLimit,
    Capacity,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct Error {
    pub kind: ErrorKind,
    pub offset: usize,
}

pub struct Configuration<const N: usize> {
    interfaces: [Option<BootInterface>; N],
    len: usize,
}

struct Interface {
    number: u8,
    alternate: u8,
    expected: u8,
    seen: u8,
    kind: Option<Kind>,
    input: Option<BootInterface>,
    hid: bool,
    offset: usize,
}

fn error(kind: ErrorKind, offset: usize) -> Error {
    Error { kind, offset }
}

impl<const N: usize> Configuration<N> {
    pub fn interfaces(&self) -> impl Iterator<Item = &BootInterface> {
        self.interfaces[..self.len].iter().flatten()
    }

    pub fn parse(bytes: &[u8]) -> Result<Self, Error> {
        if bytes.len() < 9 || bytes[0] != 9 || bytes[1] != 2 || bytes[4] == 0 || bytes[5] == 0 {
            return Err(error(ErrorKind::Header, 0));
        }
        let total = usize::from(u16::from_le_bytes([bytes[2], bytes[3]]));
        if total != bytes.len() || total > 4096 {
            return Err(error(ErrorKind::Length, 2));
        }
        let mut result = Self {
            interfaces: [None; N],
            len: 0,
        };
        let mut current: Option<Interface> = None;
        let mut numbers = [0u8; 32];
        let mut count = 0u16;
        let mut endpoints = 0u32;
        let mut offset = 9;
        while offset < total {
            let tail = &bytes[offset..];
            if tail.len() < 2 || tail[0] < 2 || usize::from(tail[0]) > tail.len() {
                return Err(error(ErrorKind::Length, offset));
            }
            let descriptor = &tail[..usize::from(tail[0])];
            match descriptor[1] {
                2 => return Err(error(ErrorKind::Header, offset)),
                4 => {
                    result.finish(current.take())?;
                    if descriptor.len() != 9 {
                        return Err(error(ErrorKind::Interface, offset));
                    }
                    let number = descriptor[2];
                    if descriptor[3] == 0 {
                        let index = usize::from(number / 8);
                        let mask = 1 << (number % 8);
                        if numbers[index] & mask != 0 {
                            return Err(error(ErrorKind::Interface, offset));
                        }
                        numbers[index] |= mask;
                        count += 1;
                    }
                    let kind = match (descriptor[5], descriptor[6], descriptor[7]) {
                        (3, 1, 1) => Some(Kind::Keyboard),
                        (3, 1, 2) => Some(Kind::Mouse),
                        _ => None,
                    };
                    current = Some(Interface {
                        number,
                        alternate: descriptor[3],
                        expected: descriptor[4],
                        seen: 0,
                        kind,
                        input: None,
                        hid: false,
                        offset,
                    });
                }
                0x21 => {
                    let interface = current
                        .as_mut()
                        .ok_or(error(ErrorKind::Interface, offset))?;
                    if interface.kind.is_some() {
                        if descriptor.len() < 9
                            || interface.hid
                            || descriptor[5] == 0
                            || descriptor.len() != 6 + 3 * usize::from(descriptor[5])
                        {
                            return Err(error(ErrorKind::Hid, offset));
                        }
                        let mut reports = 0;
                        for entry in descriptor[6..].chunks_exact(3) {
                            if entry[0] == 0x22 {
                                if entry[1] == 0 && entry[2] == 0 {
                                    return Err(error(ErrorKind::Hid, offset));
                                }
                                reports += 1;
                            }
                        }
                        if reports != 1 {
                            return Err(error(ErrorKind::Hid, offset));
                        }
                        interface.hid = true;
                    }
                }
                5 => {
                    let interface = current
                        .as_mut()
                        .ok_or(error(ErrorKind::Interface, offset))?;
                    if descriptor.len() < 7 {
                        return Err(error(ErrorKind::Endpoint, offset));
                    }
                    interface.seen = interface
                        .seen
                        .checked_add(1)
                        .ok_or(error(ErrorKind::EndpointCount, offset))?;
                    let address = descriptor[2];
                    if address & 15 == 0 || address & 0x70 != 0 {
                        return Err(error(ErrorKind::Endpoint, offset));
                    }
                    if interface.alternate == 0 {
                        let bit = (address & 15) + if address & 0x80 != 0 { 16 } else { 0 };
                        if endpoints & (1 << bit) != 0 {
                            return Err(error(ErrorKind::Endpoint, offset));
                        }
                        endpoints |= 1 << bit;
                    }
                    if interface.alternate == 0
                        && address & 0x80 != 0
                        && descriptor[3] & 3 == 3
                        && let Some(kind) = interface.kind
                    {
                        if interface.input.is_some() {
                            return Err(error(ErrorKind::AmbiguousInput, offset));
                        }
                        let packet_bytes = u16::from_le_bytes([descriptor[4], descriptor[5]]);
                        let minimum = if kind == Kind::Keyboard { 8 } else { 3 };
                        if !(minimum..=64).contains(&packet_bytes) || descriptor[6] == 0 {
                            return Err(error(ErrorKind::ProfileLimit, offset));
                        }
                        interface.input = Some(BootInterface {
                            configuration: bytes[5],
                            interface: interface.number,
                            kind,
                            endpoint: address,
                            packet_bytes,
                            interval: descriptor[6],
                        });
                    }
                }
                _ => {}
            }
            offset += descriptor.len();
        }
        result.finish(current)?;
        if count != u16::from(bytes[4]) {
            return Err(error(ErrorKind::Interface, 4));
        }
        Ok(result)
    }

    fn finish(&mut self, interface: Option<Interface>) -> Result<(), Error> {
        let Some(interface) = interface else {
            return Ok(());
        };
        if interface.expected != interface.seen {
            return Err(error(ErrorKind::EndpointCount, interface.offset));
        }
        if interface.alternate == 0 && interface.kind.is_some() {
            if !interface.hid {
                return Err(error(ErrorKind::Hid, interface.offset));
            }
            let input = interface
                .input
                .ok_or(error(ErrorKind::Endpoint, interface.offset))?;
            if self.len == N {
                return Err(error(ErrorKind::Capacity, interface.offset));
            }
            self.interfaces[self.len] = Some(input);
            self.len += 1;
        }
        Ok(())
    }
}
