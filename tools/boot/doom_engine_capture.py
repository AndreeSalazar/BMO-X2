"""Verify Doom's live CPL3 presentation and response to keyboard input."""
import hashlib
from pathlib import Path
import struct
import time

from cpu_config import register
from desktop_session_capture import verify_external_rejection


def verify_engine(command, memory, prefix, image, case):
    if case == 'external-permissions':
        result = verify_external_rejection(command, memory, image)
        assert memory(0x4000000, 4096, 'rejected-engine-text') == bytes(4096)
        return result

    serial = Path(str(prefix) + '-serial.log')
    deadline = time.monotonic() + 40
    while time.monotonic() < deadline:
        log = serial.read_text(encoding='utf-8', errors='replace') if serial.is_file() else ''
        regs = command('human-monitor-command', {'command-line': 'info registers'})
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

    def screenshot(label):
        path = Path(str(prefix) + f'-{label}.ppm')
        command('screendump', dict(filename=str(path)))
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def key(name, hold=100):
        command('send-key', {'keys': [{'type': 'qcode', 'data': name}], 'hold-time': hold})
        time.sleep(hold / 1000 + 0.35)

    time.sleep(2)
    initial = screenshot('engine-initial')
    key('esc')
    menu = screenshot('engine-menu')
    key('esc')
    resumed = screenshot('engine-resumed')
    assert menu != initial and menu != resumed, 'El menu no respondio a Escape'
    key('up', 500)
    moved = screenshot('engine-moved')
    assert moved != resumed, 'El cuadro no cambio al avanzar'
    return dict(Case=case, Passed=True, DoomEngine=True, DoomKeyboardVerified=True,
                SbefSha256=hashlib.sha256(image).hexdigest(), SbefBytes=len(image),
                UserCpl=3, FrameWidth=320, FrameHeight=200, FrameSha256=initial,
                MenuSha256=menu, ResumedSha256=resumed, MovedSha256=moved, GuestRamMiB=256,
                GuestBackingBytes=16 * 1024 * 1024)
