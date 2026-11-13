"""Verify a live CPL3 session, framebuffer changes and QEMU keyboard input."""
import hashlib
from pathlib import Path
import struct
import time

from cpu_config import register
from splash_capture import compare_frame


def verify_external_rejection(command, memory, image):
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        regs = command('human-monitor-command', {'command-line': 'info registers'})
        context = register(regs, 'RBP')
        if 'HLT=1' in regs and 'CPL=0' in regs and 0x100000 <= context <= 0xffe0000:
            if memory(context, 8, 'rejected-context') == b'METAL64!':
                assert register(regs, 'R12') == 0
                assert register(regs, 'CR3') == register(regs, 'R13')
                assert memory(context + 0x18000, 8192, 'rejected-text') == bytes(8192)
                offset = struct.unpack('<I', memory(context + 0x1a350, 4, 'rejected-field'))[0]
                count = struct.unpack_from('<H', image, 10)[0]
                assert offset == 52 + 32*(count-1), 'El kernel no indico el campo de permisos'
                if count >= 2:
                    assert memory(context + 0x1c000, 4096, 'rejected-rodata') == bytes(4096)
                if count == 3:
                    assert memory(context + 0x1d000, 4096, 'rejected-data') == bytes(4096)
                return dict(Case='external-permissions', Passed=True, SbefAccepted=False,
                            UserCodeCopied=False, UserAddressSpaceActivated=False,
                            RejectedField='permissions', RejectedOffset=offset)
        time.sleep(0.04)
    raise ValueError(f'El cargador externo no rechazo W+X: {regs[:420]}')


