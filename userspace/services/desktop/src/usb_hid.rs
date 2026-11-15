//! Desktop policy adapter over the Ring 3 USB report decoder.

#[path = "../../../drivers/usb/src/hid.rs"]
mod reports;
pub use reports::*;

impl KeyChange {
    /// Extended keys keep their prefix and bypass the number shortcut router.
    pub fn route<const N: usize>(
        self,
        keyboard: &mut crate::Keyboard,
        desktop: &mut crate::Desktop<'_, N>,
    ) -> bool {
        !self.extended
            && keyboard.route(
                desktop,
                crate::KeyEvent {
                    scancode: self.scancode,
                    pressed: self.pressed,
                },
                self.desktop_modifiers(),
            ) == crate::KeyRoute::Consumed
    }

    /// Modifier bits consumed by the desktop's BMO-X keyboard router.
    pub fn desktop_modifiers(self) -> u8 {
        u8::from(self.modifiers & 0x22 != 0)
            | (u8::from(self.modifiers & 0x11 != 0) << 1)
            | (u8::from(self.modifiers & 0x88 != 0) << 5)
    }
}
