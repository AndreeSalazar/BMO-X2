use core::cell::RefCell;
use core::mem::MaybeUninit;

// Only the cooperative desktop thread accesses the queue.
struct Input {
    pending: [u8; 64],
    head: usize,
    len: usize,
    held: u128,
}

impl Input {
    fn pop(&mut self) -> u32 {
        if self.len == 0 {
            return 256;
        }
        let key = self.pending[self.head];
        self.head = (self.head + 1) % self.pending.len();
        self.len -= 1;
        let bit = 1 << (key & 0x7f);
        if key & 0x80 == 0 {
            self.held |= bit;
        } else {
            self.held &= !bit;
        }
        u32::from(key)
    }

    fn push(&mut self, key: u8) {
        if self.len == self.pending.len() {
            self.release_all();
        }
        if self.len < self.pending.len() {
            self.pending[(self.head + self.len) % self.pending.len()] = key;
            self.len += 1;
        }
    }

    fn release_all(&mut self) {
        self.head = 0;
        self.len = 0;
        let mut held = self.held;
        while held != 0 {
            let key = held.trailing_zeros();
            held &= held - 1;
            self.pending[self.len] = key as u8 | 0x80;
            self.len += 1;
        }
    }
}

struct SingleThreadInput(RefCell<MaybeUninit<Input>>);
unsafe impl Sync for SingleThreadInput {}
static INPUT: SingleThreadInput = SingleThreadInput(RefCell::new(MaybeUninit::uninit()));

fn with_input<T>(action: impl FnOnce(&mut Input) -> T) -> T {
    let mut input = INPUT.0.borrow_mut();
    // DoomWindow::open initializes the queue before invoking Doom.
    action(unsafe { input.assume_init_mut() })
}

#[unsafe(no_mangle)]
extern "C" fn director_doom_key() -> u32 {
    with_input(Input::pop)
}

pub fn forward(key: u8) {
    // Only Set 1 codes mapped by DG_GetKey need held-key accounting.
    if matches!(key & 0x7f, 1..=10 | 14 | 15 | 21 | 28 | 29 | 42 | 49 | 54 | 56 | 57 | 72 | 75 | 77 | 80) {
        with_input(|input| input.push(key));
    }
}

unsafe extern "C" {
    fn doom_init();
    fn doom_tick();
}

#[derive(Default)]
pub struct DoomWindow {
    initialized: bool,
    workspace: Option<usize>,
    focused: bool,
}

impl DoomWindow {
    pub fn open(&mut self, workspace: usize) -> usize {
        if !self.initialized {
            INPUT.0.borrow_mut().write(Input { pending: [0; 64], head: 0, len: 0, held: 0 });
            unsafe { doom_init() };
            self.initialized = true;
        }
        let workspace = *self.workspace.get_or_insert(workspace);
        self.focused = true;
        workspace
    }

    pub fn active(&self, workspace: usize) -> bool {
        self.workspace == Some(workspace) && self.focused
    }

    pub fn focus(&mut self, workspace: usize) -> bool {
        self.focused = self.workspace == Some(workspace);
        self.focused
    }

    pub fn blur(&mut self) {
        self.focused = false;
        if self.initialized {
            with_input(Input::release_all);
        }
    }

    pub fn close(&mut self) {
        self.blur();
        self.workspace = None;
    }

    pub fn tick(&self) {
        unsafe { doom_tick() };
    }
}
