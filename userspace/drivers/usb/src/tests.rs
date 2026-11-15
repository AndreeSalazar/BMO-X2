extern crate std;

use super::input::{Error as InputError, InputService, Payload};
use super::{
    descriptor::{Configuration, ErrorKind, Kind},
    hid::{BootKeyboard, BootMouse},
};
use std::vec::Vec;

const KEYBOARD: &[u8] = include_bytes!("../fixtures/qemu-keyboard.bin");
const MOUSE: &[u8] = include_bytes!("../fixtures/qemu-mouse.bin");

fn failure(bytes: &[u8]) -> super::descriptor::Error {
    match Configuration::<8>::parse(bytes) {
        Ok(_) => panic!("unexpected admission"),
        Err(error) => error,
    }
}

#[test]
fn actual_qemu_descriptors_and_requests() {
    for (bytes, kind, minimum) in [(KEYBOARD, Kind::Keyboard, 8), (MOUSE, Kind::Mouse, 3)] {
        let config = Configuration::<2>::parse(bytes).unwrap();
        let interfaces: Vec<_> = config.interfaces().collect();
        assert_eq!(interfaces.len(), 1);
        let interface = *interfaces[0];
        assert_eq!(interface.kind, kind);
        assert!(interface.packet_bytes >= minimum);
        assert_eq!(interface.endpoint, 0x81);
        assert_eq!(interface.configuration_request(), [0, 9, 1, 0, 0, 0, 0, 0]);
        assert_eq!(
            interface.boot_protocol_request(),
            [0x21, 11, 0, 0, 0, 0, 0, 0]
        );
    }
}

#[test]
fn composite_keyboard_and_mouse_keep_their_interfaces_and_endpoints() {
    let mut bytes = KEYBOARD.to_vec();
    let offset = bytes.len();
    bytes.extend_from_slice(&MOUSE[9..]);
    bytes[offset + 2] = 3;
    bytes[offset + 9 + 9 + 2] = 0x84;
    let total = bytes.len() as u16;
    bytes[2..4].copy_from_slice(&total.to_le_bytes());
    bytes[4] = 2;
    let config = Configuration::<2>::parse(&bytes).unwrap();
    let interfaces: Vec<_> = config.interfaces().collect();
    assert_eq!(interfaces[0].kind, Kind::Keyboard);
    assert_eq!(interfaces[1].kind, Kind::Mouse);
    assert_eq!(interfaces[1].interface, 3);
    assert_eq!(interfaces[1].endpoint, 0x84);
    assert_eq!(interfaces[1].boot_protocol_request()[4], 3);
    assert!(Configuration::<1>::parse(&bytes).is_err());
}

#[test]
fn truncated_and_zero_length_descriptors_explain_the_offset() {
    for end in 0..KEYBOARD.len() {
        assert!(Configuration::<2>::parse(&KEYBOARD[..end]).is_err());
    }
    let mut bytes = KEYBOARD.to_vec();
    bytes[18] = 0;
    let error = failure(&bytes);
    assert_eq!((error.kind, error.offset), (ErrorKind::Length, 18));
}

#[test]
fn selected_endpoint_requires_direction_type_size_and_interval() {
    for (field, value) in [(29, 1), (30, 2), (31, 2), (33, 0)] {
        let mut bytes = KEYBOARD.to_vec();
        bytes[field] = value;
        assert!(Configuration::<2>::parse(&bytes).is_err(), "field {field}");
    }
}

#[test]
fn duplicate_endpoint_and_mismatched_counts_are_rejected() {
    let mut bytes = KEYBOARD.to_vec();
    bytes.extend_from_slice(&KEYBOARD[27..]);
    let total = bytes.len() as u16;
    bytes[2..4].copy_from_slice(&total.to_le_bytes());
    bytes[13] = 2;
    assert_eq!(failure(&bytes).kind, ErrorKind::Endpoint);
    let mut bytes = KEYBOARD.to_vec();
    bytes[13] = 2;
    assert_eq!(failure(&bytes).kind, ErrorKind::EndpointCount);
    bytes[13] = 1;
    bytes[4] = 2;
    assert_eq!(failure(&bytes).kind, ErrorKind::Interface);
}

