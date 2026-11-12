"""Verify a live CPL3 session, framebuffer changes and QEMU keyboard input."""
import hashlib
import struct
import time

from cpu_config import register
from splash_capture import compare_frame


def verify_session(command, memory, prefix, packet, intro, fixture):
    def registers():
        return command('human-monitor-command', {'command-line': 'info registers'})

    def wait_until(check):
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            result = check()
            if result:
                return result
            time.sleep(0.04)
        raise ValueError(f'Sesion no alcanzo el estado esperado: {registers()[:420]}')

    frames = set()

    def started():
        regs = registers()
        address = register(regs, 'RBP')
        if 0x100000 <= address <= 0xffe0000 and address % 4096 == 0:
            context = memory(address, 0xb0, 'session-context')
            if context[:8] == b'METAL64!' and struct.unpack_from('<I', context, 0x78)[0] == 1:
                code = struct.unpack_from('<Q', context, 8)[0]
                rip = register(regs, 'RIP')
                frame = register(regs, 'R12')
                if intro and frame in (1, 2) and frame not in frames and 0xb6 <= rip-code < 0xd0:
                    command('stop')
                    try:
                        if 0xb6 <= register(registers(), 'RIP')-code < 0xd0:
                            compare_frame(memory, context, intro, frame)
                            frames.add(frame)
                    finally:
                        command('cont')
                return address, context, code

    address, context, code = wait_until(started)
    if intro and frames != {1, 2}:
        def through_intro():
            started()
            return len(frames) == 2
        wait_until(through_intro)
    fb = struct.unpack_from('<Q', context, 0x10)[0]
    width, height = struct.unpack_from('<II', context, 0x20)
    pitch, order = struct.unpack_from('<II', context, 0x28)

    def pixel(x, y, color):
        raw = color.to_bytes(4, 'little')
        if order == 0:
            raw = raw[:3][::-1] + b'\0'
        return memory(fb + (pitch*y+x)*4, 4, 'session-pixel') == raw

    def ring3():
        regs = registers()
        return 'CPL=3' in regs and 0x40000000 <= register(regs, 'RIP') < 0x40001000

    def key(*keys):
        command('send-key', {'keys': [{'type': 'qcode', 'data': key} for key in keys],
                             'hold-time': 100})
        time.sleep(0.2)

    wait_until(lambda: pixel(216, 33, 0x5ad8ff) and pixel(52, 99, 0x5ad8ff) and ring3())
    assert pixel(width-1, height-1, 0x0d0e17), 'La intro no fue reemplazada'
    assert memory(code, len(packet)-24, 'session-code') == packet[24:]
    for digit, x, color in [('2', 272, 0xad92ff), ('3', 328, 0x6ee7b7), ('4', 384, 0xff7c98)]:
        key('ctrl', 'meta_l', digit)
        wait_until(lambda: pixel(x, 33, color) and pixel(52, 99, color))
    key('ctrl', 'meta_l', '2')
    wait_until(lambda: pixel(272, 33, 0xad92ff))
    key('meta_l', '2')
    wait_until(lambda: pixel(390, 147, 0xad92ff) and pixel(52, 99, 0x40465d))
    key('1')
    wait_until(lambda: pixel(216, 33, 0x5ad8ff))
    key('2')
    wait_until(lambda: pixel(390, 147, 0xad92ff) and ring3())
    command('screendump', {'filename': str(prefix)+'.png', 'format': 'png'})
    return dict(Case='normal', Passed=True, BootServicesExited=True, UserCPL=3,
                IntroFramesObserved=sorted(frames), WorkspacesVerified=[1, 2, 3, 4],
                KeyboardVerified=True, FocusRestored=True, DesktopSession=True, IntroReplaced=True,
                PayloadSHA256=hashlib.sha256(packet[24:]).hexdigest(),
                SbefSHA256=fixture['sbef_sha256'])
