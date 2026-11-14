"""Verify Doom's live CPL3 presentation and response to keyboard input."""
import hashlib
from pathlib import Path
import struct
import time

from cpu_config import register
from desktop_session_capture import verify_external_rejection


def verify_engine(command, memory, prefix, image, case, *, desktop=False):
    if case == 'external-permissions':
        result = verify_external_rejection(command, memory, image)
        assert memory(0x4000000, 4096, 'rejected-engine-text') == bytes(4096)
        return result

    serial = Path(str(prefix) + '-serial.log')

    def registers():
        return command('human-monitor-command', {'command-line': 'info registers'})

    def screenshot(label):
        path = Path(str(prefix) + f'-{label}.ppm')
        command('screendump', dict(filename=str(path)))
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def key(*names, hold=100):
        command('send-key', {'keys': [{'type': 'qcode', 'data': name} for name in names],
                             'hold-time': hold})
        time.sleep(hold / 1000 + 0.35)

    if desktop:
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            regs = registers()
            rbp = register(regs, 'RBP')
            if ('HLT=1' in regs and 0x100000 <= rbp < 0xffe0000 and
                    register(regs, 'CR3') == rbp + 0x13000):
                context = memory(rbp, 0x30, 'desktop-context')
                if context[:8] == b'METAL64!':
                    break
            time.sleep(0.05)
        else:
            raise ValueError(f'El escritorio no entro en WAIT: {regs[:460]}')
        fb = struct.unpack_from('<Q', context, 16)[0]
        width, height, pitch, order = struct.unpack_from('<IIII', context, 32)
        scale = 2 if width >= 1280 and height >= 800 else 1

        def check_pixel(x, y, color):
            rgb = color.to_bytes(4, 'little')
            if order == 0:
                rgb = rgb[:3][::-1] + b'\0'
            assert memory(fb + 4*scale*(y*pitch+x), 4, 'desktop-doom-pixel') == rgb

        check_pixel(272, 33, 0x0d0e17)
        key('ctrl', 'meta_l', '2')
        check_pixel(272, 33, 0xad92ff)
        time.sleep(1.5)
        check_pixel(272, 33, 0x0d0e17)
        key('f2')
        check_pixel(24, 24, 0x232638)
        key('d')
        key('ret')
        check_pixel(24, 24, 0x232638)
        assert 'BMO DOOM START' not in serial.read_text(encoding='utf-8', errors='replace')
        screenshot('cabina')
        for char in ('d', 'o', 'o', 'm', 'spc', 'r', 'u', 'n', 'ret'):
            key(char, hold=40)

    deadline = time.monotonic() + 40
    while time.monotonic() < deadline:
        log = serial.read_text(encoding='utf-8', errors='replace') if serial.is_file() else ''
        regs = registers()
        if 'BMO DOOM EXIT' in log:
            raise ValueError(log[-1600:])
        if 'BMO DOOM FRAME' in log and 'CPL=3' in regs:
            rip = register(regs, 'RIP')
            text_bytes = struct.unpack_from('<I', image, 44)[0]
            if 0x40000000 <= rip < 0x40000000 + text_bytes:
                break
        time.sleep(0.05)
    else:
        raise ValueError(f'DOOM no presento un cuadro CPL3:\n{log[-1600:]}\n{regs[:1100]}')

    tr = next(line for line in regs.splitlines() if line.startswith('TR ='))
    descriptor = int(tr.split()[2], 16) - 0x100
    page_directory = register(regs, 'CR3') + 0x3000
    assert page_directory == descriptor - 0x4000
    table = struct.unpack('<8Q', memory(page_directory, 64, 'engine-pages'))
    expected = [0x4000085, 0x8000000004200085]
    expected.extend(0x8000000004400087 + i * 0x200000 for i in range(6))
    assert tuple(entry & ~0x60 for entry in table) == tuple(expected), table

    time.sleep(2)
    initial = screenshot('engine-initial')
    key('esc')
    menu = screenshot('engine-menu')
    key('esc')
    resumed = screenshot('engine-resumed')
    assert menu != initial and menu != resumed, 'El menu no respondio a Escape'
    key('up', hold=500)
    moved = screenshot('engine-moved')
    assert moved != resumed, 'El cuadro no cambio al avanzar'
    if desktop:
        assert width == 1280 and height == 800
        frame = Path(str(prefix) + '-engine-moved.ppm').read_bytes().split(b'\n', 3)[-1]
        assert len(frame) == width * height * 3
        for y in (0, height - 1):
            assert any(frame[y * width * 3:(y + 1) * width * 3]), 'DOOM dejo un borde horizontal'
        for x in (0, width - 1):
            assert any(frame[3 * (y * width + x) + channel]
                       for y in range(height) for channel in range(3)), 'DOOM dejo un borde vertical'
        key('meta_l', '2')
        check_pixel(390, 147, 0xad92ff)
        background = screenshot('engine-background')
        key('meta_l', '1')
        assert screenshot('engine-refocused') != background
        key('ctrl', 'meta_l', '3')
        check_pixel(52, 99, 0x6ee7b7)
        key('ctrl', 'meta_l', '2')
        check_pixel(390, 147, 0xad92ff)
        key('meta_l', '1')
        key('meta_l', 'q')
        check_pixel(390, 147, 0xad92ff)
        key('f2')
        check_pixel(24, 24, 0x232638)
    return dict(Case=case, Passed=True, DoomEngine=True, DoomKeyboardVerified=True,
                CabinaDoomVerified=desktop, WorkspaceBarAutoHideVerified=desktop,
                DoomFullScreenVerified=desktop, DoomFocusAndCloseVerified=desktop,
                SbefSha256=hashlib.sha256(image).hexdigest(), SbefBytes=len(image),
                UserCpl=3, FrameWidth=320, FrameHeight=200, FrameSha256=initial,
                MenuSha256=menu, ResumedSha256=resumed, MovedSha256=moved, GuestRamMiB=256,
                GuestBackingBytes=16 * 1024 * 1024)
