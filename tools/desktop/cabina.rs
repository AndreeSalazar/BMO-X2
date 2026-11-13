use super::{fill, invoke};

const DIAGNOSTICS: u64 = 3;
const READ: u64 = 3;
const INK: u32 = 0xe7efff;
const PANEL: u32 = 0x232638;

// Rasterized from BMO-X's bmo-letra. See CABINA-FONT.md for provenance.
const CHARACTERS: &[u8] = b"0123456789ABCDEFGHIKLMNOPRSTUVYZJ";
const ATLAS: &[u8; CHARACTERS.len() * 37] = include_bytes!("cabina_font.bin");
const SHADES: [u32; 4] = [PANEL, 0x64697a, 0xa5acbc, INK];
const FIELDS: [(u8, &[u8], &[u8]); 3] = [
    (0x14, b"T TICKS", b"PULSOS DEL RELOJ PIT"),
    (0x12, b"E EVENTOS", b"ESPERAS CON ENTRADA LISTA"),
    (0x2f, b"V VENCIMIENTOS", b"ESPERAS SIN ENTRADA AL VENCER"),
];

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
    fill(24, 24, 592, 194, PANEL);
    text(40, 42, b"CABINA RING 0");
    text(40, 68, b"CONTADOR");
    text(168, 68, b"VALOR");
    text(272, 68, b"SIGNIFICADO");
    fill(40, 86, 560, 1, 0x40465d);
    for (field, (_, label, description)) in FIELDS.iter().enumerate() {
        let y = row(field);
        text(40, y, label);
        text(272, y, description);
        refresh(field);
    }
    text(40, 188, b"R ACTUALIZAR TODO   F2 CERRAR");
}

pub fn command(scancode: u8) {
    if scancode == 0x13 {
        for field in 0..FIELDS.len() {
            refresh(field);
        }
    } else if let Some(field) = FIELDS.iter().position(|&(key, _, _)| key == scancode) {
        refresh(field);
    }
}

fn row(field: usize) -> u64 {
    100 + field as u64 * 24
}

fn refresh(field: usize) {
    let mut value = invoke(DIAGNOSTICS, READ, field as u64, 0);
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
    let y = row(field);
    fill(168, y, 100, 12, PANEL);
    text(168, y, &digits[first..]);
}
