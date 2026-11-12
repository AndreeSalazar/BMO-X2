use super::*;

const SUPER: u8 = 0x20;
const SHIFT: u8 = 0x01;
const CTRL: u8 = 0x02;

#[test]
fn parent_event_keeps_raw_scancode_press_and_release() {
    assert_eq!(KeyEvent::from_bmo_x(0), Ok(None));
    assert_eq!(
        KeyEvent::from_bmo_x(0x302),
        Ok(Some(KeyEvent {
            scancode: 2,
            pressed: true
        }))
    );
    assert_eq!(
        KeyEvent::from_bmo_x(0x102),
        Ok(Some(KeyEvent {
            scancode: 2,
            pressed: false
        }))
    );
    for invalid in [0x02, 0x202, 0x300, 0x702, u64::MAX] {
        assert_eq!(KeyEvent::from_bmo_x(invalid), Err(MalformedKeyEvent));
    }
}

#[test]
fn ctrl_super_selects_each_workspace_and_captures_the_matching_release() {
    let mut desktop = Desktop::<1>::new();
    let mut keyboard = Keyboard::default();
    for workspace in 1..=4 {
        let code = u64::from(workspace + 1);
        assert_eq!(
            keyboard.handle(&mut desktop, 0x300 | code, SUPER | CTRL | 0x10),
            Ok(Some(KeyRoute::Consumed))
        );
        assert_eq!(desktop.active().number(), workspace);
        assert_eq!(
            keyboard.handle(&mut desktop, 0x100 | code, 0),
            Ok(Some(KeyRoute::Consumed))
        );
    }
}

#[test]
fn super_shift_moves_once_even_when_the_digit_repeats() {
    let mut desktop = Desktop::<2>::new();
    let mut keyboard = Keyboard::default();
    let pixel = Surface::new(1, 1, &[1]).unwrap();
    desktop.open(10, 0, 0, pixel).unwrap();
    desktop.open(20, 0, 0, pixel).unwrap();
    assert_eq!(
        keyboard.handle(&mut desktop, 0x303, SUPER | SHIFT),
        Ok(Some(KeyRoute::Consumed))
    );
    assert_eq!(desktop.active(), Workspace::FIRST);
    assert_eq!(desktop.focused(), Some(10));
    assert_eq!(
        keyboard.handle(&mut desktop, 0x303, SUPER | SHIFT),
        Ok(Some(KeyRoute::Consumed))
    );
    assert_eq!(desktop.focused(), Some(10));
    desktop.switch(Workspace::new(2).unwrap());
    assert_eq!(desktop.focused(), Some(20));
}

#[test]
fn ordinary_digits_and_unrelated_chords_are_forwarded() {
    let mut desktop = Desktop::<0>::new();
    let mut keyboard = Keyboard::default();
    for modifiers in [0, SUPER | 0x04, SUPER | 0x08] {
        let press = Ok(Some(KeyRoute::Forward(KeyEvent {
            scancode: 3,
            pressed: true,
        })));
        assert_eq!(keyboard.handle(&mut desktop, 0x303, modifiers), press);
        assert_eq!(keyboard.handle(&mut desktop, 0x303, SUPER), press);
        assert_eq!(
            keyboard.handle(&mut desktop, 0x103, 0),
            Ok(Some(KeyRoute::Forward(KeyEvent {
                scancode: 3,
                pressed: false
            })))
        );
    }
    assert_eq!(
        keyboard.handle(&mut desktop, 0x34f, SUPER),
        Ok(Some(KeyRoute::Forward(KeyEvent {
            scancode: 0x4f,
            pressed: true
        })))
    );
    assert_eq!(desktop.active(), Workspace::FIRST);
}

#[test]
fn super_focuses_stable_slots_within_the_active_workspace() {
    let mut desktop = Desktop::<4>::new();
    let mut keyboard = Keyboard::default();
    let pixel = Surface::new(1, 1, &[1]).unwrap();
    for id in [10, 20, 30] {
        desktop.open(id, 0, 0, pixel).unwrap();
    }
    keyboard.handle(&mut desktop, 0x303, SUPER).unwrap();
    assert_eq!(desktop.focused(), Some(20));
    assert_eq!(desktop.close_focused(), Some(20));
    assert!(!desktop.focus_shortcut(2));
    keyboard.handle(&mut desktop, 0x304, SUPER).unwrap();
    assert_eq!(desktop.focused_shortcut(), Some(3));
    keyboard.handle(&mut desktop, 0x303, SUPER | CTRL).unwrap();
    assert_eq!(desktop.active().number(), 1);
    keyboard.handle(&mut desktop, 0x103, 0).unwrap();
    keyboard.handle(&mut desktop, 0x303, SUPER | CTRL).unwrap();
    assert_eq!(desktop.active().number(), 2);
    assert_eq!(desktop.focused(), None);
    desktop.switch(Workspace::FIRST);
    assert_eq!(desktop.focused(), Some(30));
}

