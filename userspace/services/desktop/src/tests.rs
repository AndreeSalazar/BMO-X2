use super::*;

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
