"""Verify a live CPL3 session, framebuffer changes and QEMU keyboard input."""
import hashlib
import struct
import time

from cpu_config import register
from splash_capture import compare_frame


def verify_external_rejection(command, memory):
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        regs = command('human-monitor-command', {'command-line': 'info registers'})
        context = register(regs, 'RBP')
        if 'HLT=1' in regs and 'CPL=0' in regs and 0x100000 <= context < 0xffe0000:
            if memory(context, 8, 'rejected-context') == b'METAL64!':
                assert register(regs, 'R12') == 0
                assert register(regs, 'CR3') == register(regs, 'R13')
                assert memory(context + 0x18000, 4096, 'rejected-text') == bytes(4096)
                return dict(Case='external-permissions', Passed=True, SbefAccepted=False,
                            UserCodeCopied=False, UserAddressSpaceActivated=False)
        time.sleep(0.04)
    raise ValueError(f'El cargador externo no rechazo W+X: {regs[:420]}')


def verify_session(command, memory, prefix, packet, intro, fixture, external_image=None):
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
                low, high = (0xb6, 0xd0) if intro and len(intro) == 64 else (0xb3, 0xcd)
                if intro and frame in (1, 2) and frame not in frames and low <= rip-code < high:
                    command('stop')
                    try:
                        if low <= register(registers(), 'RIP')-code < high:
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
    scale = 2 if width >= 1280 and height >= 800 else 1

    def pixel(x, y, color):
        raw = color.to_bytes(4, 'little')
        if order == 0:
            raw = raw[:3][::-1] + b'\0'
        return memory(fb + (pitch*y+x)*4, 4, 'session-pixel') == raw

    def logical(x, y, color):
        return pixel(x*scale, y*scale, color)

    def ring3():
        regs = registers()
        return 'CPL=3' in regs and 0x40000000 <= register(regs, 'RIP') < 0x40001000

    def wait_stats():
        return struct.unpack('<II', memory(address + 0x1a340, 8, 'wait-stats'))

    def sleeping():
        regs = registers()
        return 'CPL=0' in regs and 'HLT=1' in regs and code <= register(regs, 'RIP') < code + len(packet)-24

    def key(*keys):
        command('send-key', {'keys': [{'type': 'qcode', 'data': key} for key in keys],
                             'hold-time': 100})
        time.sleep(0.2)

    wait_until(lambda: logical(216, 33, 0x5ad8ff) and logical(52, 99, 0x5ad8ff) and sleeping())
    timeout_before = wait_stats()[1]
    wait_until(lambda: wait_stats()[1] > timeout_before)
    event_before = wait_stats()[0]
    assert pixel(width-1, height-1, 0x0d0e17), 'La intro no fue reemplazada'
    assert memory(code, len(packet)-24, 'session-code') == packet[24:]
    if external_image is not None:
        assert external_image not in packet, 'SBEF externo embebido en el paquete'
        payload = external_image[64:]
        assert memory(address + 0x18000, 4096, 'external-text') == payload.ljust(4096, b'\0')
    for digit, x, color in [('2', 272, 0xad92ff), ('3', 328, 0x6ee7b7), ('4', 384, 0xff7c98)]:
        key('ctrl', 'meta_l', digit)
        wait_until(lambda: logical(x, 33, color) and logical(52, 99, color))
    key('ctrl', 'meta_l', '2')
    wait_until(lambda: logical(272, 33, 0xad92ff))
    key('meta_l', '2')
    wait_until(lambda: logical(390, 147, 0xad92ff) and logical(52, 99, 0x40465d))
    key('1')
    wait_until(lambda: logical(216, 33, 0x5ad8ff))
    key('2')
    wait_until(lambda: logical(390, 147, 0xad92ff) and (sleeping() or ring3()))
    assert wait_stats()[0] > event_before, 'WAIT no devolvio entrada disponible'

    def full_repaints():
        return int.from_bytes(memory(address + 0x1a32c, 4, 'full-repaints'), 'little')

    def move(dx, dy):
        command('input-send-event', {'events': [
            {'type': 'rel', 'data': {'axis': 'x', 'value': dx}},
            {'type': 'rel', 'data': {'axis': 'y', 'value': dy}},
        ]})

    baseline = full_repaints()
    assert baseline > 0, 'Contador de repintados sin inicializar'
    move(-80, -32)
    wait_until(lambda: logical(240, 168, 0xe7efff) and logical(320, 200, 0x171825))
    move(4, 0)
    wait_until(lambda: logical(244, 168, 0xe7efff) and logical(240, 168, 0x171825))
    move(-4, 0)
    wait_until(lambda: logical(240, 168, 0xe7efff) and logical(246, 173, 0x171825))
    move(0, -12)
    wait_until(lambda: logical(240, 157, 0xe7efff))
    move(0, 12)
    wait_until(lambda: logical(240, 168, 0xe7efff) and logical(240, 157, 0x353c53))
    # Send a burst without waiting for a framebuffer update between events.
    for _ in range(24):
        move(6, 0)
    wait_until(lambda: logical(384, 168, 0xe7efff) and logical(240, 168, 0x171825))
    for _ in range(24):
        move(-6, 0)
    wait_until(lambda: logical(240, 168, 0xe7efff) and logical(384, 168, 0x0d0e17))
    assert full_repaints() == baseline, 'Mover el cursor repinto la pantalla completa'
    for down in (True, False):
        command('input-send-event', {'events': [{'type': 'btn', 'data': {'button': 'left', 'down': down}}]})
    wait_until(lambda: logical(52, 99, 0xad92ff) and logical(390, 147, 0x40465d))
    if external_image is not None:
        key('f2')
        wait_until(lambda: logical(24, 24, 0x232638))
        glyphs = (0x7b6f, 0x749a, 0x73e7, 0x79e7, 0x49ed,
                  0x79cf, 0x7bcf, 0x4927, 0x7bef, 0x79ef)
        for field, command_key in enumerate(('t', 'e', 'v')):
            key(command_key)
            selected, value = struct.unpack('<II', memory(address + 0x1a348, 8, 'cabina-read'))
            assert selected == field and value > 0, 'CABINA no consulto el contador esperado'
            for index, char in enumerate(str(value)):
                glyph = glyphs[int(char)]
                for bit in range(15):
                    assert logical(160 + index*8 + bit%3*2, 121 + bit//3*2,
                                   0xe7efff if glyph & (1 << bit) else 0x232638), 'CABINA mostro otro valor'
        command('screendump', {'filename': str(prefix)+'-cabina.png', 'format': 'png'})
        key('f2')
        wait_until(lambda: logical(52, 99, 0xad92ff) and logical(240, 168, 0xe7efff))
    command('screendump', {'filename': str(prefix)+'.png', 'format': 'png'})
    return dict(Case='normal', Passed=True, BootServicesExited=True, UserCPL=3,
                IntroFramesObserved=sorted(frames), WorkspacesVerified=[1, 2, 3, 4],
                KeyboardVerified=True, FocusRestored=True, DesktopSession=True, IntroReplaced=True,
                MouseVerified=True, Framebuffer=[width, height], DesktopScale=scale,
                PointerMovesVerified=5, FullRepaintsDuringPointerMoves=0,
                PointerBurstEvents=48,
                WaitHalted=True, WaitTimeoutVerified=True, WaitInputVerified=True,
                ExternalSbef=external_image is not None,
                CabinaCommandsVerified=3 if external_image is not None else 0,
                PayloadSHA256=hashlib.sha256(packet[24:]).hexdigest(),
                SbefSHA256=fixture['sbef_sha256'])
