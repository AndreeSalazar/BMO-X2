use crate::raster::{triangle, Vertex, Texture, Rect};
pub fn scene() -> [u32;256] {
    let mut pixels=[0x0b1019;256];
    let v=|x,y,r,g,b| Vertex{x,y,r,g,b,a:255.0,u:0.0,v:0.0};
    let a=v(0.0,0.0,125.0,227.0,210.0); let b=v(16.0,0.0,173.0,146.0,255.0);
    let c=v(16.0,16.0,90.0,216.0,255.0); let d=v(0.0,16.0,125.0,227.0,210.0);
    let full=Rect{left:0,top:0,right:16,bottom:16};
    assert!(triangle(&mut pixels,16,16,[a,b,c],None,full).is_ok());
    assert!(triangle(&mut pixels,16,16,[a,d,c],None,full).is_ok());
    let white=|x,y| v(x,y,255.0,255.0,255.0);
    let t=Texture{width:1,height:1,rgba:&[64,64,64,128]};
    assert!(triangle(&mut pixels,16,16,[white(0.0,0.0),white(16.0,0.0),white(0.0,16.0)],Some(t),
        Rect{left:3,top:3,right:13,bottom:13}).is_ok());
    pixels
}
