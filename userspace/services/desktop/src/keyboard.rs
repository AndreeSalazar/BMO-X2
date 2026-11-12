use crate::{Desktop, Workspace};

const EVENT_PRESENT: u64 = 1 << 8;
const KEY_PRESSED: u64 = 1 << 9;
const EVENT_MASK: u64 = 0xff | EVENT_PRESENT | KEY_PRESSED;
const MOD_SHIFT: u8 = 1 << 0;
const MOD_CAPS: u8 = 1 << 4;
const MOD_SUPER: u8 = 1 << 5;
const MOD_SUPER_SHIFT: u8 = MOD_SUPER | MOD_SHIFT;

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

/// Tracks only the top-row keys 1 through 4. Captured keys keep their
/// press, repeat, and release together even if modifiers change.
#[derive(Default)]
pub struct Keyboard {
    down: u8,
    captured: u8,
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
        let Some(workspace) = event.scancode.checked_sub(1).and_then(Workspace::new) else {
            return Ok(Some(KeyRoute::Forward(event)));
        };
        let bit = 1 << (workspace.number() - 1);
        if !event.pressed {
            let was_captured = self.captured & bit != 0;
            self.down &= !bit;
            self.captured &= !bit;
            return Ok(Some(if was_captured {
                KeyRoute::Consumed
            } else {
                KeyRoute::Forward(event)
            }));
        }
        if self.down & bit != 0 {
            return Ok(Some(if self.captured & bit != 0 {
                KeyRoute::Consumed
            } else {
                KeyRoute::Forward(event)
            }));
        }
        self.down |= bit;
        match modifiers & !MOD_CAPS {
            MOD_SUPER => desktop.switch(workspace),
            MOD_SUPER_SHIFT => {
                desktop.move_focused(workspace);
            }
            _ => return Ok(Some(KeyRoute::Forward(event))),
        }
        self.captured |= bit;
        Ok(Some(KeyRoute::Consumed))
    }

    /// Reset the local key state when the input source is replaced.
    pub fn reset(&mut self) {
        *self = Self::default();
    }
}
