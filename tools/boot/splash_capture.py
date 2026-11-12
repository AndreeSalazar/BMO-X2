"""Compare a captured rectangle with the original logo cells, frame by frame."""
import struct


def compare_frame(memory, context, rows, frame):
    fb = struct.unpack_from('<Q', context, 0x10)[0]
    width, height, pitch, order = struct.unpack_from('<IIII', context, 0x20)
    if not (640 <= width <= 4096 and 400 <= height <= 4096 and width <= pitch <= 8192 and order in (0, 1)):
        raise ValueError('SPLASH-FRAMEBUFFER: geometria o formato invalido')
    x, y = (width-256)//2, (height-256)//2
    raw = memory(fb + (y*pitch+x)*4, (255*pitch+256)*4, f'frame-{frame}')
    eye = [(12,80,96),(64,230,255),(39,189,217)][frame-1]
    if order == 1:
        eye = eye[::-1]
    colors = {'.':bytes(4), '#':bytes((232,232,232,0)), 'o':bytes((*eye,0))}
    scale = 256 // len(rows)
    for index, row in enumerate(rows):
        expected = b''.join(colors[cell]*scale for cell in row)
        for scanline in range(index*scale,(index+1)*scale):
            offset = scanline*pitch*4
            if raw[offset:offset+1024] != expected:
                raise ValueError(f'SPLASH-PIXELS: cuadro {frame}, linea {scanline}')
