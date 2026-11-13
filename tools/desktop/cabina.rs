use super::{fill, invoke};

const DIAGNOSTICS: u64 = 3;
const READ: u64 = 3;
const INK: u32 = 0xe7efff;
const PANEL: u32 = 0x232638;

// 3x5 row-major glyphs for the console's fixed vocabulary.
fn text(mut x: u64, y: u64, bytes: &[u8]) {
    for byte in bytes {
        let glyph = match byte {
            b'0'..=b'9' => [
                0x7b6f, 0x749a, 0x73e7, 0x79e7, 0x49ed, 0x79cf, 0x7bcf, 0x4927, 0x7bef, 0x79ef,
            ][usize::from(byte - b'0')],
            b'A' => 0x5bef,
            b'B' => 0x3aeb,
            b'C' => 0x724f,
            b'E' => 0x73cf,
            b'F' => 0x13cf,
            b'I' => 0x7497,
            b'K' => 0x5aed,
            b'M' => 0x5bfd,
            b'N' => 0x5b7d,
            b'O' => 0x7b6f,
            b'P' => 0x13ef,
            b'R' => 0x57ef,
            b'S' => 0x79cf,
            b'T' => 0x2497,
            b'U' => 0x7b6d,
            b'V' => 0x2b6d,
            _ => 0,
        };
        for bit in 0..15 {
            if glyph & (1 << bit) != 0 {
                fill(x + bit % 3 * 2, y + bit / 3 * 2, 2, 2, INK);
            }
        }
        x += 8;
    }
}

pub fn show() {
    fill(0, 0, 640, 400, 0x0d0e17);
    fill(24, 24, 592, 142, PANEL);
    text(40, 42, b"CABINA");
    text(40, 67, b"T TICKS   E EVENTOS   V TIMEOUTS");
    text(40, 89, b"F2 CERRAR");
}

pub fn command(scancode: u8) {
    let (field, label): (u64, &[u8]) = match scancode {
        0x14 => (0, b"TICKS"),
        0x12 => (1, b"EVENTOS"),
        0x2f => (2, b"TIMEOUTS"),
        _ => return,
    };
    let mut value = invoke(DIAGNOSTICS, READ, field, 0);
    let mut digits = [b'0'; 10];
    let mut first = digits.len();
    loop {
        first -= 1;
        digits[first] += (value % 10) as u8;
        value /= 10;
        if value == 0 {
            break;
        }
    }
    fill(40, 116, 400, 24, PANEL);
    text(40, 121, label);
    text(160, 121, &digits[first..]);
}