#[test]
fn replacing_input_discards_stale_key_capture() {
    let mut desktop = Desktop::<0>::new();
    let mut keyboard = Keyboard::default();
    keyboard.handle(&mut desktop, 0x304, SUPER).unwrap();
    keyboard.reset();
    assert_eq!(
        keyboard.handle(&mut desktop, 0x304, 0),
        Ok(Some(KeyRoute::Forward(KeyEvent {
            scancode: 4,
            pressed: true
        })))
    );
}

#[test]
fn switching_restores_focus_and_composes_only_the_active_workspace() {
    let mut desktop = Desktop::<3>::new();
    let red = Surface::new(1, 1, &[0x00ff0000]).unwrap();
    let blue = Surface::new(1, 1, &[0x000000ff]).unwrap();
    let second = Workspace::new(2).unwrap();
    desktop.open(10, 0, 0, red).unwrap();
    desktop.switch(second);
    desktop.open(20, 0, 0, blue).unwrap();

    let mut pixels = [0; 2];
    desktop.compose(&mut Frame::new(2, 1, &mut pixels).unwrap(), 0);
    assert_eq!(pixels, [0x000000ff, 0]);
    assert_eq!(desktop.focused(), Some(20));

    desktop.switch(Workspace::FIRST);
    desktop.compose(&mut Frame::new(2, 1, &mut pixels).unwrap(), 0);
    assert_eq!(pixels, [0x00ff0000, 0]);
    assert_eq!(desktop.focused(), Some(10));
}

#[test]
fn moving_keeps_the_current_workspace_and_closing_restores_focus() {
    let mut desktop = Desktop::<3>::new();
    let pixel = Surface::new(1, 1, &[1]).unwrap();
    let second = Workspace::new(2).unwrap();
    desktop.open(10, 0, 0, pixel).unwrap();
    desktop.open(20, 0, 0, pixel).unwrap();
    assert!(desktop.focus(10));
    assert_eq!(desktop.move_focused(second), Some(10));
    assert_eq!(desktop.active(), Workspace::FIRST);
    assert_eq!(desktop.focused(), Some(20));
    assert!(!desktop.focus(10));

    desktop.switch(second);
    desktop.open(30, 0, 0, pixel).unwrap();
    assert_eq!(desktop.close_focused(), Some(30));
    assert_eq!(desktop.focused(), Some(10));
}

#[test]
fn composition_clips_each_surface_and_draws_the_top_window_last() {
    let mut desktop = Desktop::<3>::new();
    let base = Surface::new(3, 2, &[1, 2, 3, 4, 5, 6]).unwrap();
    let top = Surface::new(2, 2, &[7, 8, 9, 10]).unwrap();
    desktop.open(10, -1, 0, base).unwrap();
    desktop.open(20, 1, 1, top).unwrap();
    desktop.open(30, i32::MIN, i32::MAX, top).unwrap();
    let mut pixels = [0; 4];
    desktop.compose(&mut Frame::new(2, 2, &mut pixels).unwrap(), 0);
    assert_eq!(pixels, [2, 3, 5, 7]);
}

#[test]
fn rejects_invalid_workspaces_buffers_and_window_ids() {
    assert_eq!(Workspace::new(0), None);
    assert_eq!(Workspace::new(5), None);
    assert!(Surface::new(2, 2, &[0; 3]).is_none());
    assert!(Surface::new(usize::MAX, 2, &[]).is_none());
    assert!(Frame::new(1, 2, &mut [0; 1]).is_none());
    let mut desktop = Desktop::<1>::new();
    let pixel = Surface::new(1, 1, &[1]).unwrap();
    desktop.open(10, 0, 0, pixel).unwrap();
    assert_eq!(desktop.open(10, 0, 0, pixel), Err(OpenError::DuplicateId));
    assert_eq!(desktop.open(20, 0, 0, pixel), Err(OpenError::Full));
    assert_eq!(desktop.close_focused(), Some(10));
    desktop.open(20, 0, 0, pixel).unwrap();
}
