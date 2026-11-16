#[path="../../../userspace/services/desktop/src/rmlui.rs"] mod raster;
mod probe_scene;
fn main() {
    let pixels=probe_scene::scene();
    let bytes:Vec<_>=pixels.iter().flat_map(|p|p.to_le_bytes()).collect();
    std::fs::write(std::env::args().nth(1).expect("output"),bytes).unwrap();
}
