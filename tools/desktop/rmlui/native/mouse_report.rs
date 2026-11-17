//! Decode the relative pointer from a bounded HID Report Descriptor.
//! Field offsets follow the device descriptor, as in BMO-X's formato.rs.

#[derive(Clone, Copy)]
struct Field { offset: u16, width: u8, signed: bool }

impl Field {
    fn read(self, data: u64) -> i32 {
        let mask = (1u64 << self.width) - 1;
        let value = ((data >> self.offset) & mask) as i32;
        if self.signed && value & (1 << (self.width - 1)) != 0 {
            value - (1 << self.width)
        } else {
            value
        }
    }
}

#[derive(Clone, Copy, Default)]
struct Fields {
    bits: u16,
    x: Option<Field>,
    y: Option<Field>,
    buttons: [Option<Field>; 3],
}

#[derive(Clone, Copy)]
pub(crate) struct MouseReport { id: u8, fields: Fields }

impl MouseReport {
    pub(crate) fn parse(mut descriptor: &[u8]) -> Option<Self> {
        if descriptor.is_empty() || descriptor.len() > 512 { return None; }
        let mut reports = [Fields::default(); 256];
        let (mut page, mut width, mut count, mut id) = (0, 0, 0, 0);
        let mut signed = false;
        let mut usages = [0; 16];
        let mut used = 0;
        let (mut minimum, mut maximum) = (None, None);
        while let Some((&tag, remaining)) = descriptor.split_first() {
            if tag == 0xfe { return None; }
            let size = [0, 1, 2, 4][usize::from(tag & 3)];
            let (data, rest) = remaining.split_at_checked(size)?;
            descriptor = rest;
            let mut value = [0; 4];
            value[..size].copy_from_slice(data);
            let value = u32::from_le_bytes(value);
            match tag & 0xfc {
                0x04 => page = value,
                0x14 => signed = data.last().is_some_and(|byte| byte & 0x80 != 0),
                0x74 => width = value,
                0x84 => { id = usize::from(u8::try_from(value).ok()?); if id == 0 { return None; } }
                0x94 => count = value,
                0xa4 | 0xb4 => return None,
                0x08 => { *usages.get_mut(used)? = value; used += 1; }
                0x18 => minimum = Some(value),
                0x28 => maximum = Some(value),
                0x80 => {
                    let fields = &mut reports[id];
                    let end = u32::from(fields.bits).checked_add(width.checked_mul(count)?)?;
                    if width == 0 || end > 512 { return None; }
                    if value & 3 == 2 && width <= 16 {
                        for i in 0..count {
                            let usage = if (i as usize) < used { Some(usages[i as usize]) }
                                else { minimum.and_then(|lo: u32| lo.checked_add(i)).filter(|u| Some(*u) <= maximum) };
                            let Some(usage) = usage else { continue; };
                            let field_page = if usage > 0xffff { usage >> 16 } else { page };
                            let offset = u32::from(fields.bits) + width * i + if id == 0 { 0 } else { 8 };
                            if offset + width > 64 { continue; }
                            let field = Field { offset: offset as u16, width: width as u8, signed };
                            match (field_page, usage & 0xffff) {
                                (1, 0x30) if value & 4 != 0 => fields.x = Some(field),
                                (1, 0x31) if value & 4 != 0 => fields.y = Some(field),
                                (9, button @ 1..=3) if width == 1 => fields.buttons[(button-1) as usize] = Some(field),
                                _ => {}
                            }
                        }
                    }
                    fields.bits = end as u16;
                }
                _ => {}
            }
            if tag & 0x0c == 0 { used = 0; minimum = None; maximum = None; }
        }
        reports.into_iter().enumerate().find_map(|(id, fields)| {
            (fields.x.is_some() && fields.y.is_some() && fields.buttons[0].is_some())
                .then_some(Self { id: id as u8, fields })
        })
    }

    pub(crate) fn decode(self, data: u64, length: u32) -> Option<(i16, i16, u8)> {
        let expected = u32::from(self.fields.bits).div_ceil(8) + u32::from(self.id != 0);
        if length < expected || length > 64 || (self.id != 0 && data as u8 != self.id) { return None; }
        let mut buttons = 0;
        for (i, field) in self.fields.buttons.into_iter().enumerate() {
            if field.is_some_and(|field| field.read(data) != 0) { buttons |= 1 << i; }
        }
        let x = self.fields.x?.read(data).clamp(i16::MIN.into(), i16::MAX.into()) as i16;
        let y = self.fields.y?.read(data).clamp(i16::MIN.into(), i16::MAX.into()) as i16;
        Some((x,y,buttons))
    }
}

#[cfg(test)]
mod tests {
    use super::MouseReport;

    #[test]
    fn report_id_and_signed_wide_axes_keep_clicks_separate() {
        let descriptor=[0x85,7,0x05,9,0x19,1,0x29,3,0x75,1,0x95,3,0x81,2,
            0x75,5,0x95,1,0x81,1,0x05,1,0x09,0x30,0x09,0x31,0x15,0xff,0x75,16,0x95,2,0x81,6];
        let mouse=MouseReport::parse(&descriptor).unwrap();
        let data=u64::from_le_bytes([7,1,0xfc,0xff,0x2c,1,0,0]);
        assert_eq!(mouse.decode(data,6),Some((-4,300,1)));
        assert_eq!(mouse.decode(data&!(1<<8),6),Some((-4,300,0)));
        assert_eq!(mouse.decode(data^1,6),None);
        assert_eq!(mouse.decode(data,5),None);
        assert!(MouseReport::parse(&descriptor[..descriptor.len()-1]).is_none());
    }
}
