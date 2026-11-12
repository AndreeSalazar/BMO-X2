#![no_std]
#![forbid(unsafe_code)]

/// A gain in percent, bounded to unity.
#[derive(Clone, Copy)]
pub struct Gain(u8);

impl Gain {
    pub const UNITY: Self = Self(100);
    pub const MUTE: Self = Self(0);

    pub const fn percent(value: u8) -> Option<Self> {
        if value <= 100 {
            Some(Self(value))
        } else {
            None
        }
    }
}

pub type Stereo = [i16; 2];

pub struct Source<'a> {
    pub frames: &'a [Stereo],
    /// Independent gains allow balance and mute without rewriting the source.
    pub gain: [Gain; 2],
}

#[derive(Debug, Default, PartialEq, Eq)]
pub struct Meter {
    pub peak: [u16; 2],
    pub clipped_samples: u64,
}

pub const MAX_SOURCES: usize = 16;

#[derive(Debug, PartialEq, Eq)]
pub struct TooManySources;

/// Mix one block at the output rate. A short source contributes silence
/// after its last frame. The caller supplies all buffers.
pub fn mix(
    output: &mut [Stereo],
    sources: &[Source<'_>],
    master: Gain,
) -> Result<Meter, TooManySources> {
    if sources.len() > MAX_SOURCES {
        return Err(TooManySources);
    }
    if master.0 == 0 {
        output.fill([0; 2]);
        return Ok(Meter::default());
    }
    let mut meter = Meter::default();
    for (index, frame) in output.iter_mut().enumerate() {
        let mut sum = [0i32; 2];
        for source in sources {
            if let Some(sample) = source.frames.get(index) {
                for channel in 0..2 {
                    sum[channel] += i32::from(sample[channel]) * i32::from(source.gain[channel].0);
                }
            }
        }
        for channel in 0..2 {
            let scaled = sum[channel] * i32::from(master.0) / 10_000;
            let clipped = scaled.clamp(i32::from(i16::MIN), i32::from(i16::MAX));
            frame[channel] = clipped as i16;
            meter.clipped_samples += u64::from(clipped != scaled);
            meter.peak[channel] = meter.peak[channel].max(frame[channel].unsigned_abs());
        }
    }
    Ok(meter)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn balances_sources_and_reports_saturation() {
        let frames = [[30_000, -30_000], [-32_768, 10]];
        let sources = [
            Source {
                frames: &frames,
                gain: [Gain::UNITY; 2],
            },
            Source {
                frames: &frames[..1],
                gain: [Gain::percent(50).unwrap(), Gain::MUTE],
            },
        ];
        let mut output = [[1; 2]; 3];
        let meter = mix(&mut output, &sources, Gain::UNITY).unwrap();
        assert_eq!(output, [[32_767, -30_000], [-32_768, 10], [0, 0]]);
        assert_eq!(
            meter,
            Meter {
                peak: [32_768, 30_000],
                clipped_samples: 1
            }
        );
        assert_eq!(mix(&mut output, &sources, Gain::MUTE), Ok(Meter::default()));
        assert_eq!(output, [[0; 2]; 3]);
    }

    #[test]
    fn master_attenuates_before_saturation_at_maximum_source_count() {
        let frames = [[32_767, -32_768]];
        let sources = core::array::from_fn::<_, MAX_SOURCES, _>(|_| Source {
            frames: &frames,
            gain: [Gain::UNITY; 2],
        });
        let mut output = [[0; 2]];
        let meter = mix(&mut output, &sources, Gain::percent(5).unwrap()).unwrap();
        assert_eq!(output, [[26_213, -26_214]]);
        assert_eq!(meter.clipped_samples, 0);
        assert!(Gain::percent(101).is_none());
    }

    #[test]
    fn rejects_excess_sources_before_writing() {
        let sources = core::array::from_fn::<_, { MAX_SOURCES + 1 }, _>(|_| Source {
            frames: &[],
            gain: [Gain::UNITY; 2],
        });
        let mut output = [[12, -12]];
        assert_eq!(mix(&mut output, &sources, Gain::UNITY), Err(TooManySources));
        assert_eq!(output, [[12, -12]]);
        assert_eq!(mix(&mut output, &[], Gain::UNITY), Ok(Meter::default()));
        assert_eq!(output, [[0; 2]]);
    }
}
