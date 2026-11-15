use bmo_x2_usb::{descriptor::Kind, input::{InputService, Payload, Token}};

pub struct Input {
    service: InputService<1, 20>,
    source: Token,
    pending: Option<u8>,
}

impl Default for Input {
    fn default() -> Self {
        let mut service = InputService::default();
        let source = service.bind(Kind::Keyboard).unwrap();
        Self { service, source, pending: None }
    }
}

impl Input {
    pub fn next(&mut self) -> Option<u32> {
        if let Some(byte) = self.pending.take() {
            return Some(u32::from(byte));
        }
        if self.service.pending() == 0 {
            let raw = super::invoke_word(3, 3, 5, 0);
            if matches!(raw, 256 | 257) {
                return None;
            }
            // An empty queue always fits the maximum 20 keyboard changes.
            self.service.report(self.source, &raw.to_le_bytes()).ok()?;
        }
        let event = self.service.poll()?;
        let Payload::Key(change) = event.payload else { return None };
        let byte = change.scancode | if change.pressed { 0 } else { 0x80 };
        if change.extended {
            self.pending = Some(byte);
            Some(0xe0)
        } else {
            Some(u32::from(byte))
        }
    }
}
