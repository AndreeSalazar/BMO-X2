#![no_std]
#![forbid(unsafe_code)]

mod keyboard;
mod surface;

pub use keyboard::{KeyEvent, KeyRoute, Keyboard, MalformedKeyEvent};
pub use surface::{Frame, Surface};

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct Workspace(u8);

impl Workspace {
    pub const FIRST: Self = Self(1);

    pub const fn new(number: u8) -> Option<Self> {
        match number {
            1..=4 => Some(Self(number)),
            _ => None,
        }
    }

    pub const fn number(self) -> u8 {
        self.0
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum OpenError {
    DuplicateId,
    Full,
}

#[derive(Clone, Copy)]
struct Window<'a> {
    id: u32,
    workspace: Workspace,
    x: i32,
    y: i32,
    surface: Surface<'a>,
}

/// The occupied prefix is ordered from bottom to top. Each workspace's
/// focused window is its highest entry in that order.
pub struct Desktop<'a, const N: usize> {
    active: Workspace,
    windows: [Option<Window<'a>>; N],
    len: usize,
}

impl<'a, const N: usize> Desktop<'a, N> {
    pub const fn new() -> Self {
        Self {
            active: Workspace::FIRST,
            windows: [None; N],
            len: 0,
        }
    }

    pub fn active(&self) -> Workspace {
        self.active
    }

    pub fn switch(&mut self, workspace: Workspace) {
        self.active = workspace;
    }

    pub fn open(&mut self, id: u32, x: i32, y: i32, surface: Surface<'a>) -> Result<(), OpenError> {
        if self.windows[..self.len]
            .iter()
            .flatten()
            .any(|window| window.id == id)
        {
            return Err(OpenError::DuplicateId);
        }
        let slot = self.windows.get_mut(self.len).ok_or(OpenError::Full)?;
        *slot = Some(Window {
            id,
            workspace: self.active,
            x,
            y,
            surface,
        });
        self.len += 1;
        Ok(())
    }

    fn focused_index(&self) -> Option<usize> {
        self.windows[..self.len]
            .iter()
            .rposition(|entry| entry.is_some_and(|window| window.workspace == self.active))
    }

    pub fn focused(&self) -> Option<u32> {
        self.focused_index()
            .and_then(|index| self.windows[index].map(|window| window.id))
    }

    pub fn focus(&mut self, id: u32) -> bool {
        let Some(index) = self.windows[..self.len].iter().position(|entry| {
            entry.is_some_and(|window| window.workspace == self.active && window.id == id)
        }) else {
            return false;
        };
        self.windows[index..self.len].rotate_left(1);
        true
    }

    pub fn move_focused(&mut self, destination: Workspace) -> Option<u32> {
        let index = self.focused_index()?;
        let window = self.windows[index].as_mut()?;
        window.workspace = destination;
        let id = window.id;
        self.windows[index..self.len].rotate_left(1);
        Some(id)
    }

    pub fn close_focused(&mut self) -> Option<u32> {
        let index = self.focused_index()?;
        let closed = self.windows[index].take()?;
        self.windows[index..self.len].rotate_left(1);
        self.len -= 1;
        Some(closed.id)
    }

    pub fn compose(&self, frame: &mut Frame<'_>, background: u32) {
        frame.clear(background);
        for window in self.windows[..self.len].iter().flatten() {
            if window.workspace == self.active {
                frame.blit(window.surface, window.x, window.y);
            }
        }
    }
}

impl<const N: usize> Default for Desktop<'_, N> {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests;
