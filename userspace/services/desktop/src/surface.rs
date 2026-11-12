/// An opaque XRGB8888 surface in tightly packed rows.
#[derive(Clone, Copy)]
pub struct Surface<'a> {
    width: usize,
    height: usize,
    pixels: &'a [u32],
}

impl<'a> Surface<'a> {
    pub fn new(width: usize, height: usize, pixels: &'a [u32]) -> Option<Self> {
        if width == 0 || height == 0 || width.checked_mul(height)? != pixels.len() {
            return None;
        }
        Some(Self {
            width,
            height,
            pixels,
        })
    }
}

/// The caller owns the back buffer and decides how to present it.
pub struct Frame<'a> {
    width: usize,
    height: usize,
    pixels: &'a mut [u32],
}

impl<'a> Frame<'a> {
    pub fn new(width: usize, height: usize, pixels: &'a mut [u32]) -> Option<Self> {
        if width == 0 || height == 0 || width.checked_mul(height)? != pixels.len() {
            return None;
        }
        Some(Self {
            width,
            height,
            pixels,
        })
    }

    pub(crate) fn clear(&mut self, color: u32) {
        self.pixels.fill(color);
    }

    pub(crate) fn blit(&mut self, surface: Surface<'_>, x: i32, y: i32) {
        let (sx, dx, width) = clip_axis(x, surface.width, self.width);
        let (sy, dy, height) = clip_axis(y, surface.height, self.height);
        if width == 0 || height == 0 {
            return;
        }
        for row in 0..height {
            let source = (sy + row) * surface.width + sx;
            let target = (dy + row) * self.width + dx;
            self.pixels[target..target + width]
                .copy_from_slice(&surface.pixels[source..source + width]);
        }
    }
}

fn clip_axis(offset: i32, source: usize, target: usize) -> (usize, usize, usize) {
    let from = if offset < 0 {
        offset.unsigned_abs() as usize
    } else {
        0
    };
    let to = offset.max(0) as usize;
    let length = source.saturating_sub(from).min(target.saturating_sub(to));
    (from, to, length)
}
