"""Real CPL3 pixel equivalence for the shared Rust rasterizer, not the RmlUi engine."""
import hashlib
import struct
import time
from cpu_config import register


def verify_raster(command, memory, prefix, expected_path):
    expected = expected_path.read_bytes()
    deadline = time.monotonic() + 25
    while time.monotonic() < deadline:
        regs = command('human-monitor-command', {'command-line': 'info registers'})
        if 'CPL=3' not in regs or not 0x40000000 <= register(regs, 'RIP') < 0x40002000:
            time.sleep(0.04)
            continue
        # Rust owns RBP. Read the existing supervisor descriptor, never a guest register guess.
        root = register(regs, 'CR3')
        address = struct.unpack('<Q', memory(root+0x7320,8,'raster-handoff'))[0]
        if 0x100000 <= address <= 0xffe0000:
            context = memory(address, 0x30, 'raster-context')
            if context[:8] == b'METAL64!':
                fb = struct.unpack_from('<Q', context, 0x10)[0]
                width, height, pitch, order = struct.unpack_from('<IIII', context, 0x20)
                if not (640 <= width <= 4096 and 400 <= height <= 4096 and width <= pitch <= 8192 and order in (0, 1)):
                    raise ValueError('Framebuffer raster invalido')
                scale = 2 if width >= 1280 and height >= 800 else 1
                marker = memory(fb+(104*scale*pitch+240*scale)*4,4,'raster-marker')
                wanted = bytes.fromhex('d2e37d00') if order == 1 else bytes.fromhex('7de3d200')
                if marker == wanted:
                    command('stop')
                    break
        time.sleep(0.04)
    else:
        raise ValueError(f'El rasterizador no completo en CPL3: {regs[:500]}')
    raw = memory(fb+(120*scale*pitch+256*scale)*4, ((128*scale-1)*pitch+128*scale)*4, 'raster-pixels')
    for y in range(128*scale):
        for x in range(128*scale):
            index=((y//(8*scale))*16+x//(8*scale))*4
            color=expected[index:index+4]
            if order == 0:
                color=color[:3][::-1]+b'\0'
            offset=(y*pitch+x)*4
            if raw[offset:offset+4] != color:
                raise ValueError(f'Rust HOST/guest difieren en pixel {x},{y}')
    command('screendump', {'filename': str(prefix)+'-raster.ppm'})
    return dict(Case='normal', Passed=True, Evidence='QEMU', CPL=3,
                SharedRustRasterizer=True, FullRmlUiEngine=False,
                HostGuestPixelsIdentical=True, LogicalPixelsVerified=256,
                PhysicalPixelsVerified=128*scale*128*scale,
                ReferenceSHA256=hashlib.sha256(expected).hexdigest(),
                Scope='Triangle winding, gradient, clipping and premultiplied texture in external SBEF')
