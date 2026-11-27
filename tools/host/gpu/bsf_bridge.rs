//! HOST adapter for the original BMO-X BSF1 reader and writer.
use bmo_bsf::ModuleIn;
use std::{env, fs, io::{self, Read}, path::Path};

#[path = "../../../userspace/services/graphics/verrano/bsf.rs"]
mod profile;
use profile::{MAX_PACKAGE, MAX_SHADER, SHADER, STAGES};

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
        let input = read(package, MAX_PACKAGE)?;
        let shaders = profile::load(&input).map_err(|error| error.to_string())?;
        for (path, data) in [vertex, fragment].into_iter().zip(shaders) {
            fs::write(path, data).map_err(|error| error.to_string())?;
        }
    } else {
        return Err("expected pack or unpack".into());
    }
    Ok(())
}
