use bmo_letra::{Fuente, LetraFija, Peso};
use std::io::{self, Write};

fn main() -> io::Result<()> {
    let mut font = Box::new(LetraFija::<4096, 64>::nueva());
    let mut output = io::stdout().lock();
    for character in b"0123456789ABCDEFGIKMNOPRSTUV" {
        let glyph = font.glifo(*character, 11, Peso::Media, 0).unwrap();
        let advance = ((glyph.avance64 + 32) / 64).clamp(4, 9);
        let mut rows = [0u32; 12];
        for y in 0..glyph.h {
            for x in 0..glyph.w {
                let coverage = u32::from(glyph.alfa[(y * glyph.w + x) as usize]);
                let shade = (coverage * 3 + 127) / 255;
                if shade != 0 {
                    let (column, row) = (x + glyph.x + 1, y + glyph.y + 9);
                    assert!(
                        (0..12).contains(&column) && (0..12).contains(&row),
                        "Glyph {} at ({column},{row})",
                        char::from(*character)
                    );
                    rows[row as usize] |= shade << (column * 2);
                }
            }
        }
        output.write_all(&[advance as u8])?;
        for row in rows {
            output.write_all(&row.to_le_bytes()[..3])?;
        }
    }
    Ok(())
}
