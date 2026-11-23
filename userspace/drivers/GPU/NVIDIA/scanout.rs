#![no_std]
#![forbid(unsafe_code)]

// NVD_40 / C67E. See NVIDIA open-gpu-doc, classes/display/clc67e.h.
// A core channel must already bind this window at (0,0) to the active head.
// The DMA handle must refer to a pitch-linear, GPU-readable VRAM context.
const SET_PRESENT_CONTROL: u32 = 0x308;
const SET_SIZE: u32 = 0x224;
const SET_CONTEXT_DMA_ISO: u32 = 0x240;
const SET_OFFSET: u32 = 0x260;
const SET_POINT_IN: u32 = 0x290;
const SET_SIZE_IN: u32 = 0x298;
const SET_SIZE_OUT: u32 = 0x2a4;
const SET_CONTEXT_DMA_NOTIFIER: u32 = 0x21c;
const SET_INTERLOCK_FLAGS: u32 = 0x370;
const UPDATE: u32 = 0x200;
const X8R8G8B8: u32 = 0xe6;
const ADDRESS_LIMIT: u64 = 1 << 40;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Extent {
    pub width: u16,
    pub height: u16,
}

#[derive(Clone, Copy, Debug)]
pub struct VramFrame {
    pub extent: Extent,
    pub pitch_bytes: u32,
    pub offset_bytes: u64,
}

#[derive(Clone, Copy, Debug)]
pub struct DisplayContext {
    pub handle: u32,
    pub len_bytes: u64,
}

#[derive(Clone, Copy, Debug)]
pub struct FlipNotifier {
    pub handle: u32,
    pub len_bytes: u64,
    pub offset_bytes: u16,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum ScanoutError {
    Geometry,
    Pitch,
    Context,
    Offset,
    Range,
    Notifier,
}

/// Encode one C67E flip on an already configured head with no concurrent modeset.
/// After the rendering fence, submit this packet with a freshly reset, dedicated
/// GPU-writable notifier. Keep the old buffer pinned until the display engine
/// releases it.
pub fn flip_methods(
    head: Extent,
    frame: VramFrame,
    context: DisplayContext,
    notifier: FlipNotifier,
) -> Result<[u32; 26], ScanoutError> {
    let image = image_methods(head, frame, context)?;
    let offset = u32::from(notifier.offset_bytes);
    if notifier.handle <= 1
        || notifier.handle == context.handle
        || offset > 0xff0
        || offset % 16 != 0
        || u64::from(offset) + 16 > notifier.len_bytes
    {
        return Err(ScanoutError::Notifier);
    }

    let mut words = [0; 26];
    words[..image.len()].copy_from_slice(&image);
    words[image.len()..].copy_from_slice(&[
        method(SET_CONTEXT_DMA_NOTIFIER, 2),
        notifier.handle,
        offset, // Byte offset occupies bits 11:4. Mode is write without interrupt.
        method(SET_INTERLOCK_FLAGS, 2),
        0, // No interlock with core or cursor.
        0, // No interlock with other windows.
        method(UPDATE, 1),
        1, // Release ELV.
    ]);
    Ok(words)
}

fn image_methods(
    head: Extent,
    frame: VramFrame,
    context: DisplayContext,
) -> Result<[u32; 18], ScanoutError> {
    if head != frame.extent || head.width == 0 || head.height == 0 {
        return Err(ScanoutError::Geometry);
    }
    let pitch_units = frame.pitch_bytes / 64;
    if frame.pitch_bytes < u32::from(head.width) * 4
        || frame.pitch_bytes % 64 != 0
        || pitch_units > 0x1fff
    {
        return Err(ScanoutError::Pitch);
    }
    if context.handle <= 1 || context.len_bytes == 0 {
        return Err(ScanoutError::Context);
    }
    if frame.offset_bytes % 256 != 0 || frame.offset_bytes >= ADDRESS_LIMIT {
        return Err(ScanoutError::Offset);
    }
    // Reserve all rows, including the final row's pitch padding.
    let end = frame.offset_bytes + u64::from(frame.pitch_bytes) * u64::from(head.height);
    if end > context.len_bytes || end > ADDRESS_LIMIT {
        return Err(ScanoutError::Range);
    }

    let size = (u32::from(head.height) << 16) | u32::from(head.width);
    Ok([
        method(SET_PRESENT_CONTROL, 1),
        1, // Present at the next vertical blank.
        method(SET_SIZE, 4),
        size,
        0,
        X8R8G8B8,
        pitch_units,
        method(SET_CONTEXT_DMA_ISO, 2),
        context.handle,
        1, // Unused chroma plane.
        method(SET_OFFSET, 1),
        (frame.offset_bytes >> 8) as u32,
        method(SET_POINT_IN, 1),
        0,
        method(SET_SIZE_IN, 1),
        size,
        method(SET_SIZE_OUT, 1),
        size,
    ])
}

const fn method(address: u32, count: u32) -> u32 {
    (count << 18) | address
}

#[cfg(test)]
mod tests;
