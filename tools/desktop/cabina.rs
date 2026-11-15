use super::{fill, invoke};

const DIAGNOSTICS: u64 = 3;
const READ: u64 = 3;
const INK: u32 = 0xe7efff;
const PANEL: u32 = 0x232638;

// Rasterized from BMO-X's bmo-letra. See CABINA-FONT.md for provenance.
const CHARACTERS: &[u8] = b"0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ";
const ATLAS: &[u8; CHARACTERS.len() * 37] = include_bytes!("cabina_font.bin");
const SHADES: [u32; 4] = [PANEL, 0x64697a, 0xa5acbc, INK];
const FIELDS: [(u8, &[u8], &[u8]); 3] = [
    (0x14, b"T TICKS", b"PULSOS DEL RELOJ PIT"),
    (0x12, b"E EVENTOS", b"ESPERAS CON ENTRADA LISTA"),
    (0x2f, b"V VENCIMIENTOS", b"ESPERAS SIN ENTRADA AL VENCER"),
];

pub(super) fn text(mut x: u64, y: u64, bytes: &[u8]) {
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
    fill(24, 24, 592, 226, PANEL);
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
    text(40, 210, b"DOOM RUN");
    #[cfg(external_session)]
    text(136, 210, b"SESSION EXIT");
    prompt(b"");
}

#[cfg(all(external_session, not(usb_probe), not(desktop_sheet)))]
#[inline(never)]
pub fn boot_input(controllers: u32, keyboard: bool, mouse: bool) {
    fill(24, 354, 548, 32, PANEL);
    let status = match invoke(3, 3, 6, 0) {
        1 => b"XHCI OCUPADO".as_slice(),
        2 => b"XHCI PAGINA NO ADMISIBLE",
        3 => b"XHCI DETENIDO",
        4 => b"XHCI ACTIVO",
        5 => b"XHCI SIN ENTREGA UEFI",
        6 => b"XHCI FALLO REINICIO",
        7 => b"XHCI REINICIO OK",
        _ => b"XHCI SIN ESTADO",
    };
    text(36, 359, status);
    let ports = invoke(3, 3, 7, 0);
    let surveyed = (1..=256).contains(&ports);
    text(260, 359, if surveyed { b"USB PUERTOS".as_slice() } else { b"XHCI" });
    let mut count = [b'0'; 5];
    let mut value = if surveyed { ports - 1 } else { controllers };
    for digit in count.iter_mut().rev() {
        *digit += (value % 10) as u8;
        value /= 10;
    }
    let start = count.iter().position(|&digit| digit != b'0').unwrap_or(4);
    text(if surveyed { 360 } else { 303 }, 359, &count[start..]);
    text(36, 372, if keyboard { b"TECLADO PS2 OK" } else { b"TECLADO PS2 ESPERA" });
    text(260, 372, if mouse { b"RATON PS2 OK" } else { b"RATON PS2 ESPERA" });
}

pub fn diagnostic(scancode: u8) {
    if scancode == 0x13 {
        for field in 0..FIELDS.len() {
            refresh(field);
        }
    } else if let Some(field) = FIELDS.iter().position(|&(key, _, _)| key == scancode) {
        refresh(field);
    }
}

fn prompt(input: &[u8]) {
    fill(40, 228, 560, 12, PANEL);
    text(40, 228, input);
    fill(40, 240, 32, 1, 0x5ad8ff);
}

#[derive(Default)]
pub struct Command {
    bytes: [u8; 24],
    len: usize,
    active: bool,
}

impl Command {
    pub fn key(&mut self, scan: u8) -> bool {
        if scan == 0x1c {
            let command = self.bytes[..self.len].trim_ascii();
            #[cfg(external_session)]
            if command == b"SESSION EXIT" {
                prompt(b"CERRANDO SESION");
                invoke(0, 8, 0, 0);
                prompt(b"CIERRE DENEGADO");
                *self = Self::default();
                return false;
            }
            let launch = self.active && command == b"DOOM RUN";
            let message: &[u8] = if launch {
                if cfg!(desktop_doom) { b"INICIANDO DOOM" } else { b"DOOM REQUIERE EL PERFIL CON IWAD" }
            } else if self.active {
                b"COMANDO INVALIDO"
            } else {
                b""
            };
            *self = Self::default();
            prompt(message);
            return launch;
        }
        if !self.active && matches!(scan, 0x13 | 0x14 | 0x12 | 0x2f) {
            diagnostic(scan);
            return false;
        }
        if scan == 0x0e {
            self.len = self.len.saturating_sub(1);
        } else {
            let row = match scan {
                0x10..=0x19 => b"QWERTYUIOP"[usize::from(scan - 0x10)],
                0x1e..=0x26 => b"ASDFGHJKL"[usize::from(scan - 0x1e)],
                0x2c..=0x32 => b"ZXCVBNM"[usize::from(scan - 0x2c)],
                0x39 => b' ',
                _ => return false,
            };
            if self.len < self.bytes.len() {
                self.bytes[self.len] = row;
                self.len += 1;
                self.active = true;
            }
        }
        prompt(&self.bytes[..self.len]);
        false
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