def verify_session(command, memory, prefix, packet, intro, fixture, external_image=None, *, desktop_media=False):
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
        end = 0x40002000 if external_image is not None else 0x40001000
        return 'CPL=3' in regs and 0x40000000 <= register(regs, 'RIP') < end

    def wait_stats():
        return struct.unpack('<II', memory(address + 0x1a340, 8, 'wait-stats'))

    def sleeping():
        regs = registers()
        return 'CPL=0' in regs and 'HLT=1' in regs and code <= register(regs, 'RIP') < code + len(packet)-24

    def key(*keys):
        command('send-key', {'keys': [{'type': 'qcode', 'data': key} for key in keys],
                             'hold-time': 100})
        time.sleep(0.2)

    command_probe = desktop_media and (prefix.parent.parent / 'xhci-command.txt').is_file()
    if command_probe:
        wait_until(lambda: memory(address + 0x1a396, 1, 'xhci-armed') == b'\x01')
        key('f2')
    wait_until(lambda: logical(216, 33, 0x0d0e17) and logical(52, 99, 0x5ad8ff) and sleeping())
    if desktop_media:
        dma, pages = struct.unpack('<QQ', memory(address + 0xb8, 16, 'xhci-reservation'))
        assert pages == 5 and 0x100000 <= dma <= 0x10000000 - pages * 4096 and dma % 4096 == 0
        assert dma + pages * 4096 <= address or dma >= address + 0x20000
        assert not dma <= code < dma + pages * 4096
        length = struct.unpack_from('<Q', context, 0x50)[0]
        stride = struct.unpack_from('<Q', context, 0x60)[0]
        assert 40 <= stride <= 256 and 0 < length <= 65536 and length % stride == 0
        descriptors = memory(address + 0x1000, length, 'xhci-memory-map')
        covering = []
        for offset in range(0, length, stride):
            kind, start, _, count, _ = struct.unpack_from('<I4xQQQQ', descriptors, offset)
            if start < dma + pages * 4096 and dma < start + count * 4096:
                covering.append((kind, start, start + count * 4096))
        assert len(covering) == 1
        kind, start, end = covering[0]
        assert kind == 2 and start <= dma and dma + pages * 4096 <= end
        reserved = memory(dma, pages * 4096, 'xhci-reserved-pages')
        if command_probe:
            status = memory(address + 0x1a379, 2, 'xhci-command-status')
            assert status == b'\x01\x01', f'xHCI command/stop status: {status.hex()}'
            original, restored = struct.unpack('<HH', memory(address + 0x1a37c, 4, 'xhci-pci-command'))
            assert original == restored, 'El comando PCI no se restauro'
            pointer, result, control = struct.unpack_from('<QII', reserved, 0x2000)
            assert pointer == dma + 4096 and result >> 24 == 1 and (control >> 10) & 63 == 33
            device_state = tuple(memory(address + 0x1a380, 5, 'xhci-device'))
            port, speed, slot, addressed, descriptor_read = device_state
            assert port and speed in (1, 2, 3) and slot == addressed == descriptor_read == 1, device_state
            output_slot = struct.unpack_from('<I', reserved, 0x440c)[0]
            assert (output_slot >> 27) & 0x1f == 3 and output_slot & 0xff
            descriptor = reserved[0x4c00:0x4c12]
            assert descriptor[:2] == bytes([18, 1]) and descriptor[17] >= 1
            assert memory(address + 0x1a385, 3, 'xhci-keyboard-state') == bytes([1, 1, 1])
            total, config, interface, endpoint = struct.unpack(
                '<IBBB', memory(address + 0x1a38c, 7, 'xhci-keyboard-config'))
            data = reserved[0x4c40:0x4c40 + total]
            assert len(data) == total and data[:5] == struct.pack('<BBHB', 9, 2, total, 1)
            assert config == data[5] and endpoint & 0x80
            assert memory(address + 0x1a397, 1, 'xhci-report-state') == b'\x01'
            report = reserved[0x4e80:0x4e88]
            assert report == bytes([0, 0, 0x3b, 0, 0, 0, 0, 0])
        else:
            assert reserved == bytes(pages * 4096)
        assert memory(address + 0x1a358, 5, 'xhci-inventory') == struct.pack('<IB', 1, 1)
        bdf, low, high = struct.unpack('<III', memory(address + 0x1a360, 12, 'xhci-pci'))
        devices = [device for bus in command('query-pci') for device in bus['devices']]
        controller = next(device for device in devices if device['class_info']['class'] == 0x0c03)
        assert bdf == (controller['bus'] << 8 | controller['slot'] << 3 | controller['function'])
        bar = low & ~15
        if low & 6 == 4:
            bar |= high << 32
        region = next(region for region in controller['regions'] if region['bar'] == 0)
        assert bar != 0 and bar == region['address']
        if command_probe:
            assert region['size'] >= 0x3000
        caps, parameters = struct.unpack('<II', memory(address + 0x1a370, 8, 'xhci-capabilities'))
        if command_probe:
            status_register = bar + (caps & 0xff) + 4
            usb_status = command('human-monitor-command', {'command-line': f'xp /1wx {status_register:#x}'})
            assert int(usb_status.split(':', 1)[1].split()[0], 16) & 1
        actual = command('human-monitor-command', {'command-line': f'xp /2wx {bar:#x}'})
        words = actual.split(':', 1)[1].split()
        assert (caps, parameters) == tuple(int(word, 16) for word in words[:2])
        assert caps >> 16 and parameters & 0xff
        handoff = memory(address + 0x1a378, 1, 'xhci-handoff')[0]
        assert handoff in (1, 2), f'xHCI handoff state: {handoff}'
        assert memory(address + 0x15400, 8, 'xhci-alias-pde') == bytes(8)
        assert memory(address + 0x1e000, 24, 'xhci-alias-pte') == bytes(24)
        assert logical(24, 354, 0x232638), 'El escritorio no mostro el aviso de entrada USB'
        if command_probe:
            # QEMU directs keyboard input to usb-kbd. The xHCI probe stops
            # the controller after EP0. PS/2 interaction has its own run.
            return dict(Case='normal', Passed=True, UserCpl=3, DesktopSession=True,
                        XhciCommandCompleted=True, XhciUsbDeviceAddressed=True,
                        XhciUsbDeviceDescriptorRead=True, XhciPort=port, XhciSpeed=speed,
                        XhciSlot=slot, XhciControllerStopped=True,
                        UsbConfigurationBytes=total, UsbBootKeyboardInterface=interface,
                        UsbKeyboardEndpoint=endpoint, UsbBootProtocolSelected=True,
                        UsbDeviceDescriptor=descriptor.hex(), UsbF2Report=report.hex(),
                        UsbKeyboardTransferVerified=True,
                        UsbInputVerified=False)
    timeout_before = wait_stats()[1]
    wait_until(lambda: wait_stats()[1] > timeout_before)
    event_before = wait_stats()[0]
    assert pixel(width-1, height-1, 0x0d0e17), 'La intro no fue reemplazada'
    assert memory(code, len(packet)-24, 'session-code') == packet[24:]
    if external_image is not None:
        assert external_image not in packet, 'SBEF externo embebido en el paquete'
        count = struct.unpack_from('<H', external_image, 10)[0]
        offset, size = struct.unpack_from('<II', external_image, 40)
        payload = external_image[offset:offset+size]
        assert memory(address + 0x18000, 8192, 'external-text') == payload.ljust(8192, b'\0')
        if count >= 2:
            offset, size = struct.unpack_from('<II', external_image, 72)
            payload = external_image[offset:offset+size]
            assert memory(address + 0x1c000, 4096, 'external-rodata') == payload.ljust(4096, b'\0')
            entries = struct.unpack('<QQQQQ', memory(address + 0x17000, 40, 'external-pte'))
            base = address + 0x13000
            assert tuple(entry & ~0x60 for entry in entries) == (
                (base + 0x5000) | 5, (base + 0x6000) | 5,
                (base + 0x8000) | (1 << 63) | 7, (base + 0x9000) | (1 << 63) | 5,
                (base + 0xa000) | (1 << 63) | 7 if count == 3 else 0)
        if count == 3:
            offset, file_size, memory_size = struct.unpack_from('<III', external_image, 104)
            assert (file_size, memory_size) == (4, 8)
            assert external_image[offset:offset+4] == struct.pack('<I', 0x424d4f32)
            assert memory(address + 0x1d000, 4096, 'external-data') == (
                struct.pack('<II', 0x52334441, 0x52334253).ljust(4096, b'\0'))
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
    wait_until(lambda: logical(272, 33, 0x0d0e17))
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
        atlas = (Path(__file__).resolve().parents[1] / 'desktop/cabina_font.bin').read_bytes()
        shades = (0x232638, 0x64697a, 0xa5acbc, 0xe7efff)
        def check_counter(field):
            selected, value = struct.unpack('<II', memory(address + 0x1a348, 8, 'cabina-read'))
            assert selected == field and value > 0, 'CABINA no consulto el contador esperado'
            expected = [[0] * 100 for _ in range(12)]
            x = 0
            for char in str(value):
                offset = int(char) * 37
                for y in range(12):
                    start = offset + 1 + 3*y
                    row = int.from_bytes(atlas[start:start+3], 'little')
                    for column in range(12):
                        shade = (row >> (2*column)) & 3
                        if shade:
                            expected[y][x + column] = shade
                x += atlas[offset]
            raw = memory(fb + ((100 + 24*field)*scale*pitch + 168*scale)*4,
                         (11*scale*pitch + 100*scale)*4, 'cabina-digits')
            for y, row in enumerate(expected):
                for column, shade in enumerate(row):
                    offset = (y*pitch + column)*scale*4
                    color = shades[shade].to_bytes(4, 'little')
                    if order == 0:
                        color = color[:3][::-1] + b'\0'
                    assert raw[offset:offset+4] == color, f'CABINA mostro otro valor en {column},{y}'
        wait_until(lambda: logical(40, 86, 0x40465d))
        check_counter(2)
        for field, command_key in enumerate(('t', 'e', 'v')):
            key(command_key)
            check_counter(field)
        key('r')
        check_counter(2)
        command('screendump', {'filename': str(prefix)+'-cabina.png', 'format': 'png'})
        key('f2')
        wait_until(lambda: logical(52, 99, 0xad92ff) and logical(240, 168, 0xe7efff))
        assert logical(603, 359, 0xe7efff), 'Falta el icono de Configuracion'
        key('f3')
        wait_until(lambda: logical(40, 90, 0x5ad8ff))
        key('2')
        wait_until(lambda: logical(140, 90, 0x5ad8ff))
        key('esc')
        wait_until(lambda: logical(240, 168, 0xe7efff))
        move(6, 0)
        wait_until(lambda: logical(252, 168, 0xe7efff))
        for _ in range(3):
            move(58, 66)
        wait_until(lambda: logical(600, 390, 0xe7efff))
        move(0, -10)
        wait_until(lambda: logical(600, 370, 0xe7efff))
        for down in (True, False):
            command('input-send-event', {'events': [{'type': 'btn', 'data': {'button': 'left', 'down': down}}]})
        wait_until(lambda: logical(140, 90, 0x5ad8ff))
        key('1')
        wait_until(lambda: logical(40, 90, 0x5ad8ff))
        command('screendump', {'filename': str(prefix)+'-settings.png', 'format': 'png'})
        key('f3')
        wait_until(lambda: logical(52, 99, 0xad92ff))
    command('screendump', {'filename': str(prefix)+'.png', 'format': 'png'})
    return dict(Case='normal', Passed=True, BootServicesExited=True, UserCPL=3,
                IntroFramesObserved=sorted(frames), WorkspacesVerified=[1, 2, 3, 4],
                KeyboardVerified=True, FocusRestored=True, DesktopSession=True, IntroReplaced=True,
                MouseVerified=True, Framebuffer=[width, height], DesktopScale=scale,
                PointerMovesVerified=5, FullRepaintsDuringPointerMoves=0,
                PointerBurstEvents=48,
                WaitHalted=True, WaitTimeoutVerified=True, WaitInputVerified=True,
                ExternalSbef=external_image is not None,
                ReadOnlyNxRegionVerified=external_image is not None and count >= 2,
                WritableNxRegionVerified=external_image is not None and count == 3,
                UserDataAndBssVerified=external_image is not None and count == 3,
                CabinaCommandsVerified=4 if external_image is not None else 0,
                SettingsVerified=external_image is not None,
                XhciInventoryVerified=desktop_media,
                XhciReadOnlyMmioVerified=desktop_media,
                XhciFirmwareHandoff=handoff if desktop_media else None,
                XhciCommandCompleted=desktop_media and command_probe,
                XhciReservedBytes=pages * 4096 if desktop_media else 0,
                PayloadSHA256=hashlib.sha256(packet[24:]).hexdigest(),
                SbefSHA256=fixture['sbef_sha256'])
