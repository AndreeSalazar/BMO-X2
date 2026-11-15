//! Single-owner Ring 3 input service. Tokens are local bookkeeping, not kernel
//! capabilities. Hardware completions must come from an authorized transport.
use crate::{
    descriptor::Kind,
    hid::{BootKeyboard, BootMouse, KeyChange, MouseMotion, ReportError},
};

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct Token {
    slot: usize,
    generation: u64,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum Payload {
    Key(KeyChange),
    Mouse(MouseMotion),
    Detached,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct Event {
    pub source: Token,
    pub payload: Payload,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum Error {
    Capacity,
    GenerationExhausted,
    StaleSource,
    Backpressure,
    Report(ReportError),
}

#[derive(Clone)]
enum Decoder {
    Keyboard(BootKeyboard),
    Mouse(BootMouse),
}

struct Device {
    token: Token,
    decoder: Decoder,
}

pub struct InputService<const DEVICES: usize, const EVENTS: usize> {
    devices: [Option<Device>; DEVICES],
    queue: [Option<Event>; EVENTS],
    head: usize,
    len: usize,
    generation: u64,
}

impl<const D: usize, const E: usize> Default for InputService<D, E> {
    fn default() -> Self {
        Self {
            devices: [const { None }; D],
            queue: [None; E],
            head: 0,
            len: 0,
            generation: 0,
        }
    }
}

impl<const D: usize, const E: usize> InputService<D, E> {
    pub fn bind(&mut self, kind: Kind) -> Result<Token, Error> {
        let slot = self
            .devices
            .iter()
            .position(Option::is_none)
            .ok_or(Error::Capacity)?;
        let generation = self
            .generation
            .checked_add(1)
            .ok_or(Error::GenerationExhausted)?;
        let token = Token { slot, generation };
        let decoder = match kind {
            Kind::Keyboard => Decoder::Keyboard(BootKeyboard::default()),
            Kind::Mouse => Decoder::Mouse(BootMouse::default()),
        };
        self.devices[slot] = Some(Device { token, decoder });
        self.generation = generation;
        Ok(token)
    }

    pub fn report(&mut self, token: Token, bytes: &[u8]) -> Result<usize, Error> {
        let mut candidate = self.device(token)?.decoder.clone();
        let mut events = [None; 21];
        let mut count = 0;
        let mut emit = |payload| {
            events[count] = Some(payload);
            count += 1;
        };
        match &mut candidate {
            Decoder::Keyboard(keyboard) => keyboard
                .update(bytes, |key| emit(Payload::Key(key)))
                .map_err(Error::Report)?,
            Decoder::Mouse(mouse) => {
                let motion = mouse.update(bytes).map_err(Error::Report)?;
                if motion.dx != 0 || motion.dy != 0 || motion.changed_buttons != 0 {
                    emit(Payload::Mouse(motion));
                }
            }
        }
        if count > E - self.len {
            return Err(Error::Backpressure);
        }
        // Commit decoder and queue together. A rejected report can be retried.
        self.devices[token.slot].as_mut().unwrap().decoder = candidate;
        self.append(token, events);
        Ok(count)
    }

    pub fn detach(&mut self, token: Token) -> Result<usize, Error> {
        let mut decoder = self.device(token)?.decoder.clone();
        let mut events = [None; 21];
        let mut count = 0;
        let mut emit = |payload| {
            events[count] = Some(payload);
            count += 1;
        };
        match &mut decoder {
            Decoder::Keyboard(keyboard) => keyboard.disconnect(|key| emit(Payload::Key(key))),
            Decoder::Mouse(mouse) => {
                let motion = mouse.disconnect();
                if motion.changed_buttons != 0 {
                    emit(Payload::Mouse(motion));
                }
            }
        }
        emit(Payload::Detached);
        let retained = self
            .queue
            .iter()
            .flatten()
            .filter(|event| event.source != token)
            .count();
        if count > E - retained {
            return Err(Error::Backpressure);
        }
        // Discard pending presses from this source before publishing releases.
        let old_len = self.len;
        for _ in 0..old_len {
            let event = self.poll().unwrap();
            if event.source != token {
                self.push(event);
            }
        }
        self.devices[token.slot] = None;
        self.append(token, events);
        Ok(count)
    }

    pub fn poll(&mut self) -> Option<Event> {
        if self.len == 0 {
            return None;
        }
        let event = self.queue[self.head].take();
        self.head = (self.head + 1) % E;
        self.len -= 1;
        event
    }

    pub fn pending(&self) -> usize {
        self.len
    }

    fn device(&self, token: Token) -> Result<&Device, Error> {
        self.devices
            .get(token.slot)
            .and_then(Option::as_ref)
            .filter(|device| device.token == token)
            .ok_or(Error::StaleSource)
    }

    fn append(&mut self, token: Token, events: [Option<Payload>; 21]) {
        for payload in events.into_iter().flatten() {
            self.push(Event { source: token, payload });
        }
    }

    fn push(&mut self, event: Event) {
        let tail = (self.head + self.len) % E;
        self.queue[tail] = Some(event);
        self.len += 1;
    }
}
