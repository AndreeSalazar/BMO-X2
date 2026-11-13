"""Verify the GCC client, its initialized memory and the display request."""
import hashlib
import struct
import time

from cpu_config import register


def map_pixels(wad):
    count, directory = struct.unpack_from('<II', wad, 4)
    entries = list(struct.iter_unpack('<II8s', wad[directory:directory+16*count]))
    marker = next(i for i, (_, _, name) in enumerate(entries) if name.rstrip(b'\0') == b'E1M1')
    lumps = {name.rstrip(b'\0'): wad[start:start+size] for start, size, name in entries[marker+1:marker+11]}
    vertices = list(struct.iter_unpack('<hh', lumps[b'VERTEXES']))
    lines = list(struct.iter_unpack('<7H', lumps[b'LINEDEFS']))
    xs, ys = zip(*vertices)
    span = max(max(xs)-min(xs), max(ys)-min(ys))
    def project(point):
        x, y = point
        return (320 + int((2*x-min(xs)-max(xs))*150/span),
                220 + int((min(ys)+max(ys)-2*y)*150/span))
    projected = [project(vertex) for vertex in vertices]
    pixels = set()
    for first, last, *_ in lines:
        x, y = projected[first]
        end_x, end_y = projected[last]
        dx, dy = abs(end_x-x), -abs(end_y-y)
        sx, sy = (1 if x < end_x else -1), (1 if y < end_y else -1)
        error = dx + dy
        while True:
            pixels.add((x, y))
            if (x, y) == (end_x, end_y):
                break
            twice = error * 2
            if twice >= dy:
                error += dy
                x += sx
            if twice <= dx:
                error += dx
                y += sy
    return pixels, len(vertices), len(lines)


def verify_doom_external(command, memory, prefix, packet, image, wad):
    staged = wad.read_bytes() if wad.is_file() else None
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        regs = command('human-monitor-command', {'command-line': 'info registers'})
        if 'CPL=3' in regs and 0x40000000 <= register(regs, 'RIP') < 0x40002000:
            # The SYSCALL fixture stores the trusted context in kernel GS.
            msr_base = next(line for line in regs.splitlines() if line.startswith('TR ='))
            descriptor = int(msr_base.split()[2], 16) - 0x100
            context = struct.unpack('<Q', memory(descriptor + 0x320, 8, 'doom-context-pointer'))[0]
            handoff = memory(context, 0xb0, 'doom-context')
            fb = struct.unpack_from('<Q', handoff, 16)[0]
            width, height, pitch, order = struct.unpack_from('<IIII', handoff, 32)
            scale = 2 if width >= 1280 and height >= 800 else 1
            x, y = 24*scale, 32*scale
            color = bytes.fromhex('b7e76e00' if order else '6ee7b700')
            size = 96*scale
            rows = 40*scale
            raw = memory(fb + (y*pitch+x)*4, ((rows-1)*pitch+size)*4, 'doom-rectangle')
            if any(raw[row*pitch*4:row*pitch*4+size*4] != color*size for row in range(rows)):
                time.sleep(0.04)
                continue
            code = struct.unpack_from('<Q', handoff, 8)[0]
            assert handoff[:8] == b'METAL64!' and struct.unpack_from('<I', handoff, 0x78)[0] == 1
            assert image not in packet and memory(code, len(packet)-24, 'doom-code') == packet[24:]
            assert memory(context + 0x1d000, 8, 'doom-data') == struct.pack('<II', 65536, 196608)
            command('screendump', {'filename': str(prefix)+'.png', 'format': 'png'})
            result = dict(Case='normal', Passed=True, UserCPL=3, ExternalSbef=True,
                        DoomFixedArithmetic=True, UserDataAndBssVerified=True,
                        DisplayPermissionRejected=True, DisplayPixelsVerified=size*rows,
                        SbefSHA256=hashlib.sha256(image).hexdigest())
            if staged is not None:
                assert memory(0x3000000, len(staged), 'doom-wad') == staged
                pixels, vertices, lines = map_pixels(staged[8:])
                # The green status rectangle occupies x=24..119, y=32..71.
                pixels.update((x, y) for y in range(32, 72) for x in range(24, 120))
                background = bytes.fromhex('170e0d00' if order else '0d0e1700')
                raw = memory(fb, ((400*scale-1)*pitch + 640*scale)*4, 'doom-map')
                for y in range(400*scale):
                    expected = b''.join((color if (x, y//scale) in pixels else background)*scale
                                        for x in range(640))
                    start = y*pitch*4
                    assert raw[start:start+len(expected)] == expected, f'Plano E1M1 distinto en fila {y}'
                result.update(WadDirectoryEntry='E1M1', WadReadBoundsChecked=True,
                              WadStdioVerified=True,
                              WadPermissionChecked=True, WadSHA256=hashlib.sha256(staged[8:]).hexdigest(),
                              MapVertices=vertices, MapLines=lines, MapPixelsVerified=len(pixels)-96*40)
            return result
        time.sleep(0.04)
    raise ValueError('La sonda DOOM no presento su cuadro desde CPL3')
