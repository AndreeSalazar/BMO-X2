use bmo_x2_desktop::usb_hid::BootKeyboard;

#[derive(Default)]
pub struct Input {
    decoder: BootKeyboard,
    // At most six releases, eight modifier changes and six presses.
    // Extended modifiers add one prefix byte each.
    bytes: [u8; 32],
    next: usize,
    end: usize,
}

impl Input {
    pub fn next(&mut self) -> Option<u32> {
        if self.next == self.end {
            let raw = super::invoke_word(3, 3, 5, 0);
            if matches!(raw, 256 | 257) {
                return None;
            }
            self.next = 0;
            self.end = 0;
            let _ = self.decoder.update(&raw.to_le_bytes(), |change| {
                if change.extended {
                    self.bytes[self.end] = 0xe0;
                    self.end += 1;
                }
                self.bytes[self.end] = change.scancode | if change.pressed { 0 } else { 0x80 };
                self.end += 1;
            });
        }
        if self.next == self.end {
            return None;
        }
        let byte = self.bytes[self.next];
        self.next += 1;
        Some(u32::from(byte))
    }
}
