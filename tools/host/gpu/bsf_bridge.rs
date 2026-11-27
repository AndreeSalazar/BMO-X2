//! HOST adapter for the original BMO-X BSF1 reader and writer.
use bmo_bsf::{Bsf, ModuleIn};
use std::{env, fs, io::{self, Read}, path::Path};

const STAGES: [(u8, &[u8]); 2] = [(0, b"vs"), (4, b"ps")];
const SHADER: u64 = 1 << 1;
const MAX_SHADER: usize = 16 * 1024;

fn bounded_read(path: &Path, limit: usize) -> io::Result<Vec<u8>> {
    let mut result = Vec::new();
    fs::File::open(path)?.take(limit as u64 + 1).read_to_end(&mut result)?;
    if result.len() > limit {
        return Err(io::Error::new(io::ErrorKind::InvalidData, "BSF input exceeds profile limit"));
    }
    Ok(result)
}

fn main() -> Result<(), String> {
    let arguments: Vec<_> = env::args_os().skip(1).collect();
    let [mode, package, vertex, fragment] = arguments.as_slice() else {
        return Err("usage: bsf-bridge pack|unpack package.bsf vertex.spv fragment.spv".into());
    };
    let (package, vertex, fragment) = (Path::new(package), Path::new(vertex), Path::new(fragment));
    let read = |path, limit| bounded_read(path, limit).map_err(|error| error.to_string());
    let fault = |error| format!("{error:?}");
    if mode == "pack" {
        let shaders = [read(vertex, MAX_SHADER)?, read(fragment, MAX_SHADER)?];
        let modules = STAGES.map(|(model, name)| ModuleIn {
            model, name, local_size: [0; 3], capabilities: SHADER, caps_high: 0,
            spirv: &shaders[usize::from(model == 4)], bindings: &[], targets: &[],
        });
        let mut output = vec![0; bmo_bsf::size(&modules).map_err(fault)?];
        bmo_bsf::write(&modules, &mut output).map_err(fault)?;
        fs::write(package, output).map_err(|error| error.to_string())?;
    } else if mode == "unpack" {
        let input = read(package, 2 * MAX_SHADER + 1024)?;
        let bsf = Bsf::parse(&input).map_err(fault)?;
        bsf.verify_all().map_err(fault)?;
        if bsf.module_count() != STAGES.len() || bsf.target_count() != 0 {
            return Err("BSF profile requires two portable shader modules".into());
        }
        let mut shaders = [&[][..]; 2];
        for (index, (model, name)) in STAGES.iter().copied().enumerate() {
            let module = bsf.module(index);
            if module.model() != model || module.name() != name || module.binding_count() != 0 ||
                !(20..=MAX_SHADER).contains(&module.spirv_len())
            {
                return Err(format!("Invalid BSF shader module {index}"));
            }
            shaders[index] = module.spirv().map_err(fault)?;
        }
        for (path, data) in [vertex, fragment].into_iter().zip(shaders) {
            fs::write(path, data).map_err(|error| error.to_string())?;
        }
    } else {
        return Err("expected pack or unpack".into());
    }
    Ok(())
}
