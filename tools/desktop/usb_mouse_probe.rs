use bmo_x2_desktop::usb_hid::BootMouse;

#[derive(Default)]
pub struct Input {
    decoder: BootMouse,
    packet: [u8; 3],
    next: usize,
}

impl Input {
    pub fn next(&mut self) -> Option<u32> {
        if self.next == 0 {
            let raw = super::invoke_word(3, 3, 5, 0);
            if raw >> 63 == 0 {
                return None;
            }
            let [buttons, x, y, ..] = raw.to_le_bytes();
            let motion = self.decoder.update(&[buttons, x, y]).ok()?;
            let x = motion.dx as u8;
            let y = -i16::from(motion.dy);
            // Adapt the HID report to the desktop's existing relative input stream.
            let flags = motion.buttons | 8 | ((x >> 7) << 4) | (u8::from(y < 0) << 5);
            self.packet = [flags, x, y as u8];
        }
        let byte = self.packet[self.next];
        self.next = (self.next + 1) % 3;
        Some(512 | u32::from(byte))
    }
}
