//! Decode USB HID boot reports after the transport has selected boot protocol.

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ReportError {
    Length,
    KeyboardStatus,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct KeyChange {
    pub scancode: u8,
    pub extended: bool,
    pub pressed: bool,
    /// USB modifier byte after applying this change.
    pub modifiers: u8,
}

#[derive(Clone, Default)]
pub struct BootKeyboard {
    modifiers: u8,
    keys: [u8; 6],
}

impl BootKeyboard {
    /// Emit releases, modifier changes, then new presses. Duplicate usages
    /// emit one change. Invalid reports leave the previous state intact.
    pub fn update(
        &mut self,
        report: &[u8],
        emit: impl FnMut(KeyChange),
    ) -> Result<(), ReportError> {
        let &[modifiers, _, a, b, c, d, e, f] = report else {
            return Err(ReportError::Length);
        };
        let keys = [a, b, c, d, e, f];
        if keys.iter().any(|key| (1..=3).contains(key)) {
            return Err(ReportError::KeyboardStatus);
        }
        self.transition(modifiers, keys, emit);
        Ok(())
    }

    pub fn disconnect(&mut self, emit: impl FnMut(KeyChange)) {
        self.transition(0, [0; 6], emit);
    }

    fn transition(&mut self, modifiers: u8, keys: [u8; 6], mut emit: impl FnMut(KeyChange)) {
        changes(&self.keys, &keys, self.modifiers, false, &mut emit);
        // USB defines left then right Ctrl, Shift, Alt, GUI.
        let codes = [0x1d, 0x2a, 0x38, 0x5b, 0x1d, 0x36, 0x38, 0x5c];
        for (index, scancode) in codes.into_iter().enumerate() {
            let mask = 1 << index;
            if (self.modifiers ^ modifiers) & mask == 0 {
                continue;
            }
            self.modifiers ^= mask;
            emit(KeyChange {
                scancode,
                extended: matches!(index, 3 | 4 | 6 | 7),
                pressed: self.modifiers & mask != 0,
                modifiers: self.modifiers,
            });
        }
        changes(&keys, &self.keys, modifiers, true, &mut emit);
        self.keys = keys;
    }
}

fn changes(
    from: &[u8; 6],
    other: &[u8; 6],
    modifiers: u8,
    pressed: bool,
    emit: &mut impl FnMut(KeyChange),
) {
    for (index, &usage) in from.iter().enumerate() {
        if from[..index].contains(&usage) || other.contains(&usage) {
            continue;
        }
        if let Some((scancode, extended)) = set1(usage) {
            emit(KeyChange {
                scancode,
                extended,
                pressed,
                modifiers,
            });
        }
    }
}

fn set1(usage: u8) -> Option<(u8, bool)> {
    const LETTERS: [u8; 26] = [
        0x1e, 0x30, 0x2e, 0x20, 0x12, 0x21, 0x22, 0x23, 0x17, 0x24, 0x25, 0x26, 0x32, 0x31, 0x18,
        0x19, 0x10, 0x13, 0x1f, 0x14, 0x16, 0x2f, 0x11, 0x2d, 0x15, 0x2c,
    ];
    let code = match usage {
        0x04..=0x1d => LETTERS[usize::from(usage - 0x04)],
        0x1e..=0x27 => usage - 0x1c,
        0x28 => 0x1c,
        0x29 => 0x01,
        0x2a => 0x0e,
        0x2b => 0x0f,
        0x2c => 0x39,
        0x3a..=0x43 => usage + 1,
        0x44..=0x45 => usage + 0x13,
        0x4f => return Some((0x4d, true)),
        0x50 => return Some((0x4b, true)),
        0x51 => return Some((0x50, true)),
        0x52 => return Some((0x48, true)),
        _ => return None,
    };
    Some((code, false))
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct MouseMotion {
    pub dx: i8,
    pub dy: i8,
    pub buttons: u8,
    pub changed_buttons: u8,
}

#[derive(Clone, Default)]
pub struct BootMouse {
    buttons: u8,
}

impl BootMouse {
    /// Boot protocol supplies three buttons and relative X/Y, with Y down.
    pub fn update(&mut self, report: &[u8]) -> Result<MouseMotion, ReportError> {
        let &[buttons, dx, dy] = report else {
            return Err(ReportError::Length);
        };
        Ok(self.motion(buttons & 7, dx as i8, dy as i8))
    }

    pub fn disconnect(&mut self) -> MouseMotion {
        self.motion(0, 0, 0)
    }

    fn motion(&mut self, buttons: u8, dx: i8, dy: i8) -> MouseMotion {
        let changed_buttons = self.buttons ^ buttons;
        self.buttons = buttons;
        MouseMotion {
            dx,
            dy,
            buttons,
            changed_buttons,
        }
    }
}
