//! Borrowed CPU drawing for RmlUi geometry. No allocator, OS calls or global state.
#[repr(C)]
#[derive(Clone, Copy)]
pub struct Vertex {
    pub x: f32, pub y: f32,
    pub r: f32, pub g: f32, pub b: f32, pub a: f32,
    pub u: f32, pub v: f32,
}

#[repr(C)]
#[derive(Clone, Copy)]
pub struct Rect { pub left: u32, pub top: u32, pub right: u32, pub bottom: u32 }

pub enum Texels<'a> { Rgba(&'a [u8]), Alpha(&'a [u8]) }
pub struct Texture<'a> { pub width: u32, pub height: u32, pub texels: Texels<'a> }

#[derive(Debug, PartialEq, Eq)]
pub enum Error { Target, Texture, Vertex }

fn edge(a: Vertex, b: Vertex, x: f32, y: f32) -> f32 {
    (x-a.x)*(b.y-a.y) - (y-a.y)*(b.x-a.x)
}
fn owned(value: f32, a: Vertex, b: Vertex) -> bool {
    value > 0.0 || (value == 0.0 && (a.y < b.y || (a.y == b.y && a.x > b.x)))
}
fn channel(value: f32) -> u32 { ((value + 0.5) as u32).min(255) }

/// Premultiplied RGBA vertices/texture, XRGB8888 target, exclusive scissor bounds.
/// Validates all dimensions and vertices before changing the caller's target.
pub fn triangle(pixels: &mut [u32], width: u32, height: u32,
                mut vertices: [Vertex; 3], texture: Option<Texture<'_>>, clip: Rect) -> Result<(), Error> {
    if width == 0 || height == 0 || width > 4096 || height > 4096
        || pixels.len() != width as usize * height as usize { return Err(Error::Target); }
    if let Some(t) = &texture {
        let (length, channels)=match &t.texels {Texels::Rgba(b)=>(b.len(),4),Texels::Alpha(b)=>(b.len(),1)};
        if t.width == 0 || t.height == 0 || t.width > 4096 || t.height > 4096
            || length != t.width as usize * t.height as usize * channels { return Err(Error::Texture); }
    }
    for v in &vertices {
        if ![v.x,v.y,v.r,v.g,v.b,v.a,v.u,v.v].iter().all(|f| f.is_finite())
            || v.x.abs() > 1_000_000.0 || v.y.abs() > 1_000_000.0
            || [v.r,v.g,v.b,v.a].iter().any(|&f| !(0.0..=255.0).contains(&f)) {
            return Err(Error::Vertex);
        }
    }
    let mut area = edge(vertices[0],vertices[1],vertices[2].x,vertices[2].y);
    if area == 0.0 { return Ok(()); }
    if area < 0.0 { vertices.swap(1,2); area = -area; }
    let [a,b,c] = vertices;
    // Positive clipped coordinates permit floor by truncation and ceil by +1.
    let x0 = (a.x.min(b.x).min(c.x).max(0.0) as u32).max(clip.left).min(width);
    let x1 = ((a.x.max(b.x).max(c.x).max(0.0) as u32)+1).min(clip.right).min(width);
    let y0 = (a.y.min(b.y).min(c.y).max(0.0) as u32).max(clip.top).min(height);
    let y1 = ((a.y.max(b.y).max(c.y).max(0.0) as u32)+1).min(clip.bottom).min(height);
    for y in y0..y1 { for x in x0..x1 {
        let px=x as f32+0.5; let py=y as f32+0.5;
        let u=edge(b,c,px,py); let v=edge(c,a,px,py); let w=edge(a,b,px,py);
        if !owned(u,b,c) || !owned(v,c,a) || !owned(w,a,b) { continue; }
        let (u,v,w)=(u/area,v/area,w/area);
        let mut r=u*a.r+v*b.r+w*c.r; let mut g=u*a.g+v*b.g+w*c.g;
        let mut bl=u*a.b+v*b.b+w*c.b; let mut alpha=u*a.a+v*b.a+w*c.a;
        if let Some(t)=&texture {
            let tx=((u*a.u+v*b.u+w*c.u)*t.width as f32) as i32;
            let ty=((u*a.v+v*b.v+w*c.v)*t.height as f32) as i32;
            let index=ty.clamp(0,t.height as i32-1) as usize*t.width as usize
                + tx.clamp(0,t.width as i32-1) as usize;
            match &t.texels {
                Texels::Rgba(bytes)=> {
                    let index=index*4;
                    r*=bytes[index] as f32/255.0; g*=bytes[index+1] as f32/255.0;
                    bl*=bytes[index+2] as f32/255.0; alpha*=bytes[index+3] as f32/255.0;
                }
                Texels::Alpha(bytes)=> {
                    // Lossless shorthand for premultiplied white RGBA=(a,a,a,a).
                    let coverage=bytes[index] as f32/255.0;
                    r*=coverage; g*=coverage; bl*=coverage; alpha*=coverage;
                }
            }
        }
        let index=y as usize*width as usize+x as usize;
        let dst=pixels[index]; let inv=1.0-alpha/255.0;
        pixels[index]=channel(r+((dst>>16)&255) as f32*inv)<<16
            | channel(g+((dst>>8)&255) as f32*inv)<<8 | channel(bl+(dst&255) as f32*inv);
    }}
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    fn v(x:f32,y:f32)->Vertex { Vertex{x,y,r:128.0,g:0.0,b:0.0,a:128.0,u:0.0,v:0.0} }
    const CLIP: Rect=Rect{left:0,top:0,right:4,bottom:4};
    #[test]
    fn shared_edge_blends_once_and_winding_is_independent() {
        let mut target=[0xff;16];
        triangle(&mut target,4,4,[v(0.0,0.0),v(4.0,0.0),v(4.0,4.0)],None,CLIP).unwrap();
        triangle(&mut target,4,4,[v(0.0,0.0),v(0.0,4.0),v(4.0,4.0)],None,CLIP).unwrap();
        assert!(target.iter().all(|&p|p==0x80007f));
    }
    #[test]
    fn borrowed_font_texture_and_scissor() {
        let mut target=[0u32;16];
        let t=Texture{width:1,height:1,texels:Texels::Rgba(&[128,128,128,128])};
        triangle(&mut target,4,4,[v(0.0,0.0),v(4.0,0.0),v(0.0,4.0)],Some(t),
                 Rect{left:1,top:1,right:2,bottom:2}).unwrap();
        assert_eq!(target.iter().filter(|&&p|p!=0).count(),1);
        assert_eq!(target[5],0x400000);
    }
    #[test]
    fn invalid_inputs_do_not_change_target() {
        let mut target=[7;16]; let verts=[v(0.0,0.0),v(4.0,0.0),v(0.0,4.0)];
        assert_eq!(triangle(&mut target,5,4,verts,None,CLIP),Err(Error::Target));
        assert_eq!(triangle(&mut target,4,4,verts,Some(Texture{width:1,height:1,texels:Texels::Rgba(&[])}),CLIP),Err(Error::Texture));
        assert_eq!(triangle(&mut target,4,4,verts,Some(Texture{width:1,height:1,texels:Texels::Alpha(&[])}),CLIP),Err(Error::Texture));
        let mut bad=verts; bad[0].x=f32::NAN;
        assert_eq!(triangle(&mut target,4,4,bad,None,CLIP),Err(Error::Vertex));
        assert_eq!(target,[7;16]);
    }
    #[test]
    fn alpha_atlas_matches_rgba_for_all_coverages() {
        let verts=[v(0.0,0.0),v(4.0,0.0),v(0.0,4.0)];
        for alpha in 0..=255 {
            let mut rgba=[0x123456;16]; let mut mask=rgba;
            triangle(&mut rgba,4,4,verts,Some(Texture{width:1,height:1,texels:Texels::Rgba(&[alpha;4])}),CLIP).unwrap();
            triangle(&mut mask,4,4,verts,Some(Texture{width:1,height:1,texels:Texels::Alpha(&[alpha])}),CLIP).unwrap();
            assert_eq!(rgba,mask,"coverage {alpha}");
        }
    }
}
