//! Short, skippable Ring 3 welcome after SBEF and permission checks.
use super::{cabina, fill, invoke, wait_input, INPUT, READ_INPUT};

const MINT: u32 = 0x7de3d2;
// Five columns, seven rows, low bit first. Independent of privileged boot art.
const MARK: [u64; 5] = [
    0b11110_10001_10001_11110_10001_10001_11110, // B
    0b10001_10001_10001_10101_10101_11011_10001, // M
    0b01110_10001_10001_10001_10001_10001_01110, // O
    0b10001_10001_01010_00100_01010_10001_10001, // X
    0b11111_01000_00100_00010_00001_10001_01110, // 2
];

/// Preserve the first input byte for the normal desktop decoder, including mouse/prefix bytes.
pub fn run() -> Option<u32> {
    fill(0, 0, 640, 400, 0x0b1019);
    fill(112, 72, 416, 248, 0x131e2a);
    fill(112, 72, 416, 1, 0x2b3b4c);
    for (index, glyph) in MARK.iter().enumerate() {
        let left = 208 + index as u64 * 44 + if index > 2 { 8 } else { 0 };
        for bit in 0..35 {
            if glyph & (1 << bit) != 0 {
                fill(left + (4-bit%5)*6, 126 + bit/5*6, 5, 5, MINT);
            }
        }
    }
    cabina::text(238, 102, b"BMO X2   RING 3");
    cabina::text(206, 206, b"CONTROL RENDIMIENTO ELEGANCIA");
    cabina::text(234, 292, b"UNA TECLA PARA ENTRAR");
    for phase in 0..3 {
        fill(192 + phase*88, 258, 80, 3, MINT);
        let started = invoke(3, 3, 0, 0);
        // Absolute per-phase budget; boot ACKs are not user input.
        // Bound even repeated protocol replies, and sleep between reads.
        for _ in 0..8 {
            let elapsed = invoke(3, 3, 0, 0).wrapping_sub(started);
            if elapsed >= 18 { break; }
            let reply = wait_input(u64::from(18-elapsed));
            if reply != 0 && reply != 256 { return None; }
            let raw = invoke(INPUT, READ_INPUT, 0, 0);
            if raw != 256 && !matches!(raw & 255, 0xfa | 0xfe) {
                return Some(raw);
            }
        }
    }
    None
}
