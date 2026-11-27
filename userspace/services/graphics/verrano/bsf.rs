//! Profile of the original BSF1 container consumed by VERRANO.
use bmo_bsf::{Bsf, Fault};
use core::fmt;

pub const STAGES: [(u8, &[u8]); 2] = [(0, b"vs"), (4, b"ps")];
pub const SHADER: u64 = 1 << 1;
pub const MAX_SHADER: usize = 16 * 1024;
pub const MAX_PACKAGE: usize = 2 * MAX_SHADER + 1024;

#[derive(Debug)]
pub enum Rejection {
    Size,
    Container(Fault),
    Layout,
    Module(usize),
}

impl fmt::Display for Rejection {
    fn fmt(&self, output: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Size => output.write_str("BSF exceeds the profile size limit"),
            Self::Container(fault) => write!(output, "BSF container: {fault:?}"),
            Self::Layout => output.write_str("BSF requires two portable shader modules"),
            Self::Module(index) => write!(output, "Invalid BSF shader module {index}"),
        }
    }
}

/// Check the index and both payload hashes once, before creating a pipeline.
/// The trusted shader producer must already have checked the SPIR-V profile.
pub fn load(bytes: &[u8]) -> Result<[&[u8]; 2], Rejection> {
    if bytes.len() > MAX_PACKAGE {
        return Err(Rejection::Size);
    }
    let bsf = Bsf::parse(bytes).map_err(Rejection::Container)?;
    if bsf.module_count() != STAGES.len() || bsf.target_count() != 0 {
        return Err(Rejection::Layout);
    }
    let mut shaders = [&[][..]; 2];
    for (index, (model, name)) in STAGES.iter().copied().enumerate() {
        let module = bsf.module(index);
        if module.model() != model || module.name() != name || module.binding_count() != 0
            || module.capabilities() != SHADER || module.caps_high() != 0
            || !(20..=MAX_SHADER).contains(&module.spirv_len())
            || module.es_mapa()
        {
            return Err(Rejection::Module(index));
        }
        shaders[index] = module.spirv().map_err(Rejection::Container)?;
    }
    Ok(shaders)
}
