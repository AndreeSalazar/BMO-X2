use super::{Clip, cabina, fill};

pub const TILE: Clip = Clip { left: 52, top: 48, right: 104, bottom: 94 };

pub fn icon(clip: Clip) {
    clip.fill(52, 48, 52, 46, 0x232638);
    clip.fill(68, 53, 20, 32, 0xe7efff);
    for y in [62, 68, 74] {
        clip.fill(72, y, 12, 2, 0x5b7394);
    }
}

pub fn show() {
    fill(0, 0, 640, 400, 0x0d0e17);
    fill(118, 44, 404, 312, 0x232638);
    cabina::text(140, 56, b"HOJA   ESC PARA CERRAR");
    fill(140, 83, 360, 250, 0xe7efff);
    fill(165, 104, 1, 209, 0xb58c9b);
    for y in (115..321).step_by(22) {
        fill(148, y, 344, 1, 0xb1c1d8);
    }
}
