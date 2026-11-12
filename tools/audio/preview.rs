use bmo_x2_audio::{Gain, Source, Stereo, mix};
use std::env;
use std::fs::File;
use std::io::{self, BufWriter, Write};

const RATE: u32 = 48_000;
const BLOCK: usize = 240;
const BLOCKS_PER_SECTION: usize = 80;
const SECTIONS: usize = 4;

fn tone(frame: usize, period: usize, amplitude: i16) -> i16 {
    let phase = (frame % period) as i32;
    let half = period as i32 / 2;
    let triangle = half - (phase - half).abs();
    ((2 * triangle - half) * i32::from(amplitude) / half) as i16
}

fn main() -> io::Result<()> {
    let path = env::args_os()
        .nth(1)
        .ok_or_else(|| io::Error::new(io::ErrorKind::InvalidInput, "Indicar ruta para el WAV"))?;
    let mut file = BufWriter::new(File::create(path)?);
    let data_bytes = (BLOCK * BLOCKS_PER_SECTION * SECTIONS * 4) as u32;
    file.write_all(b"RIFF")?;
    file.write_all(&(36 + data_bytes).to_le_bytes())?;
    file.write_all(b"WAVEfmt ")?;
    file.write_all(&16u32.to_le_bytes())?;
    for field in [1u16, 2] {
        file.write_all(&field.to_le_bytes())?;
    }
    file.write_all(&RATE.to_le_bytes())?;
    file.write_all(&(RATE * 4).to_le_bytes())?;
    for field in [4u16, 16] {
        file.write_all(&field.to_le_bytes())?;
    }
    file.write_all(b"data")?;
    file.write_all(&data_bytes.to_le_bytes())?;

    let left = [Gain::UNITY, Gain::MUTE];
    let right = [Gain::MUTE, Gain::UNITY];
    let mut a: [Stereo; BLOCK] = [[0; 2]; BLOCK];
    let mut b = a;
    let mut output = a;
    let mut bytes = [0; BLOCK * 4];
    for (gain_a, gain_b, master) in [
        (left, [Gain::MUTE; 2], Gain::UNITY),
        ([Gain::MUTE; 2], right, Gain::UNITY),
        (left, right, Gain::percent(50).unwrap()),
        (left, right, Gain::MUTE),
    ] {
        for block in 0..BLOCKS_PER_SECTION {
            for i in 0..BLOCK {
                let frame = block * BLOCK + i;
                let remaining = BLOCK * BLOCKS_PER_SECTION - 1 - frame;
                let ramp = frame.min(remaining).min(BLOCK) as i32;
                a[i] = [(i32::from(tone(frame, 120, 8000)) * ramp / BLOCK as i32) as i16; 2];
                b[i] = [(i32::from(tone(frame, 80, 6000)) * ramp / BLOCK as i32) as i16; 2];
            }
            let sources = [
                Source {
                    frames: &a,
                    gain: gain_a,
                },
                Source {
                    frames: &b,
                    gain: gain_b,
                },
            ];
            let meter = mix(&mut output, &sources, master).unwrap();
            if meter.clipped_samples != 0 {
                return Err(io::Error::other("La sonda de audio saturo"));
            }
            for (chunk, [l, r]) in bytes.chunks_exact_mut(4).zip(output) {
                chunk[..2].copy_from_slice(&l.to_le_bytes());
                chunk[2..].copy_from_slice(&r.to_le_bytes());
            }
            file.write_all(&bytes)?;
        }
    }
    file.flush()
}