#[test]
fn report_protocol_only_interface_is_not_treated_as_boot() {
    let mut bytes = KEYBOARD.to_vec();
    bytes[15] = 0;
    assert_eq!(
        Configuration::<2>::parse(&bytes)
            .unwrap()
            .interfaces()
            .count(),
        0
    );
}

#[test]
fn boot_binding_requires_a_report_descriptor_declaration() {
    let mut bytes = KEYBOARD.to_vec();
    bytes[19] = 0xff;
    assert_eq!(failure(&bytes).kind, ErrorKind::Hid);
    bytes[19] = 0x21;
    bytes[25] = 0;
    bytes[26] = 0;
    assert_eq!(failure(&bytes).kind, ErrorKind::Hid);
}

#[test]
fn alternate_setting_is_not_activated_implicitly() {
    let mut bytes = KEYBOARD.to_vec();
    let offset = bytes.len();
    bytes.extend_from_slice(&KEYBOARD[9..]);
    bytes[offset + 3] = 1;
    let total = bytes.len() as u16;
    bytes[2..4].copy_from_slice(&total.to_le_bytes());
    assert_eq!(
        Configuration::<2>::parse(&bytes)
            .unwrap()
            .interfaces()
            .count(),
        1
    );
}

#[test]
fn mutations_of_untrusted_lengths_do_not_panic() {
    for offset in 0..KEYBOARD.len() {
        for value in 0..=255 {
            let mut bytes = KEYBOARD.to_vec();
            bytes[offset] = value;
            let _ = Configuration::<2>::parse(&bytes);
        }
    }
}

#[test]
fn disconnect_releases_keys_and_mouse_buttons() {
    let mut keyboard = BootKeyboard::default();
    let mut changes = Vec::new();
    keyboard
        .update(&[8, 0, 4, 0, 0, 0, 0, 0], |change| changes.push(change))
        .unwrap();
    changes.clear();
    keyboard.disconnect(|change| changes.push(change));
    assert_eq!(changes.len(), 2);
    assert!(changes.iter().all(|change| !change.pressed));
    let mut mouse = BootMouse::default();
    mouse.update(&[1, 127, 128]).unwrap();
    let released = mouse.disconnect();
    assert_eq!(
        (
            released.buttons,
            released.changed_buttons,
            released.dx,
            released.dy
        ),
        (0, 1, 0, 0)
    );
}

#[test]
fn input_service_keeps_keyboard_and_mouse_sources_separate() {
    let mut service = InputService::<2, 8>::default();
    let keyboard = service.bind(Kind::Keyboard).unwrap();
    let mouse = service.bind(Kind::Mouse).unwrap();
    service.report(keyboard, &[0, 0, 4, 0, 0, 0, 0, 0]).unwrap();
    service.report(mouse, &[1, 10, 255]).unwrap();
    let key = service.poll().unwrap();
    let pointer = service.poll().unwrap();
    assert_eq!(key.source, keyboard);
    assert_eq!(pointer.source, mouse);
    assert!(matches!(key.payload, Payload::Key(change) if change.pressed));
    assert!(
        matches!(pointer.payload, Payload::Mouse(motion) if motion.dx == 10 && motion.dy == -1)
    );
    assert_eq!(service.poll(), None);
}

#[test]
fn queue_pressure_does_not_commit_a_partial_keyboard_report() {
    let mut service = InputService::<2, 2>::default();
    let keyboard = service.bind(Kind::Keyboard).unwrap();
    let mouse = service.bind(Kind::Mouse).unwrap();
    service.report(mouse, &[0, 1, 0]).unwrap();
    let report = [8, 0, 4, 0, 0, 0, 0, 0];
    assert_eq!(
        service.report(keyboard, &report),
        Err(InputError::Backpressure)
    );
    assert_eq!(service.pending(), 1);
    assert_eq!(service.poll().unwrap().source, mouse);
    assert_eq!(service.report(keyboard, &report), Ok(2));
    assert!(matches!(service.poll().unwrap().payload, Payload::Key(change) if change.extended));
    assert!(
        matches!(service.poll().unwrap().payload, Payload::Key(change) if change.scancode == 0x1e)
    );
}

