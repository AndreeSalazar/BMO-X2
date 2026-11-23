use super::*;

const HD: Extent = Extent {
    width: 1280,
    height: 720,
};
const FULL_HD: Extent = Extent {
    width: 1920,
    height: 1080,
};
const CONTEXT: DisplayContext = DisplayContext {
    handle: 0x200,
    len_bytes: 0x100_0000,
};
const FRAME: VramFrame = VramFrame {
    extent: FULL_HD,
    pitch_bytes: 7680,
    offset_bytes: 0,
};

#[test]
fn full_hd_packets_match_c67e_method_layout() {
    assert_eq!(
        image_methods(FULL_HD, FRAME, CONTEXT),
        Ok([
            0x0004_0308,
            1,
            0x0010_0224,
            0x0438_0780,
            0,
            0xe6,
            120,
            0x0008_0240,
            0x200,
            1,
            0x0004_0260,
            0,
            0x0004_0290,
            0,
            0x0004_0298,
            0x0438_0780,
            0x0004_02a4,
            0x0438_0780,
        ])
    );
}

#[test]
fn flip_encodes_a_bounded_notifier_and_update() {
    let notifier = FlipNotifier {
        handle: 0x201,
        len_bytes: 4096,
        offset_bytes: 0xff0,
    };
    let words = flip_methods(FULL_HD, FRAME, CONTEXT, notifier).unwrap();
    assert_eq!(
        &words[..18],
        &image_methods(FULL_HD, FRAME, CONTEXT).unwrap()
    );
    assert_eq!(
        &words[18..],
        &[0x0008_021c, 0x201, 0xff0, 0x0008_0370, 0, 0, 0x0004_0200, 1]
    );
    for invalid in [
        FlipNotifier {
            len_bytes: 4095,
            ..notifier
        },
        FlipNotifier {
            offset_bytes: 0xff1,
            ..notifier
        },
        FlipNotifier {
            offset_bytes: 0x1000,
            len_bytes: 8192,
            ..notifier
        },
        FlipNotifier {
            handle: CONTEXT.handle,
            ..notifier
        },
    ] {
        assert_eq!(
            flip_methods(FULL_HD, FRAME, CONTEXT, invalid),
            Err(ScanoutError::Notifier)
        );
    }
}

#[test]
fn supports_hd_and_second_full_hd_buffer_with_a_padded_pitch() {
    let hd = VramFrame {
        extent: HD,
        pitch_bytes: 5120,
        offset_bytes: 0,
    };
    let words = image_methods(HD, hd, CONTEXT).unwrap();
    assert_eq!(
        (words[3], words[6], words[15], words[17]),
        (0x02d0_0500, 80, 0x02d0_0500, 0x02d0_0500)
    );

    let next = VramFrame {
        pitch_bytes: 7744,
        offset_bytes: 0x800_000,
        ..FRAME
    };
    let words = image_methods(FULL_HD, next, CONTEXT).unwrap();
    assert_eq!((words[6], words[11]), (121, 0x8000));
}

#[test]
fn rejects_scaling_and_zero_dimensions() {
    assert_eq!(
        image_methods(HD, FRAME, CONTEXT),
        Err(ScanoutError::Geometry)
    );
    let head = Extent {
        width: 0,
        ..FULL_HD
    };
    assert_eq!(
        image_methods(
            head,
            VramFrame {
                extent: head,
                ..FRAME
            },
            CONTEXT
        ),
        Err(ScanoutError::Geometry)
    );
}

#[test]
fn rejects_bad_pitch_and_unaligned_or_unencodable_offsets() {
    for pitch_bytes in [7616, 7684, 0x80000] {
        let frame = VramFrame {
            pitch_bytes,
            ..FRAME
        };
        assert_eq!(
            image_methods(FULL_HD, frame, CONTEXT),
            Err(ScanoutError::Pitch)
        );
    }
    for offset_bytes in [128, 1 << 40, u64::MAX] {
        let frame = VramFrame {
            offset_bytes,
            ..FRAME
        };
        assert_eq!(
            image_methods(FULL_HD, frame, CONTEXT),
            Err(ScanoutError::Offset)
        );
    }
}

#[test]
fn requires_the_entire_buffer_inside_an_authorized_context() {
    let len_bytes = 7680 * 1080;
    let exact = DisplayContext {
        len_bytes,
        ..CONTEXT
    };
    assert!(image_methods(FULL_HD, FRAME, exact).is_ok());
    let truncated = DisplayContext {
        len_bytes: len_bytes - 1,
        ..CONTEXT
    };
    assert_eq!(
        image_methods(FULL_HD, FRAME, truncated),
        Err(ScanoutError::Range)
    );
    let wrong = DisplayContext {
        handle: 1,
        ..CONTEXT
    };
    assert_eq!(
        image_methods(FULL_HD, FRAME, wrong),
        Err(ScanoutError::Context)
    );
    let high = VramFrame {
        offset_bytes: (1 << 40) - 256,
        ..FRAME
    };
    let huge = DisplayContext {
        len_bytes: u64::MAX,
        ..CONTEXT
    };
    assert_eq!(image_methods(FULL_HD, high, huge), Err(ScanoutError::Range));
}
