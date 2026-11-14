"""Verify a live CPL3 session, framebuffer changes and QEMU keyboard input."""
import hashlib
import re
from pathlib import Path
import struct
import time

from cpu_config import l1_cache_profile, register
from splash_capture import compare_frame


def verify_bootlog_file(image, prefix):
    expected = Path(str(prefix) + '-bootlog-expected.bin').read_bytes()
    with image.open('rb') as disk:
        disk.seek(512 + 72)
        table = struct.unpack('<Q', disk.read(8))[0]
        disk.seek(table * 512 + 32)
        volume = struct.unpack('<Q', disk.read(8))[0] * 512
        disk.seek(volume)
        bpb = disk.read(512)
        sectors = struct.unpack_from('<H', bpb, 14)[0]
        fat_size, root = struct.unpack_from('<I4xI', bpb, 36)
        data = volume + (sectors + bpb[16] * fat_size) * 512
        cluster_size = bpb[13] * 512

        def read_cluster(cluster):
            disk.seek(data + (cluster - 2) * cluster_size)
            return disk.read(cluster_size)

        def find(cluster, name):
            block = read_cluster(cluster)
            for offset in range(0, len(block), 32):
                entry = block[offset:offset+32]
                if entry[:11] == name:
                    return ((int.from_bytes(entry[20:22], 'little') << 16)
                            | int.from_bytes(entry[26:28], 'little'),
                            int.from_bytes(entry[28:32], 'little'))
            raise ValueError(f'Falta {name!r} en el volumen FAT32 invitado')

        folder, _ = find(root, b'BMO-X2     ')
        cluster, size = find(folder, b'BOOTLOG TXT')
        if size != len(expected) or read_cluster(cluster)[:size] != expected:
            raise ValueError('BOOTLOG.TXT de FAT32 difiere de la captura UEFI')
    Path(str(prefix) + '-BOOTLOG.TXT').write_bytes(expected)


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
        wait_until(lambda: memory(address + 0x1a396, 1, 'xhci-rearmed') == b'\x03')
        key('f3')
    if command_probe:
        wait_until(lambda: logical(24, 24, 0x232638) and sleeping()
                   and memory(address + 0x1a398, 1, 'xhci-delivered') == b'\x03')
        command('screendump', {'filename': str(prefix) + '-usb-cabina.png', 'format': 'png'})
    else:
        wait_until(lambda: logical(216, 33, 0x0d0e17) and logical(52, 99, 0x5ad8ff) and sleeping())
    def input_label(x, tag):
        stride = pitch * 4
        length = 115 * scale * 4
        data = memory(fb + (372*scale*pitch + x*scale)*4, 11*scale*stride + length, tag)
        return tuple(data[row*stride:row*stride+length] for row in range(0, 11*scale+1, scale))

    if external_image is not None and not command_probe:
        assert logical(24, 354, 0x232638), 'Falta el panel de entrada al arrancar'
        keyboard_before = input_label(36, 'keyboard-before')
        mouse_before = input_label(260, 'mouse-before')
    cache = l1_cache_profile(memory(address + 0xd0, 32, 'cpu-l1')) if desktop_media else None
    if desktop_media:
        assert memory(address + 0xf0, 1, 'bootlog-status') == b'\x01', 'UEFI no pudo guardar BOOTLOG.TXT'
        raw = memory(address + 0x800, 128, 'bootlog-expected-buffer')
        match = re.match(rb'BMO-X2 V1 UEFI\r\nSBEF=([0-9A-F]{8})\r\nCPUID=([0-9A-F]{8})\r\n'
                         rb'PS2=[0-9A-F]{8}\r\nXHCI=00000001\r\n', raw)
        assert (match and int(match[1], 16) == len(external_image)
                and int(match[2], 16) == int(cache['Leaf'] or '0', 16)), 'Informe UEFI invalido'
        Path(str(prefix) + '-bootlog-expected.bin').write_bytes(match[0])
        staging, image_bytes = struct.unpack('<QQ', memory(address + 0xa8, 16, 'desktop-staging'))
        staging_pages = struct.unpack('<Q', memory(address + 0xc8, 8, 'desktop-staging-pages'))[0]
        assert image_bytes == len(external_image)
        assert staging_pages == (image_bytes + 4095) // 4096
        assert memory(staging, image_bytes, 'desktop-staging-image') == external_image
        dma, pages = struct.unpack('<QQ', memory(address + 0xb8, 16, 'xhci-reservation'))
        assert pages == 5 and 0x100000 <= dma <= 0x10000000 - pages * 4096 and dma % 4096 == 0
        assert dma + pages * 4096 <= address or dma >= address + 0x20000
        assert not dma <= code < dma + pages * 4096
        length = struct.unpack_from('<Q', context, 0x50)[0]
        stride = struct.unpack_from('<Q', context, 0x60)[0]
        assert 40 <= stride <= 256 and 0 < length <= 65536 and length % stride == 0
        descriptors = memory(address + 0x1000, length, 'xhci-memory-map')
        staging_end = staging + staging_pages * 4096
        memory_map = list(struct.iter_unpack('<I4xQQQQ' + f'{stride - 40}x', descriptors))
        assert staging % 4096 == 0 and any(
            kind == 2 and start <= staging and staging_end <= start + count * 4096
            for kind, start, _, count, _ in memory_map
        )
        if staging_pages < 5:
            assert any(kind == 7 and start <= staging_end and staging + 5 * 4096 <= start + count * 4096
                       for kind, start, _, count, _ in memory_map)
        covering = []
        for kind, start, _, count, _ in memory_map:
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
            assert memory(address + 0x1a397, 1, 'xhci-report-state') == b'\x03'
            reports = [reserved[offset:offset + 8] for offset in range(0x4e80, 0x4e98, 8)]
            assert reports == [bytes([0, 0, usage, 0, 0, 0, 0, 0]) for usage in (0x3b, 0, 0x3c)]
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
        if not command_probe:
            assert logical(24, 354, 0x232638), 'El escritorio no mostro el aviso de entrada USB'
        if command_probe:
            # QEMU routes these keys to usb-kbd. This run ends with DMA stopped.
            return dict(Case='normal', Passed=True, UserCpl=3, DesktopSession=True,
                        XhciCommandCompleted=True, XhciUsbDeviceAddressed=True,
                        XhciUsbDeviceDescriptorRead=True, XhciPort=port, XhciSpeed=speed,
                        XhciSlot=slot, XhciControllerStopped=True,
                        UsbConfigurationBytes=total, UsbBootKeyboardInterface=interface,
                        UsbKeyboardEndpoint=endpoint, UsbBootProtocolSelected=True,
                        UsbDeviceDescriptor=descriptor.hex(), UsbF2Report=reports[0].hex(),
                        UsbKeyboardReports=[report.hex() for report in reports],
                        UsbKeyboardTransferVerified=True,
                        UsbInputVerified=True, UsbCabinaVerified=True, CpuL1=cache)
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
    if external_image is not None:
        assert input_label(36, 'keyboard-after') != keyboard_before
        assert input_label(260, 'mouse-idle') == mouse_before

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
    if external_image is not None:
        assert input_label(260, 'mouse-after') != mouse_before
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
    closed = {}
    if external_image is not None and count == 3:
        descriptor = address + 0x1a000
        bridge_cr3 = struct.unpack('<Q', memory(descriptor + 0x318, 8, 'bridge-cr3'))[0]
        reuse = desktop_media and (prefix.parent.parent / 'reuse-session.txt').is_file()

        def close_session():
            key('f2')
            wait_until(lambda: logical(24, 24, 0x232638))
            for letter in 'session exit':
                key('spc' if letter == ' ' else letter)
            key('ret')

        def session_closed():
            regs = registers()
            return ('CPL=0' in regs and 'HLT=1' in regs and register(regs, 'R12') == 5
                    and register(regs, 'CR3') == bridge_cr3 and not register(regs, 'EFER') & 1)

        def verify_closed():
            wait_until(session_closed)
            assert memory(address + 0x17000, 40, 'closed-pte') == bytes(40)
            assert memory(address + 0x18000, 8192, 'closed-text') == bytes(8192)
            assert memory(address + 0x1b000, 12288, 'closed-stack-and-data') == bytes(12288)

        close_session()
        verify_closed()
        closed = dict(SessionClosed=True, SyscallGateDisabled=True, UserPagesUnmapped=5, UserBytesScrubbed=20480)
        if reuse:
            def owner(expected):
                return memory(descriptor + 0x3a8, 1, 'session-owner') == bytes([expected])

            assert owner(1)
            key('f4')
            wait_until(lambda: owner(2) and logical(52, 99, 0x5ad8ff)
                       and logical(320, 200, 0xe7efff) and sleeping())
            regs = registers()
            assert register(regs, 'EFER') & 1 and register(regs, 'CR3') == base
            new_entries = struct.unpack('<QQQQQ', memory(address + 0x17000, 40, 'reused-pte'))
            assert tuple(entry & ~0x60 for entry in new_entries) == tuple(entry & ~0x60 for entry in entries)
            assert memory(address + 0x1d000, 8, 'reused-data') == struct.pack('<II', 0x52334441, 0x52334253)
            key('2')
            wait_until(lambda: logical(52, 99, 0xad92ff))
            close_session()
            verify_closed()
            assert owner(3)
            closed.update(SessionsCompleted=2, ReusedUserPages=5, SecondSessionInputVerified=True)
    return dict(Case='normal', Passed=True, BootServicesExited=True, UserCPL=3,
                IntroFramesObserved=sorted(frames), WorkspacesVerified=[1, 2, 3, 4],
                KeyboardVerified=True, FocusRestored=True, DesktopSession=True, IntroReplaced=bool(intro),
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
                DesktopStagingBytes=staging_pages * 4096 if desktop_media else None,
                DesktopStagingReturnedBytes=(5 - staging_pages) * 4096 if desktop_media else None,
                PayloadSHA256=hashlib.sha256(packet[24:]).hexdigest(),
                SbefSHA256=fixture['sbef_sha256'], CpuL1=cache,
                BootInputIndicatorsVerified=external_image is not None, **closed)