#[test]
fn detach_discards_pending_presses_and_rejects_stale_reports() {
    let mut service = InputService::<2, 8>::default();
    let keyboard = service.bind(Kind::Keyboard).unwrap();
    let mouse = service.bind(Kind::Mouse).unwrap();
    service.report(keyboard, &[8, 0, 4, 0, 0, 0, 0, 0]).unwrap();
    service.report(mouse, &[1, 1, 0]).unwrap();
    service.detach(keyboard).unwrap();
    assert_eq!(service.poll().unwrap().source, mouse);
    for _ in 0..2 {
        assert!(matches!(service.poll().unwrap().payload, Payload::Key(change) if !change.pressed));
    }
    assert_eq!(service.poll().unwrap().payload, Payload::Detached);
    let replacement = service.bind(Kind::Keyboard).unwrap();
    assert_ne!(keyboard, replacement);
    assert_eq!(
        service.report(keyboard, &[0; 8]),
        Err(InputError::StaleSource)
    );
    assert_eq!(service.detach(keyboard), Err(InputError::StaleSource));
    assert_eq!(service.report(replacement, &[0; 8]), Ok(0));
}

#[test]
fn detach_backpressure_keeps_binding_until_releases_fit() {
    let mut service = InputService::<2, 2>::default();
    let keyboard = service.bind(Kind::Keyboard).unwrap();
    let mouse = service.bind(Kind::Mouse).unwrap();
    service.report(mouse, &[1, 0, 0]).unwrap();
    service.poll();
    service.report(keyboard, &[8, 0, 4, 0, 0, 0, 0, 0]).unwrap();
    assert_eq!(service.detach(mouse), Err(InputError::Backpressure));
    service.poll();
    service.poll();
    assert_eq!(service.detach(mouse), Ok(2));
    assert!(
        matches!(service.poll().unwrap().payload, Payload::Mouse(motion)
        if motion.buttons == 0 && motion.changed_buttons == 1)
    );
    assert_eq!(service.poll().unwrap().payload, Payload::Detached);
}

#[test]
fn maximum_keyboard_transition_and_release_batch_fit_the_bounds() {
    let mut service = InputService::<1, 20>::default();
    let keyboard = service.bind(Kind::Keyboard).unwrap();
    service.report(keyboard, &[0, 0, 4, 5, 6, 7, 8, 9]).unwrap();
    while service.poll().is_some() {}
    assert_eq!(
        service.report(keyboard, &[255, 0, 10, 11, 12, 13, 14, 15]),
        Ok(20)
    );
    assert_eq!(service.detach(keyboard), Ok(15));
    for _ in 0..14 {
        assert!(matches!(service.poll().unwrap().payload, Payload::Key(change) if !change.pressed));
    }
    assert_eq!(service.poll().unwrap().payload, Payload::Detached);
}

#[test]
fn idle_and_invalid_reports_preserve_service_state() {
    let mut service = InputService::<1, 8>::default();
    let keyboard = service.bind(Kind::Keyboard).unwrap();
    service.report(keyboard, &[0, 0, 4, 0, 0, 0, 0, 0]).unwrap();
    service.poll();
    assert!(matches!(
        service.report(keyboard, &[0, 0, 1, 0, 0, 0, 0, 0]),
        Err(InputError::Report(_))
    ));
    assert_eq!(service.pending(), 0);
    assert_eq!(service.detach(keyboard), Ok(2));
    assert!(
        matches!(service.poll().unwrap().payload, Payload::Key(change) if change.scancode == 0x1e && !change.pressed)
    );
}

#[test]
fn zero_capacity_is_rejected_without_modulo_by_zero() {
    let mut service = InputService::<0, 0>::default();
    assert_eq!(service.bind(Kind::Mouse), Err(InputError::Capacity));
    assert_eq!(service.poll(), None);
    let mut service = InputService::<1, 0>::default();
    let mouse = service.bind(Kind::Mouse).unwrap();
    assert_eq!(
        service.report(mouse, &[1, 0, 0]),
        Err(InputError::Backpressure)
    );
    assert_eq!(service.detach(mouse), Err(InputError::Backpressure));
}

#[test]
fn fixed_service_profile_has_a_measured_state_budget() {
    let bytes = core::mem::size_of::<InputService<8, 64>>();
    std::println!(
        "InputService<8,64> state bytes: {bytes}; excludes stack, code and transport buffers"
    );
    assert!(bytes <= 4096);
}
