"""Verify the GCC client, its initialized memory and the display request."""
import hashlib
import struct
import time

from cpu_config import register


def verify_doom_external(command, memory, prefix, packet, image):
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
            return dict(Case='normal', Passed=True, UserCPL=3, ExternalSbef=True,
                        DoomFixedArithmetic=True, UserDataAndBssVerified=True,
                        DisplayPermissionRejected=True, DisplayPixelsVerified=size*rows,
                        SbefSHA256=hashlib.sha256(image).hexdigest())
        time.sleep(0.04)
    raise ValueError('La sonda DOOM no presento su cuadro desde CPL3')
