use bmo_x2_desktop::{Desktop, Frame, Keyboard, Surface, Workspace};
use std::io::{self, BufRead, Write};

const WIDTH: usize = 432;
const HEIGHT: usize = 248;
const ACCENTS: [u32; 4] = [0x5ad8ff, 0xad92ff, 0x6ee7b7, 0xff7c98];

fn rectangle<const W: usize>(
    pixels: &mut [u32],
    x: usize,
    y: usize,
    width: usize,
    height: usize,
    color: u32,
) {
    for row in y..y + height {
        pixels[row * W + x..row * W + x + width].fill(color);
    }
}

fn panel<const W: usize, const H: usize>(accent: u32) -> Vec<u32> {
    let mut pixels = vec![0x171825; W * H];
    rectangle::<W>(&mut pixels, 0, 0, W, 1, accent);
    rectangle::<W>(&mut pixels, 0, 1, W, 19, 0x222334);
    rectangle::<W>(&mut pixels, 8, 8, 4, 4, accent);
    for line in 0..4 {
        let width = (W - 28) * [3, 2, 4, 1][line] / 5;
        rectangle::<W>(&mut pixels, 12, 40 + 10 * line, width, 2, 0x3b4159);
    }
    pixels
}

fn present(
    desktop: &Desktop<'_, 8>,
    pixels: &mut [u32],
    bytes: &mut Vec<u8>,
    output: &mut impl Write,
) -> io::Result<()> {
    let mut frame = Frame::new(WIDTH, HEIGHT, pixels).unwrap();
    desktop.compose(&mut frame, 0x0d0e17);
    let active = desktop.active().number();
    let focused = desktop.focused_shortcut().unwrap_or(0);
    if let Some(id) = desktop.focused() {
        let (x, y, w, h) = if id % 2 == 1 {
            (30, 75, 238, 114)
        } else {
            (278, 111, 138, 92)
        };
        let accent = ACCENTS[usize::from(active - 1)];
        rectangle::<WIDTH>(pixels, x, y, 1, h, accent);
        rectangle::<WIDTH>(pixels, x + w - 1, y, 1, h, accent);
        rectangle::<WIDTH>(pixels, x, y + h - 1, w, 1, accent);
    }
    rectangle::<WIDTH>(pixels, 0, 0, WIDTH, 23, 0x161722);
    for (index, &accent) in ACCENTS.iter().enumerate() {
        let x = 170 + index * 24;
        let color = if index + 1 == usize::from(active) {
            accent
        } else {
            0x3b4159
        };
        rectangle::<WIDTH>(pixels, x, 21, 19, 2, color);
    }
    bytes.clear();
    bytes.extend_from_slice(&[active, focused]);
    for pixel in pixels {
        bytes.extend_from_slice(&pixel.to_le_bytes());
    }
    output.write_all(bytes)?;
    output.flush()
}

fn main() -> io::Result<()> {
    let cards = ACCENTS.map(|color| (panel::<238, 114>(color), panel::<138, 92>(color)));
    let mut desktop = Desktop::<8>::new();
    for (index, (main, side)) in cards.iter().enumerate() {
        let workspace = index as u8 + 1;
        desktop.switch(Workspace::new(workspace).unwrap());
        desktop
            .open(
                u32::from(workspace) * 2 - 1,
                30,
                75,
                Surface::new(238, 114, main).unwrap(),
            )
            .unwrap();
        desktop
            .open(
                u32::from(workspace) * 2,
                278,
                111,
                Surface::new(138, 92, side).unwrap(),
            )
            .unwrap();
        desktop.focus_shortcut(1);
    }
    desktop.switch(Workspace::FIRST);
    let mut keyboard = Keyboard::default();
    let mut output = io::stdout().lock();
    let mut pixels = vec![0; WIDTH * HEIGHT];
    let mut bytes = Vec::with_capacity(2 + WIDTH * HEIGHT * 4);
    present(&desktop, &mut pixels, &mut bytes, &mut output)?;
    for line in io::stdin().lock().lines() {
        let line = line?;
        let mut fields = line.split_whitespace();
        let Some(scancode) = fields.next().and_then(|field| field.parse::<u8>().ok()) else {
            break;
        };
        let modifiers = fields
            .next()
            .and_then(|field| field.parse::<u8>().ok())
            .unwrap_or(0);
        let press = u64::from(scancode) | 0x300;
        let release = u64::from(scancode) | 0x100;
        let _ = keyboard.handle(&mut desktop, press, modifiers);
        let _ = keyboard.handle(&mut desktop, release, modifiers);
        present(&desktop, &mut pixels, &mut bytes, &mut output)?;
    }
    Ok(())
}
