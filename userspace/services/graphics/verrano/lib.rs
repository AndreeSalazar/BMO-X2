#![no_std]
#![forbid(unsafe_code)]

/// Resource metadata from the service's allocation table.
pub struct Buffer {
    pub owner: u64,
    pub bytes: u64,
}

pub struct Draw {
    pub buffer: usize,
    pub offset: u64,
    pub stride: u64,
    pub vertices: u32,
}

pub struct Limits {
    pub draws: usize,
    pub vertices: u32,
}

#[derive(Debug, PartialEq, Eq)]
pub enum Rejection {
    DrawCount,
    VertexCount(usize),
    Buffer(usize),
    Owner(usize),
    Range(usize),
}

/// The caller supplies the authenticated owner and allocation table.
/// The backend receives the batch once all draws have passed admission.
pub fn submit<T>(
    owner: u64,
    buffers: &[Buffer],
    draws: &[Draw],
    limits: Limits,
    backend: impl FnOnce(&[Draw], &[Buffer]) -> T,
) -> Result<T, Rejection> {
    if draws.is_empty() || draws.len() > limits.draws {
        return Err(Rejection::DrawCount);
    }
    let mut remaining = limits.vertices;
    for (index, draw) in draws.iter().enumerate() {
        if draw.vertices == 0 || draw.vertices > remaining {
            return Err(Rejection::VertexCount(index));
        }
        remaining -= draw.vertices;
        let buffer = buffers.get(draw.buffer).ok_or(Rejection::Buffer(index))?;
        if buffer.owner != owner {
            return Err(Rejection::Owner(index));
        }
        // Each vertex occupies a complete stride in this profile.
        let end = draw.stride.checked_mul(u64::from(draw.vertices))
            .and_then(|bytes| draw.offset.checked_add(bytes));
        if draw.stride == 0 || end.is_none_or(|end| end > buffer.bytes) {
            return Err(Rejection::Range(index));
        }
    }
    Ok(backend(draws, buffers))
}

#[cfg(test)]
mod tests {
    use super::*;

    const BUFFERS: [Buffer; 2] = [Buffer { owner: 1, bytes: 48 }, Buffer { owner: 2, bytes: 48 }];
    const LIMITS: Limits = Limits { draws: 2, vertices: 4 };
    const TRIANGLE: Draw = Draw { buffer: 0, offset: 0, stride: 16, vertices: 3 };

    #[test]
    fn valid_triangle_reaches_backend_at_exact_buffer_boundary() {
        assert_eq!(
            submit(1, &BUFFERS, &[TRIANGLE], LIMITS, |draws, _| draws[0].vertices),
            Ok(3),
        );
    }

    #[test]
    fn second_draw_outside_buffer_blocks_the_entire_batch() {
        let invalid = Draw { offset: 48, vertices: 1, ..TRIANGLE };
        assert_eq!(
            submit(1, &BUFFERS, &[TRIANGLE, invalid], LIMITS, |_, _| panic!("submitted")),
            Err(Rejection::Range(1)),
        );
    }

    #[test]
    fn rejects_foreign_buffers_overflow_and_excess_work() {
        let cases = [
            (Draw { buffer: 1, ..TRIANGLE }, Rejection::Owner(0)),
            (Draw { buffer: 2, ..TRIANGLE }, Rejection::Buffer(0)),
            (Draw { stride: u64::MAX, ..TRIANGLE }, Rejection::Range(0)),
            (Draw { offset: u64::MAX, ..TRIANGLE }, Rejection::Range(0)),
            (Draw { stride: 0, ..TRIANGLE }, Rejection::Range(0)),
            (Draw { vertices: 5, ..TRIANGLE }, Rejection::VertexCount(0)),
        ];
        for (draw, expected) in cases {
            assert_eq!(
                submit(1, &BUFFERS, &[draw], LIMITS, |_, _| panic!("submitted")),
                Err(expected),
            );
        }
    }
}
