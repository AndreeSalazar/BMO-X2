use super::{fill, invoke};

const DIAGNOSTICS: u64 = 3;
const READ: u64 = 3;
const INK: u32 = 0xe7efff;
const PANEL: u32 = 0x232638;

// Rasterized from BMO-X's bmo-letra. See CABINA-FONT.md for provenance.
const CHARACTERS: &[u8] = b"0123456789ABCDEFGIKMNOPRSTUV";
const ATLAS: &[u8; 1036] = include_bytes!("cabina_font.bin");
const SHADES: [u32; 4] = [PANEL, 0x64697a, 0xa5acbc, INK];

fn text(mut x: u64, y: u64, bytes: &[u8]) {
    for byte in bytes {
        let Some(index) = CHARACTERS.iter().position(|c| c == byte) else {
            x += 4;
            continue;
        };
        let glyph = &ATLAS[index * 37..][..37];
        for (row, mask) in glyph[1..].chunks_exact(3).enumerate() {
            let mut bits = u32::from_le_bytes([mask[0], mask[1], mask[2], 0]);
            let mut column = 0;
            while bits != 0 {
                let shade = bits & 3;
                let mut width = 1;
                bits >>= 2;
                while bits != 0 && bits & 3 == shade {
                    bits >>= 2;
                    width += 1;
                }
                if shade != 0 {
                    fill(x + column, y + row as u64, width, 1, SHADES[shade as usize]);
                }
                column += width;
            }
        }
        x += u64::from(glyph[0]);
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
