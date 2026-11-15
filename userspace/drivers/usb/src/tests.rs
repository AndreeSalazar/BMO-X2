extern crate std;

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
