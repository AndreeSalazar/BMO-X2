use super::{Clip, cabina, fill};

const PANEL: u32 = 0x232638;
const INK: u32 = 0xe7efff;
const ACCENT: u32 = 0x5ad8ff;
pub const BUTTON: Clip = Clip { left: 588, top: 352, right: 624, bottom: 388 };

pub fn icon(clip: Clip) {
    clip.fill(BUTTON.left, BUTTON.top, 36, 36, PANEL);
    for (x, y, w, h) in [(603, 359, 6, 22), (595, 367, 22, 6),
                          (598, 362, 16, 16)] {
        clip.fill(x, y, w, h, INK);
    }
    clip.fill(603, 367, 6, 6, PANEL);
}

pub fn hit(x: i16, y: i16) -> bool {
    (588..624).contains(&x) && (352..388).contains(&y)
}

pub fn show(speed: i16, usb_pending: bool) {
    fill(0, 0, 640, 400, 0x0d0e17);
    fill(24, 24, 592, 162, PANEL);
    cabina::text(40, 42, b"CONFIGURACION");
    cabina::text(40, 74, b"PUNTERO   1 NORMAL   2 RAPIDO");
    fill(if speed == 1 { 40 } else { 140 }, 90, 40, 2, ACCENT);
    let input: &[u8] = if usb_pending { b"USB XHCI DETECTADO   ENTRADA PENDIENTE" }
        else { b"ENTRADA PS2" };
    cabina::text(40, 108, input);
    cabina::text(40, 148, b"ESC O F3 PARA VOLVER");
}
