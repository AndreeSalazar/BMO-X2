use crate::{Desktop, Workspace};

const EVENT_PRESENT: u64 = 1 << 8;
const KEY_PRESSED: u64 = 1 << 9;
const EVENT_MASK: u64 = 0xff | EVENT_PRESENT | KEY_PRESSED;
const MOD_SHIFT: u8 = 1 << 0;
const MOD_CTRL: u8 = 1 << 1;
const MOD_CAPS: u8 = 1 << 4;
const MOD_SUPER: u8 = 1 << 5;
const MOD_SUPER_SHIFT: u8 = MOD_SUPER | MOD_SHIFT;
const MOD_SUPER_CTRL: u8 = MOD_SUPER | MOD_CTRL;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct KeyEvent {
    pub scancode: u8,
    pub pressed: bool,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct MalformedKeyEvent;

impl KeyEvent {
    /// Decode the BMO-X INPUT_OP_EVENTO_TECLA value. The low byte is the
    /// normalized Set 1 code. Presence and press state are separate bits.
    pub fn from_bmo_x(raw: u64) -> Result<Option<Self>, MalformedKeyEvent> {
        if raw == 0 {
            return Ok(None);
        }
        let scancode = raw as u8;
        if raw & !EVENT_MASK != 0 || raw & EVENT_PRESENT == 0 || scancode == 0 {
            return Err(MalformedKeyEvent);
        }
        Ok(Some(Self {
            scancode,
            pressed: raw & KEY_PRESSED != 0,
        }))
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum KeyRoute {
    Forward(KeyEvent),
    Consumed,
}

/// Tracks the top-row keys 1 through 9 and Q. Captured keys keep their
/// press, repeat, and release together even if modifiers change.
#[derive(Default)]
pub struct Keyboard {
    down: u16,
    captured: u16,
}

impl Keyboard {
    /// The caller supplies the modifier mask sampled for this event,
    /// in the BMO-X INPUT_OP_MODIFICADORES bit layout.
    pub fn handle<const N: usize>(
        &mut self,
        desktop: &mut Desktop<'_, N>,
        raw: u64,
        modifiers: u8,
    ) -> Result<Option<KeyRoute>, MalformedKeyEvent> {
        let Some(event) = KeyEvent::from_bmo_x(raw)? else {
            return Ok(None);
        };
        Ok(Some(self.route(desktop, event, modifiers)))
    }

    pub fn route<const N: usize>(
        &mut self,
        desktop: &mut Desktop<'_, N>,
        event: KeyEvent,
        modifiers: u8,
    ) -> KeyRoute {
        let number = event.scancode.saturating_sub(1);
        let bit = match event.scancode {
            2..=10 => 1 << (number - 1),
            0x10 => 1 << 9,
            _ => return KeyRoute::Forward(event),
        };
        if !event.pressed {
            let was_captured = self.captured & bit != 0;
            self.down &= !bit;
            self.captured &= !bit;
            return if was_captured {
                KeyRoute::Consumed
            } else {
                KeyRoute::Forward(event)
            };
        }
        if self.down & bit != 0 {
            return if self.captured & bit != 0 {
                KeyRoute::Consumed
            } else {
                KeyRoute::Forward(event)
            };
        }
        self.down |= bit;
        match (modifiers & !MOD_CAPS, event.scancode, Workspace::new(number)) {
            (MOD_SUPER, 0x10, _) => {
                desktop.close_focused();
            }
            (MOD_SUPER, _, _) => {
                desktop.focus_shortcut(number);
            }
            (MOD_SUPER_CTRL, _, Some(workspace)) => desktop.switch(workspace),
            (MOD_SUPER_SHIFT, _, Some(workspace)) => {
                desktop.move_focused(workspace);
            }
            _ => return KeyRoute::Forward(event),
        }
        self.captured |= bit;
        KeyRoute::Consumed
    }

    /// Reset the local key state when the input source is replaced.
    pub fn reset(&mut self) {
        *self = Self::default();
    }
}
