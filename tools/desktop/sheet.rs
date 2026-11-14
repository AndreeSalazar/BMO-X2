use super::Clip;
#[cfg(not(desktop_ultra_j))]
use super::{cabina, fill};

pub const TILE: Clip = Clip { left: 52, top: 48, right: 104, bottom: 94 };

pub fn icon(clip: Clip) {
    clip.fill(52, 48, 52, 46, 0x232638);
    #[cfg(desktop_ultra_j)]
    {
        clip.fill(62, 55, 32, 30, 0xa8c5ff);
        clip.fill(69, 61, 4, 17, 0x172746);
        clip.fill(73, 74, 6, 4, 0x172746);
        clip.fill(79, 61, 4, 17, 0x172746);
        clip.fill(86, 61, 3, 17, 0x172746);
    }
    #[cfg(not(desktop_ultra_j))]
    {
        clip.fill(68, 53, 20, 32, 0xe7efff);
        for y in [62, 68, 74] {
            clip.fill(72, y, 12, 2, 0x5b7394);
        }
    }
}

#[cfg(desktop_ultra_j)]
unsafe extern "C" {
    fn ultra_j_draw(active: u32);
    fn ultra_j_action() -> u32;
}

#[cfg(desktop_ultra_j)]
pub fn show() {
    unsafe { ultra_j_draw(0); }
}

#[cfg(desktop_ultra_j)]
pub fn activate() {
    unsafe { ultra_j_draw(ultra_j_action()); }
}

#[cfg(not(desktop_ultra_j))]
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
