use bmo_x2_usb::{descriptor::Kind, input::{InputService, Payload, Token}};

pub struct Input {
    service: InputService<1, 2>,
    source: Token,
    packet: [u8; 3],
    next: usize,
}

impl Default for Input {
    fn default() -> Self {
        let mut service = InputService::default();
        let source = service.bind(Kind::Mouse).unwrap();
        Self { service, source, packet: [0; 3], next: 0 }
    }
}

impl Input {
    pub fn next(&mut self) -> Option<u32> {
        if self.next == 0 {
            let raw = super::invoke_word(3, 3, 5, 0);
            if raw >> 63 == 0 {
                return None;
            }
            let [buttons, x, y, ..] = raw.to_le_bytes();
            self.service.report(self.source, &[buttons, x, y]).ok()?;
            let event = self.service.poll()?;
            let Payload::Mouse(motion) = event.payload else { return None };
            let x = motion.dx as u8;
            let y = -i16::from(motion.dy);
            let flags = motion.buttons | 8 | ((x >> 7) << 4) | (u8::from(y < 0) << 5);
            self.packet = [flags, x, y as u8];
        }
        let byte = self.packet[self.next];
        self.next = (self.next + 1) % 3;
        Some(512 | u32::from(byte))
    }
}
