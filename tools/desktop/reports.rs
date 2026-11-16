// Presentation only. Values come from the existing diagnostic capability.
use super::{cabina::text, fill, invoke, invoke_word};
const PANEL: u32 = 0x232638;

pub fn show(code: u32) {
    fill(24, 254, 592, 98, PANEL);
    let color = match code {
        8 | 28 => 0xffd166, // A milestone, never a claim of working physical HID.
        1..=7 => 0x5ad8ff,
        9..=27 | 29 => 0xff6b7a,
        _ => 0x64697a,
    };
    fill(24, 254, 3, 98, color);
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
    if (23..=28).contains(&code) {
        let words = invoke_word(3, 3, 8, 0);
        let head = invoke_word(3, 3, 10, 0);
        let port = invoke(3, 3, 11, 0);
        for (x, label, value, digits) in [
            (36, b"P".as_slice(), u64::from(port & 255), 2),
            (110, b"S", u64::from(port >> 8 & 255), 2),
            (180, b"CC", words >> 24 & 255, 2),
            (266, b"LEFT", words & 0xffffff, 6),
            (400, b"REQ", u64::from(port >> 16), 4),
            (514, b"MPS", head >> 56, 2),
        ] {
            text(x, 322, label);
            hex(x + if label.len() == 1 { 18 } else { 40 }, 322, value, digits);
        }
        text(36, 338, b"HEAD");
        hex(80, 338, head, 16);
        text(264, 338, b"PTR");
        hex(304, 338, invoke_word(3, 3, 9, 0), 8);
        text(422, 338, b"EXP");
        hex(462, 338, invoke_word(3, 3, 12, 0), 8);
    } else {
        text(36, 330, b"DETALLE EP0 AUN NO DISPONIBLE");
    }
}

fn hex(x: u64, y: u64, mut value: u64, count: usize) {
    let mut buffer = [b'0'; 16];
    for byte in buffer[..count].iter_mut().rev() {
        *byte = b"0123456789ABCDEF"[(value & 15) as usize];
        value >>= 4;
    }
    text(x, y, &buffer[..count]);
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
