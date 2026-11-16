// Presentation only. Values come from the existing diagnostic capability.
use super::{cabina::text, fill, invoke};
const PANEL: u32 = 0x232638;

pub fn show(code: u32) {
    fill(24, 254, 592, 92, PANEL);
    let color = match code {
        8 | 28 => 0xffd166, // A milestone, never a claim of working physical HID.
        1..=7 => 0x5ad8ff,
        9..=27 | 29 => 0xff6b7a,
        _ => 0x64697a,
    };
    fill(24, 254, 3, 92, color);
    text(36, 264, b"REPORTES   ENTRADA");
    text(382, 264, b"PULSOS");
    let (reason, next): (&[u8], &[u8]) = match code {
        8 => (b"TRANSPORTE DMA COMPROBADO", b"DIRECCIONAR Y LEER DESCRIPTORES"),
        28 => (b"DESCRIPTORES LEIDOS   HID PENDIENTE", b"CONFIGURAR INTERFACES Y ENDPOINTS"),
        20..=22 => (b"ENUMERACION NO COMPLETADA", b"REVISAR PUERTO Y CONTEXTOS"),
        23..=27 => (b"EP0 NO COMPLETO LA FASE", b"REVISAR MPS Y TERMINACION USB"),
        9..=19 | 29 => (b"TRANSPORTE NO COMPLETADO", b"REVISAR DMA ENTREGA Y RELOJ"),
        _ => (b"SIN ENUMERACION HID CONFIRMADA", b"CONSULTAR PERFIL Y REPORTE HOST"),
    };
    text(36, 286, b"MOTIVO");
    text(110, 286, reason);
    text(36, 308, b"SIGUE");
    text(110, 308, next);
    text(36, 330, b"FUENTE RING 0   VISTA RING 3   SIN ESCRITURA A DISCO");
}

pub fn pulse(previous: u32) -> u32 {
    let now = invoke(3, 3, 0, 0);
    if now.wrapping_sub(previous) >= 25 {
        let mut digits = [b'0'; 10];
        let mut value = now;
        for digit in digits.iter_mut().rev() {
            *digit += (value % 10) as u8;
            value /= 10;
        }
        fill(470, 264, 130, 12, PANEL);
        text(470, 264, &digits);
        now
    } else {
        previous
    }
}
