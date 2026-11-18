"""Verify a live CPL3 session, framebuffer changes and QEMU keyboard input."""
import hashlib
import re
from pathlib import Path
import struct
import sys
import time

from cpu_config import l1_cache_profile, register
from splash_capture import compare_frame

TOOLS = str(Path(__file__).resolve().parents[1])
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)
from host.sbef.format import load_plan as make_load_plan


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


def verify_external_mapping(memory, context_address, image):
    plan = make_load_plan(image)
    if plan['AbiVersion'] != 1 or not 1 <= plan['RegionCount'] <= 3:
        raise ValueError('La sonda de escritorio solo ejecuta SBEF ABI 1 de una a tres regiones')

    layouts = {1: ['RX'], 2: ['RX', 'R'], 3: ['RX', 'R', 'RW']}
    if [region['Permissions'] for region in plan['Regions']] != layouts[plan['RegionCount']]:
        raise ValueError('La sonda actual solo admite las secuencias RX, RX/R y RX/R/RW')

    page_table = struct.unpack('<512Q', memory(context_address + 0x17000, 4096, 'external-user-pte'))
    slots = {'RX': 0x40000000, 'R': 0x40003000, 'RW': 0x40004000}
    frames = {
        'RX': (context_address + 0x18000, context_address + 0x19000),
        'R': (context_address + 0x1c000,),
        'RW': (context_address + 0x1d000,),
    }
    mapped_slots = set()
    mapped_frames = set()
    page_count = 0
    zero_fill_bytes = 0
    immutable_file_bytes = 0
    mutable_pages = 0
    physical_mask = 0x000ffffffffff000
    permission_mask = (1 << 63) | 7
    hardware_mutable_mask = 0x60

    for region in plan['Regions']:
        permissions = region['Permissions']
        if permissions not in slots or region['VirtualStart'] != slots[permissions]:
            raise ValueError(f'La sonda actual no admite region SBEF {permissions} en 0x{region["VirtualStart"]:X}')
        if not region['User']:
            raise ValueError(f'La region SBEF {region["Index"]} no esta marcada como usuario en el plan HOST')
        if region['PageCount'] > len(frames[permissions]):
            raise ValueError(f'La region SBEF {permissions} excede las paginas reservadas por la sonda')
        if permissions in ('R', 'RW') and region['PageCount'] != 1:
            raise ValueError(f'La sonda actual requiere una pagina para la region {permissions}')

        expected_permissions = 5 | (2 if region['Writable'] else 0)
        if region['NoExecute']:
            expected_permissions |= 1 << 63
        actual_region = bytearray()
        for page in range(region['PageCount']):
            virtual = region['VirtualStart'] + page * 4096
            slot = (virtual - 0x40000000) // 4096
            if slot >= len(page_table) or slot == 2 or slot in mapped_slots:
                raise ValueError(f'La region SBEF colisiona con una entrada reservada: VA 0x{virtual:X}')
            pte = page_table[slot]
            if pte & permission_mask != expected_permissions:
                raise ValueError(f'Permisos PTE distintos del plan HOST en VA 0x{virtual:X}')
            physical = pte & physical_mask
            expected_frame = frames[permissions][page]
            expected_pte = expected_frame | expected_permissions
            if physical != expected_frame or physical in mapped_frames:
                raise ValueError(f'Marco fisico distinto del plan SBEF en VA 0x{virtual:X}')
            if (pte & ~hardware_mutable_mask) != expected_pte:
                raise ValueError(f'Flags PTE inesperados respecto al plan HOST en VA 0x{virtual:X}')
            mapped_slots.add(slot)
            mapped_frames.add(physical)
            if not region['Writable']:
                actual_region.extend(memory(physical, 4096, f'external-region-{region["Index"]}-page-{page}'))

        if region['Writable']:
            # The guest has run by this checkpoint; Ring 3 may have changed
            # initialized data and BSS. Its PTE/frame are verified above, but
            # comparing its current bytes with the load-time image is invalid.
            mutable_pages += region['PageCount']
        else:
            expected_bytes = image[region['FileOffset']:region['FileEnd']]
            expected_bytes = expected_bytes.ljust(region['MappedBytes'], b'\0')
            if bytes(actual_region) != expected_bytes:
                raise ValueError(f'Contenido o cola inmutable distinto del plan HOST en region {region["Index"]}')
            immutable_file_bytes += region['FileBytes']
            zero_fill_bytes += region['ZeroFillBytes']
        page_count += region['PageCount']

    stack = page_table[2]
    expected_stack = (context_address + 0x1b000) | (1 << 63) | 7
    if (stack & ~hardware_mutable_mask) != expected_stack:
        raise ValueError('La pila separada no tiene permiso RW/NX de usuario en su pagina reservada')
    for slot, pte in enumerate(page_table):
        if slot not in mapped_slots and slot != 2 and pte:
            raise ValueError(f'La sonda dejo un mapeo de usuario fuera del plan HOST en la pagina {slot}')

    return plan, page_table[:5], dict(
        SbefMappingPlanVerified=True,
        SbefMappedPagesVerified=page_count,
        SbefZeroFillBytesVerified=zero_fill_bytes,
        SbefImmutableFileBytesVerified=immutable_file_bytes,
        SbefWritablePagesContentSkipped=mutable_pages,
    )


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
    map_evidence = dict(SbefMappingPlanVerified=False, SbefMappedPagesVerified=0,
                        SbefZeroFillBytesVerified=0, SbefImmutableFileBytesVerified=0,
                        SbefWritablePagesContentSkipped=0)
    mapping_plan = None
    entries = None
    count = None
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

    def verify_mapping():
        nonlocal mapping_plan, entries, count, map_evidence
        if external_image is not None and mapping_plan is None:
            mapping_plan, entries, map_evidence = verify_external_mapping(memory, address, external_image)
            count = mapping_plan['RegionCount']

    def key(*keys):
        command('send-key', {'keys': [{'type': 'qcode', 'data': key} for key in keys],
                             'hold-time': 100})
        time.sleep(0.2)

    def bootlog():
        assert memory(address + 0xf0, 1, 'bootlog-status') == b'\x01', 'UEFI no pudo guardar BOOTLOG.TXT'
        raw = memory(address + 0x800, 224, 'bootlog-expected-buffer')
        match = re.match(rb'BMO-X2 V3 UEFI\r\nSBEF=([0-9A-F]{8})\r\nCPUID=([0-9A-F]{8})\r\n'
                         rb'PS2=[0-9A-F]{8}\r\nXHCI=([0-9A-F]{8})\r\n'
                         rb'BDF ID CMD BAR0_LO BAR0_HI\r\n'
                         rb'((?:(?:[0-9A-F-]{8} ){4}[0-9A-F-]{8}\r\n){2})', raw)
        cache = l1_cache_profile(memory(address + 0xd0, 32, 'cpu-l1'))
        assert (match and int(match[1], 16) == len(external_image)
                and int(match[2], 16) == int(cache['Leaf'] or '0', 16)), 'Informe UEFI invalido'
        devices = {(device['bus'] << 8 | device['slot'] << 3 | device['function']): device
                   for bus in command('query-pci') for device in bus['devices']
                   if device['class_info']['class'] == 0x0c03}
        assert int(match[3], 16) == len(devices)
        for row, bdf in zip(match[4].splitlines(), sorted(devices)[:2], strict=False):
            actual_bdf, device_id, pci_command, low, high = (int(value, 16) for value in row.split())
            device = devices[bdf]
            bar = next(region for region in device['regions'] if region['bar'] == 0)
            assert actual_bdf == bdf
            assert device_id == device['id']['device'] << 16 | device['id']['vendor']
            assert pci_command & 2 and low & 1 == 0
            assert ((high << 32) | (low & ~15)) == bar['address']
        Path(str(prefix) + '-bootlog-expected.bin').write_bytes(match[0])
        return cache, match

    launcher = desktop_media and (prefix.parent.parent / 'ultra-j-launcher.txt').is_file()
    if launcher or (desktop_media and (prefix.parent.parent / 'sheet-desktop.txt').is_file()):
        icon_color = 0xa8c5ff if launcher else 0xe7efff
        wait_until(lambda: logical(70, 55, icon_color) and sleeping())
        verify_mapping()
        if launcher:
            command('screendump', {'filename': str(prefix) + '-launcher-desktop.png', 'format': 'png'})
        for dx, dy in [(-120, -120), (-122, -8)]:
            command('input-send-event', {'events': [
                {'type': 'rel', 'data': {'axis': 'x', 'value': dx}},
                {'type': 'rel', 'data': {'axis': 'y', 'value': dy}},
            ]})
            time.sleep(0.08)
        wait_until(lambda: logical(78, 72, 0xe7efff) and sleeping())

        def click():
            for down in (True, False):
                command('input-send-event', {'events': [
                    {'type': 'btn', 'data': {'button': 'left', 'down': down}},
                ]})
                time.sleep(0.045)

        click()
        time.sleep(0.7)
        assert logical(250, 110, 0x232638), 'Un clic abrio el lanzador'
        click()
        wait_until(lambda: logical(250, 110, 0x232638) and sleeping())
        click()
        if launcher:
            wait_until(lambda: logical(200, 220, 0xa8c5ff) and sleeping())
            command('screendump', {'filename': str(prefix) + '-launcher-ready.png', 'format': 'png'})
            key('ret')
            wait_until(lambda: logical(200, 220, 0xa0e5ca) and sleeping())
            action = (prefix.parent.parent / 'ACTION.UJB').read_bytes()
            assert action not in external_image
            assert memory(address + 0x1cdf8, 520, 'launcher-action') == (
                struct.pack('<Q', len(action)) + action.ljust(512, b'\0'))
            assert memory(address + 0x1d010, 256, 'launcher-arena') == bytes(256)
        else:
            wait_until(lambda: logical(250, 110, 0xe7efff) and sleeping())
        screenshot = '-launcher-active.png' if launcher else '-sheet.png'
        command('screendump', {'filename': str(prefix) + screenshot, 'format': 'png'})
        if launcher:
            key('q')
            assert logical(200, 220, 0xa0e5ca), 'Q sin Super cerro ULTRA-J'
            key('meta_l', 'q')
        else:
            key('esc')
        wait_until(lambda: logical(250, 110, 0x232638) and logical(70, 55, icon_color) and sleeping())
        cache, _ = bootlog()
        if launcher:
            key('ctrl', 'meta_l', '2')
            wait_until(lambda: logical(52, 99, 0xad92ff) and sleeping())
            click()
            click()
            wait_until(lambda: logical(200, 220, 0xa8c5ff) and sleeping())
            key('meta_r', 'q')
            wait_until(lambda: logical(52, 99, 0xad92ff) and sleeping())
            click()
            click()
            wait_until(lambda: logical(200, 220, 0xa8c5ff) and sleeping())
            key('esc')
            wait_until(lambda: logical(52, 99, 0xad92ff) and sleeping())
            return dict(Case='normal', Passed=True, UserCpl=3, **map_evidence,
                        UltraJDoubleClickVerified=True,
                        UltraJExternalAction=True, UltraJArenaCleared=True, UltraJCloseVerified=True,
                        SuperQVerified=True, WorkspacePreserved=True, EscapeVerified=True,
                        Framebuffer=dict(Width=width, Height=height, PitchPixels=pitch,
                                         VisibleRowsBytes=pitch * height * 4),
                        IntroFramesObserved=sorted(frames), CpuL1=cache)
        return dict(Case='normal', Passed=True, UserCpl=3, **map_evidence,
                    SheetDoubleClickVerified=True,
                    SheetCloseVerified=True, IntroFramesObserved=sorted(frames), CpuL1=cache)

    if desktop_media and (prefix.parent.parent / 'ultra-j-view.txt').is_file():
        probes = ((0, 0, 0x10121a), (110, 96, 0x10121a), (130, 110, 0x1b1f2c),
                  (150, 239, 0x293850), (380, 239, 0xa8c5ff))
        wait_until(lambda: all(logical(*probe) for probe in probes) and sleeping())
        verify_mapping()
        action = (prefix.parent.parent / 'ACTION.UJB').read_bytes()
        assert action not in external_image
        assert memory(address + 0x1cdf8, 520, 'ultra-j-action') == (
            struct.pack('<Q', len(action)) + action.ljust(512, b'\0'))
        rodata = struct.unpack('<Q', memory(address + 0x17018, 8, 'ultra-j-rodata-pte'))[0]
        assert rodata & ((1 << 63) | 7) == ((1 << 63) | 5)
        command('screendump', {'filename': str(prefix) + '-ultra-j-ready.png', 'format': 'png'})
        key('ret')
        wait_until(lambda: logical(150, 239, 0x233d35) and logical(380, 239, 0xa0e5ca))
        assert memory(address + 0x1d008, 256, 'ultra-j-action-arena') == bytes(256)
        command('screendump', {'filename': str(prefix) + '-ultra-j-active.png', 'format': 'png'})
        key('ret')
        wait_until(lambda: logical(150, 239, 0x233d35) and sleeping())
        key('esc')
        wait_until(lambda: all(logical(*probe) for probe in probes) and sleeping())
        cache, _ = bootlog()
        return dict(Case='normal', Passed=True, UserCpl=3, **map_evidence,
                    UltraJViewVerified=True,
                    UltraJButtonAction=True, UltraJArenaCleared=True, UltraJResetVerified=True,
                    UltraJExternalAction=True,
                    IntroFramesObserved=sorted(frames),
                    CpuL1=cache)

    command_probe = desktop_media and (prefix.parent.parent / 'xhci-command.txt').is_file()
    reset_probe = desktop_media and (prefix.parent.parent / 'xhci-reset.txt').is_file()
    transport_probe = desktop_media and (prefix.parent.parent / 'xhci-transport.txt').is_file()
    enum_probe = transport_probe and (prefix.parent.parent / 'xhci-enum.txt').is_file()
    reports_panel = transport_probe and (prefix.parent.parent / 'reports.txt').is_file()
    root_file = prefix.parent.parent / 'usb-root-port.txt'
    selected_root = int(root_file.read_text()) if root_file.is_file() else None
    mouse_probe = command_probe and (prefix.parent.parent / 'usb-mouse.txt').is_file()
    if mouse_probe:
        wait_until(lambda: logical(52, 99, 0x5ad8ff) and sleeping()
                   and memory(address + 0x1a3c8, 1, 'xhci-live') == b'\x01')
        verify_mapping()
        command('input-send-event', {'events': [
            {'type': 'rel', 'data': {'axis': 'x', 'value': 100}},
        ]})
        wait_until(lambda: logical(420, 200, 0xe7efff))
        for down in (True, False):
            command('input-send-event', {'events': [
                {'type': 'btn', 'data': {'button': 'left', 'down': down}},
            ]})
            if down:
                wait_until(lambda: logical(390, 147, 0x5ad8ff))
        wait_until(lambda: memory(address + 0x1a398, 1, 'xhci-delivered')[0] >= 3)
        command('input-send-event', {'events': [
            {'type': 'rel', 'data': {'axis': 'x', 'value': -25}},
            {'type': 'rel', 'data': {'axis': 'y', 'value': -30}},
        ]})
        wait_until(lambda: logical(395, 170, 0xe7efff) and sleeping())
        command('screendump', {'filename': str(prefix) + '-usb-mouse.png', 'format': 'png'})
    elif command_probe:
        wait_until(lambda: memory(address + 0x1a396, 1, 'xhci-armed') == b'\x01')
        wait_until(lambda: logical(52, 99, 0x5ad8ff) and sleeping())
        verify_mapping()
        key('f2')
        wait_until(lambda: logical(40, 86, 0x40465d)
                   and memory(address + 0x1a3c8, 1, 'xhci-live') == b'\x01')
        wait_until(lambda: memory(address + 0x1a396, 1, 'xhci-rearmed') == b'\x03')
        for index in range(129):
            key('f3')
            expected = ((4 + 2*index) & 255).to_bytes(1, 'little')
            wait_until(lambda: memory(address + 0x1a398, 1, 'xhci-delivered') == expected)
        wait_until(lambda: logical(40, 86, 0x40465d) and sleeping()
                   and memory(address + 0x1a3c8, 1, 'xhci-live') == b'\x01')
        command('screendump', {'filename': str(prefix) + '-usb-cabina.png', 'format': 'png'})
    else:
        wait_until(lambda: logical(216, 33, 0x0d0e17) and logical(52, 99, 0x5ad8ff) and sleeping())
        verify_mapping()
    def input_label(x, tag):
        stride = pitch * 4
        length = 115 * scale * 4
        data = memory(fb + (372*scale*pitch + x*scale)*4, 11*scale*stride + length, tag)
        return tuple(data[row*stride:row*stride+length] for row in range(0, 11*scale+1, scale))

    if external_image is not None and not command_probe:
        assert logical(24, 354, 0x232638), 'Falta el panel de entrada al arrancar'
        keyboard_before = input_label(36, 'keyboard-before')
        mouse_before = input_label(260, 'mouse-before')
    cache = None
    if desktop_media:
        cache, match = bootlog()
        staging, image_bytes = struct.unpack('<QQ', memory(address + 0xa8, 16, 'desktop-staging'))
        staging_pages = struct.unpack('<Q', memory(address + 0xc8, 8, 'desktop-staging-pages'))[0]
        assert image_bytes == len(external_image)
        assert staging_pages == (image_bytes + 4095) // 4096
        assert memory(staging, image_bytes, 'desktop-staging-image') == external_image
        dma, pages = struct.unpack('<QQ', memory(address + 0xb8, 16, 'xhci-reservation'))
        assert pages == (10 if command_probe or transport_probe else 5)
        assert 0x100000 <= dma <= 0x10000000 - pages * 4096 and dma % 4096 == 0
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
        def check_report_hex(x, y, value, digits):
            atlas = (Path(__file__).resolve().parents[1] / 'desktop/cabina_font.bin').read_bytes()
            shades = (0x232638, 0x64697a, 0xa5acbc, 0xe7efff)
            glyphs = [atlas['0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'.index(c)*37:][:37]
                      for c in f'{value:0{digits}X}'[-digits:]]
            width = sum(glyph[0] for glyph in glyphs) + 12
            expected = [[0] * width for _ in range(12)]
            column = 0
            for glyph in glyphs:
                for row in range(12):
                    bits = int.from_bytes(glyph[1 + row*3:4 + row*3], 'little')
                    for bit in range(12):
                        shade = bits >> (bit*2) & 3
                        if shade:
                            expected[row][column + bit] = shade
                column += glyph[0]
            raw = memory(fb + (y*scale*pitch + x*scale)*4,
                         (11*scale*pitch + column*scale)*4, 'ep0-report-hex')
            for row in range(12):
                for col in range(column):
                    color = shades[expected[row][col]].to_bytes(4, 'little')
                    if order == 0:
                        color = color[:3][::-1] + b'\0'
                    assert raw[(row*pitch+col)*scale*4:][:4] == color, f'EP0 report differs at {x+col},{y+row}'
        if transport_probe:
            assert memory(address + 0x1a3c4, 1, 'transport-reservation-validated') == b'\x01'
            empty_ports = (prefix.parent.parent / 'xhci-empty-ports.txt').is_file()
            if empty_ports or (prefix.parent.parent / 'xhci-timer-fault.txt').is_file():
                if reports_panel:
                    assert logical(24, 254, 0xff6b7a), 'REPORTES no indica el fallo de descubrimiento'
                assert memory(address + 0x1a3e0, 4, 'transport-wait-failure') == struct.pack('<I', 19 if empty_ports else 18)
                assert memory(address + 0x1a379, 2, 'transport-no-command-halted') == b'\x00\x01'
                assert memory(address + 0x1a3fc, 4, 'transport-bounded-slices') == struct.pack('<I', 100 if empty_ports else 0)
                if empty_ports:
                    assert memory(address + 0x1a3e8, 4, 'transport-empty-census') == struct.pack('<I', 1)
                original, restored = struct.unpack('<HH', memory(address + 0x1a37c, 4, 'transport-failed-busmaster'))
                assert restored == original & ~4
                assert memory(address + 0x15400, 8, 'transport-failed-pde') == bytes(8)
                assert memory(address + 0x1e000, 24, 'transport-failed-pte') == bytes(24)
                return dict(Case='normal', Passed=True, DesktopSession=True, UserCpl=3,
                            XhciTimerFailureVerified=not empty_ports,
                            XhciEmptyPortsTimeoutVerified=empty_ports, XhciNoOpCompleted=False,
                            XhciControllerStopped=True, XhciBusMasterRevoked=True,
                            ReportsPanelVerified=reports_panel,
                            XhciHidConfigured=False, CpuL1=cache)
            if (prefix.parent.parent / 'xhci-ep0-stall.txt').is_file():
                assert memory(address + 0x1a3e0, 4, 'ep0-failed-phase') == struct.pack('<I', 23)
                assert memory(address + 0x1a379, 2, 'ep0-failed-stop') == bytes([1, 1])
                words = struct.unpack('<Q', memory(address + 0x1a3d0, 8, 'ep0-failed-event'))[0]
                assert words >> 24 & 255 == 6, 'Expected an actual Stall Error from QEMU USB device'
                assert memory(address + 0x1a384, 1, 'ep0-no-descriptor') == bytes(1)
                assert memory(address + 0x1a3c8, 1, 'ep0-no-live-hid') == bytes(1)
                original, restored = struct.unpack('<HH', memory(address + 0x1a37c, 4, 'ep0-failed-busmaster'))
                assert restored == original & ~4
                assert memory(address + 0x15400, 8, 'ep0-failed-pde') == bytes(8)
                assert memory(address + 0x1e000, 24, 'ep0-failed-pte') == bytes(24)
                if reports_panel:
                    assert logical(24, 254, 0xff6b7a)
                    check_report_hex(220, 322, 6, 2)
                    check_report_hex(440, 322, 32, 2)
                    endpoint = struct.unpack_from('<Q', reserved, 0x5820)[0]
                    check_report_hex(306, 322, endpoint & 7, 2)
                    check_report_hex(554, 322, endpoint >> 48, 4)
                    check_report_hex(80, 338, struct.unpack_from('<Q', reserved, 0x5828)[0], 8)
                    check_report_hex(304, 338, struct.unpack_from('<Q', reserved, 0x5048)[0], 8)
                command('screendump', {'filename': str(prefix) + '-ep0-stall.png', 'format': 'png'})
                return dict(Case='normal', Passed=True, UserCpl=3, XhciEp0StallVerified=True,
                            UsbCompletionCode=6, ReportsRawCodeVerified=reports_panel,
                            XhciControllerStopped=True, XhciBusMasterRevoked=True,
                            XhciHidConfigured=False, CpuL1=cache)
            assert memory(address + 0x1a379, 2, 'transport-completed-halted') == b'\x01\x01'
            if selected_root and selected_root > 2:
                assert memory(address + 0x1a3e0, 4, 'root-unavailable-phase') == struct.pack('<I', 20)
                assert memory(address + 0x1a380, 5, 'root-no-fallback') == bytes(5)
                original, restored = struct.unpack('<HH', memory(address + 0x1a37c, 4, 'root-stop-busmaster'))
                assert restored == original & ~4
                assert memory(address + 0x1e000, 24, 'root-unmapped-pte') == bytes(24)
                assert memory(address + 0x15400, 8, 'root-unmapped-pde') == bytes(8)
                return dict(Case='normal', Passed=True, UserCpl=3, RootPort=selected_root,
                            RootPortUnavailableVerified=True, RootPortFallback=False,
                            XhciControllerStopped=True, XhciBusMasterRevoked=True,
                            XhciHidConfigured=False, CpuL1=cache)
            if reports_panel:
                if not logical(24, 254, 0xffd166):
                    devs = [dev for bus in command('query-pci') for dev in bus['devices']]
                    xhc = next(dev for dev in devs if dev['class_info']['class'] == 0x0c03)
                    base_mmio = next(region['address'] for region in xhc['regions'] if region['bar'] == 0)
                    caplen = memory(address + 0x1a370, 1, 'failed-caplen')[0]
                    portsc = command('human-monitor-command', {'command-line': f'xp /16wx {base_mmio + caplen + 0x400:#x}'})
                    detail = memory(address + 0x1a370, 24, 'failed-caps-device').hex()
                    phase = memory(address + 0x1a3e0, 4, 'failed-phase').hex()
                    raise AssertionError(f'Falta hito parcial REPORTES; caps/device={detail}; phase={phase}; PORTSC: ' + portsc)
                assert logical(600, 340, 0x232638), 'Falta el panel de siguiente paso'
                def pulse_pixels():
                    return memory(fb + (264*scale*pitch + 470*scale)*4,
                                  (11*scale*pitch + 130*scale)*4, 'reports-pulse')
                first_pulse = pulse_pixels()
                wait_until(lambda: pulse_pixels() != first_pulse)
            assert memory(address + 0x1a3e0, 4, 'transport-state') == struct.pack('<I', 28 if enum_probe else 8)
            if enum_probe:
                speed = 1 if (prefix.parent.parent / 'usb-full-speed.txt').is_file() else 3
                root_port = selected_root or 5
                assert memory(address + 0x1a380, 5, 'enum-device-state') == bytes([root_port, speed, 1, 1, 1])
                descriptor = reserved[0x4e20:0x4e32]
                assert descriptor[:2] == bytes([18, 1]) and descriptor[7] == (8 if speed == 1 else 64) and descriptor[17] >= 1
                total = struct.unpack('<I', memory(address + 0x1a38c, 4, 'enum-configuration-size'))[0]
                config = reserved[0x4c00:0x4c00 + total]
                assert 9 <= total <= 512 and config[:4] == struct.pack('<BBH', 9, 2, total)
                protocol = 2 if selected_root == 2 else 1
                assert config[9:11] == bytes([9, 4]) and config[14:17] == bytes([3, 1, protocol])
                assert struct.unpack_from('<I', reserved, 0x4804)[0] == 8 << 16
                assert struct.unpack_from('<I', reserved, 0x4834)[0] == 18 << 16
                assert struct.unpack_from('<I', reserved, 0x103c)[0] == 0x01003401
                assert struct.unpack_from('<I', reserved, 0x580c)[0] >> 27 & 0x1f == 2
                if reports_panel:
                    check_report_hex(54, 322, root_port, 2)
                    check_report_hex(128, 322, speed, 2)
                    check_report_hex(220, 322, 1, 2)
                    endpoint = struct.unpack_from('<Q', reserved, 0x5820)[0]
                    assert endpoint & 7 == 1 and endpoint >> 48 == descriptor[7]
                    check_report_hex(306, 322, endpoint & 7, 2)
                    check_report_hex(440, 322, 32, 2)
                    check_report_hex(554, 322, descriptor[7], 4)
                    check_report_hex(80, 338, struct.unpack_from('<Q', reserved, 0x5828)[0], 8)
                    check_report_hex(304, 338, struct.unpack_from('<Q', reserved, 0x5048)[0], 8)
                    check_report_hex(462, 338, dma + 0x48b0, 8)
            else:
                assert memory(address + 0x1a380, 8, 'transport-no-device-slots') == bytes(8)
            assert memory(address + 0x1a3c8, 1, 'transport-no-live-hid') == bytes(1)
            assert struct.unpack_from('<I', reserved, 0x100c)[0] == 0x5c01
            events = [struct.unpack_from('<QII', reserved, offset) for offset in range(0x2000, 0x2100, 16)]
            completions = [event for event in events if event[2] & 0xfc01 == 0x8401]
            assert len(completions) == (4 if enum_probe else 1) and completions[0][0] == dma + 0x1000
            assert completions[0][1] >> 24 == 1
            if not enum_probe:
                assert reserved[0x4000:0x6000] == bytes(0x2000), 'El perfil de transporte no enumera dispositivos'
            original, restored = struct.unpack('<HH', memory(address + 0x1a37c, 4, 'transport-busmaster'))
            assert restored == original & ~4
            assert memory(address + 0x15400, 8, 'transport-alias-pde') == bytes(8)
            assert memory(address + 0x1e000, 24, 'transport-alias-pte') == bytes(24)
            assert memory(address + 0x1a3e8, 4, 'transport-connected-ports') == struct.pack('<I', 3)
            settle_slices = struct.unpack('<I', memory(address + 0x1a3fc, 4, 'transport-real-time-slices'))[0]
            assert (33 if enum_probe else 11) <= settle_slices <= 100
            running_status = struct.unpack('<I', memory(address + 0x1a3ec, 4, 'transport-census-status'))[0]
            assert running_status & 0x801 == 0, 'El censo requiere xHC activo y CNR despejado'
            devices = [device for bus in command('query-pci') for device in bus['devices']]
            controller = next(device for device in devices if device['class_info']['class'] == 0x0c03)
            bdf = controller['bus'] << 8 | controller['slot'] << 3 | controller['function']
            assert memory(address + 0x1a360, 4, 'transport-selected-pci') == struct.pack('<I', bdf)
            assert memory(address + 0x1a3b9, 1, 'transport-reset-stage') == b'\x03'
            assert memory(address + 0x1a3f0, 8, 'transport-register-offsets') == struct.pack('<II', 0x1000, 0x2000)
            bar = next(region['address'] for region in controller['regions'] if region['bar'] == 0)
            caps = struct.unpack('<I', memory(address + 0x1a370, 4, 'transport-caps'))[0]
            status = command('human-monitor-command', {'command-line': f'xp /1wx {bar + (caps & 255) + 4:#x}'})
            assert int(status.split(':', 1)[1].split()[0], 16) & 1
            command('screendump', {'filename': str(prefix) + '-usb-transport.png', 'format': 'png'})
            return dict(Case='normal', Passed=True, DesktopSession=True, UserCpl=3,
                        XhciTransportVerified=True, XhciNoOpCompleted=True, XhciControllerStopped=True,
                        XhciBusMasterRevoked=True, XhciReservedBytes=pages * 4096,
                        XhciConnectedPorts=2, XhciHidConfigured=False, CpuL1=cache,
                        XhciDeviceDescriptorVerified=enum_probe, XhciConfigurationRead=enum_probe,
                        XhciFirstDescriptorBytes=8 if enum_probe else 0,
                        XhciEp0Evaluated=enum_probe,
                        UsbRootPort=selected_root,
                        ReportsPanelVerified=reports_panel, ReportsPulseUpdated=reports_panel,
                        UsbDeviceDescriptor=descriptor.hex() if enum_probe else None,
                        UsbConfiguration=config.hex() if enum_probe else None,
                        XhciPortSettleMilliseconds=settle_slices * 10,
                        XhciAdaptiveDebounceVerified=True, XhciRunningCensusVerified=True)
        if command_probe:
            assert memory(address + 0x1a3c4, 1, 'xhci-dma-validated') == b'\x01'
            status = memory(address + 0x1a379, 2, 'xhci-command-status')
            assert status == b'\x01\x00', f'xHCI command/stop status: {status.hex()}'
            # The live keyboard can overwrite the initial No Op completion.
            # Ring 0 recorded its successful type, status and pointer check.
            assert struct.unpack_from('<I', reserved, 0x100c)[0] == 0x5c01
            assert struct.unpack_from('<Q', reserved, 0x4940)[0] == dma + 0x4900
            device_state = tuple(memory(address + 0x1a380, 5, 'xhci-device'))
            port, speed, slot, addressed, descriptor_read = device_state
            expected_speed = 1 if (prefix.parent.parent / 'usb-full-speed.txt').is_file() else 3
            assert port and speed == expected_speed and slot == addressed == descriptor_read == 1, device_state
            assert struct.unpack_from('<Q', reserved, 8)[0] == dma + 0x5800
            output_slot = struct.unpack_from('<I', reserved, 0x580c)[0]
            assert (output_slot >> 27) & 0x1f == 3 and output_slot & 0xff
            descriptor = reserved[0x4c00:0x4c12]
            assert descriptor[:2] == bytes([18, 1]) and descriptor[17] >= 1
            assert memory(address + 0x1a385, 3, 'xhci-keyboard-state') == bytes([1, 1, 1])
            total, config, interface, endpoint = struct.unpack(
                '<IBBB', memory(address + 0x1a38c, 7, 'xhci-keyboard-config'))
            data = reserved[0x4c40:0x4c40 + total]
            assert len(data) == total and data[:5] == struct.pack('<BBHB', 9, 2, total, 1)
            assert config == data[5] and endpoint & 0x80
            report_count = memory(address + 0x1a397, 1, 'xhci-report-state')[0]
            reports = [reserved[offset:offset + 8] for offset in range(0x4e80, 0x4ea0, 8)]
            if mouse_probe:
                assert report_count == 4
                assert [report[:3] for report in reports] == [
                    b'\x00\x64\x00', b'\x01\x00\x00', b'\x00\x00\x00', b'\x00\xe7\xe2',
                ]
            else:
                assert report_count == 4
                assert reports == [bytes([0, 0, usage, 0, 0, 0, 0, 0]) for usage in (0x3c, 0, 0x3c, 0)]
            assert wait_stats()[0] > 0
        else:
            assert reserved == bytes(pages * 4096)
        count = 2 if command_probe else 1
        assert int(match[3], 16) == count
        assert memory(address + 0x1a358, 5, 'xhci-inventory') == struct.pack('<IB', count, 1)
        bdf, low, high = struct.unpack('<III', memory(address + 0x1a360, 12, 'xhci-pci'))
        devices = [device for bus in command('query-pci') for device in bus['devices']]
        controllers = sorted((device for device in devices if device['class_info']['class'] == 0x0c03),
                             key=lambda device: (device['bus'], device['slot'], device['function']))
        assert len(controllers) == count
        controller = controllers[-1]
        assert bdf == (controller['bus'] << 8 | controller['slot'] << 3 | controller['function'])
        pci_id = controller['id']['device'] << 16 | controller['id']['vendor']
        pci_command = struct.unpack('<H', memory(address + 0x1a36c, 2, 'xhci-pci-command-inventory'))[0]
        pci_row = match[4].splitlines()[count - 1].split()
        assert tuple(int(field, 16) for field in pci_row) == (bdf, pci_id, pci_command, low, high)
        rank = struct.unpack('<I', memory(address + 0x1a3b0, 4, 'xhci-rank'))[0]
        assert rank == (3 if reset_probe else count)
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
        actual = command('human-monitor-command', {'command-line': f'xp /2wx {bar:#x}'})
        words = actual.split(':', 1)[1].split()
        assert (caps, parameters) == tuple(int(word, 16) for word in words[:2])
        assert caps >> 16 and parameters & 0xff
        requirements = command('human-monitor-command', {'command-line': f'xp /3wx {bar + 8:#x}'})
        params2, _, cap1 = (int(word, 16) for word in requirements.split(':', 1)[1].split()[:3])
        scratchpads, context_bytes = struct.unpack('<II', memory(address + 0x1a3bc, 8, 'xhci-dma-needs'))
        assert scratchpads == ((params2 >> 27) | ((params2 >> 16) & 0x3e0))
        assert context_bytes == (64 if cap1 & 4 else 32)
        if command_probe:
            packet_size, interval = struct.unpack_from('<HB', data, data.index(bytes([7, 5, endpoint])) + 4)
            expected_interval = interval - 1 if speed == 3 else interval.bit_length() + 2
            input_control = struct.unpack_from('<II', reserved, 0x5000)
            assert input_control == (0, 9)
            slot_context = struct.unpack_from('<I', reserved, 0x5000 + context_bytes)[0]
            assert slot_context >> 27 == 3 and (slot_context >> 20) & 0xf == speed
            endpoint_context = struct.unpack_from('<IIQI', reserved, 0x5000 + 4*context_bytes)
            assert endpoint_context == (expected_interval << 16, packet_size << 16 | 0x3e,
                                        dma + 0x4901, packet_size << 16 | packet_size)
            assert struct.unpack_from('<Q', reserved)[0] == (dma + 0x800 if scratchpads else 0)
            assert struct.unpack_from('<4Q', reserved, 0x800) == tuple(
                dma + page * 4096 for page in range(6, 10))
            if not scratchpads:
                assert reserved[0x6000:] == bytes(4 * 4096)
        reset_stage = memory(address + 0x1a3b9, 1, 'xhci-reset-stage')[0]
        assert reset_stage == (3 if command_probe or reset_probe else 0)
        handoff = memory(address + 0x1a378, 1, 'xhci-handoff')[0]
        assert handoff in (1, 2), f'xHCI handoff state: {handoff}'
        if not command_probe:
            assert memory(address + 0x15400, 8, 'xhci-alias-pde') == bytes(8)
            assert memory(address + 0x1e000, 24, 'xhci-alias-pte') == bytes(24)
            status, page_mask, preflight = struct.unpack('<III', memory(address + 0x1a3d8, 12, 'xhci-preflight'))
            operational = bar + (caps & 0xff)
            actual = command('human-monitor-command', {'command-line': f'xp /2wx {operational + 4:#x}'})
            words = [int(value, 16) for value in actual.split(':', 1)[1].split()[:2]]
            assert page_mask == words[1] and (status ^ words[0]) & 0x801 == 0
            expected_state = 1 if status & 0x800 else 2 if not page_mask & 1 else 3 if status & 1 else 4
            if reset_probe:
                assert preflight == 7 and expected_state == 3
                assert memory(address + 0x1a379, 2, 'reset-only-command-state') == bytes(2)
                assert reserved == bytes(pages * 4096)
                reported_ports = struct.unpack('<I', memory(address + 0x1a3e8, 4, 'post-reset-ports'))[0]
                ports = []
                for i in range(parameters >> 24):
                    result = command('human-monitor-command', {'command-line': f'xp /1wx {operational+0x400+i*16:#x}'})
                    ports.append(int(result.split(':', 1)[1].split()[0], 16))
                assert reported_ports == sum(port & 1 for port in ports) + 1 == 3
                assert logical(24, 354, 0x232638)
                command('screendump', {'filename': str(prefix) + '-usb-ports.png', 'format': 'png'})
                return dict(Case='normal', Passed=True, DesktopSession=True, UserCpl=3,
                            XhciResetOnlyVerified=True, XhciConnectedPortsAfterReset=reported_ports - 1,
                            XhciSelectedBdf=f'{bdf:04X}', CpuL1=cache)
            else:
                assert preflight == expected_state
        if not command_probe:
            assert logical(24, 354, 0x232638), 'El escritorio no mostro el aviso de entrada USB'
        if command_probe:
            if mouse_probe:
                key('f2')
                wait_until(lambda: logical(40, 86, 0x40465d))
            for letter in 'session exit':
                key('spc' if letter == ' ' else letter)
            key('ret')
            def closed_usb_session():
                regs = registers()
                return ('CPL=0' in regs and 'HLT=1' in regs and register(regs, 'R12') == 5
                        and not register(regs, 'EFER') & 1)
            wait_until(closed_usb_session)
            assert memory(address + 0x1a3c8, 1, 'xhci-live-after-exit') == bytes(1)
            assert memory(address + 0x1a37a, 1, 'xhci-stop-after-exit') == b'\x01'
            original, restored = struct.unpack('<HH', memory(address + 0x1a37c, 4, 'xhci-pci-command'))
            assert original == restored, 'El comando PCI no se restauro'
            usb_status = command('human-monitor-command', {'command-line': f'xp /1wx {status_register:#x}'})
            assert int(usb_status.split(':', 1)[1].split()[0], 16) & 1
            assert memory(address + 0x15400, 8, 'xhci-alias-pde') == bytes(8)
            assert memory(address + 0x1e000, 24, 'xhci-alias-pte') == bytes(24)
            assert memory(address + 0x17000, 40, 'usb-closed-pte') == bytes(40)
            result = dict(Case='normal', Passed=True, UserCpl=3, DesktopSession=True,
                        XhciCommandCompleted=True, XhciUsbDeviceAddressed=True,
                        XhciUsbDeviceDescriptorRead=True, XhciPort=port, XhciSpeed=speed,
                        XhciSlot=slot, XhciControllerStopped=True,
                        UsbConfigurationBytes=total, UsbBootProtocolSelected=True,
                        UsbDeviceDescriptor=descriptor.hex(),
                        UsbSessionExitVerified=True,
                        UsbInputVerified=True, UsbCabinaVerified=True, CpuL1=cache,
                        XhciControllers=count, XhciSelectedBdf=f'{bdf:04X}', XhciConnectedPorts=rank-1,
                        XhciResetStage=reset_stage, XhciScratchpadPages=scratchpads, XhciContextBytes=context_bytes,
                        DmaReservationValidated=True, XhciReservedBytes=pages * 4096,
                        UsbCabinaOpenedWhileControllerRunning=True, UsbWaitVerified=True,
                        XhciContextLayoutVerified=True,
                        XhciScratchpadCapacityPages=4, XhciScratchpadTableVerified=True)
            if mouse_probe:
                result.update(UsbBootMouseInterface=interface, UsbMouseEndpoint=endpoint,
                              UsbMouseReportsBeforeExit=report_count, UsbMouseVerified=True,
                              UsbMouseFinalReports=[report.hex() for report in reports],
                              XhciMouseInterval=expected_interval)
            else:
                result.update(UsbBootKeyboardInterface=interface, UsbKeyboardEndpoint=endpoint,
                              UsbKeyboardReportsBeforeExit=260, UsbKeyboardRingWrapVerified=True,
                              UsbKeyboardFinalReports=[report.hex() for report in reports],
                              UsbKeyboardTransferVerified=True, XhciKeyboardInterval=expected_interval)
            return result
    timeout_before = wait_stats()[1]
    wait_until(lambda: wait_stats()[1] > timeout_before)
    event_before = wait_stats()[0]
    assert pixel(width-1, height-1, 0x0d0e17), 'La intro no fue reemplazada'
    assert memory(code, len(packet)-24, 'session-code') == packet[24:]
    if external_image is not None:
        assert external_image not in packet, 'SBEF externo embebido en el paquete'
        if count == 3:
            data_region = mapping_plan['Regions'][2]
            assert (data_region['FileBytes'], data_region['MemoryBytes']) == (4, 8)
            assert external_image[data_region['FileOffset']:data_region['FileEnd']] == struct.pack('<I', 0x424d4f32)
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
        closed = dict(SessionClosed=True, SyscallGateDisabled=True,
                      UserPagesUnmapped=map_evidence['SbefMappedPagesVerified'] + 1,
                      UserBytesScrubbed=20480)
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
                **map_evidence,
                ReadOnlyNxRegionVerified=external_image is not None and count >= 2,
                WritableNxRegionVerified=external_image is not None and count == 3,
                UserDataAndBssVerified=external_image is not None and count == 3,
                CabinaCommandsVerified=4 if external_image is not None else 0,
                SettingsVerified=external_image is not None,
                XhciInventoryVerified=desktop_media,
                XhciScratchpadPages=scratchpads if desktop_media else None,
                XhciContextBytes=context_bytes if desktop_media else None,
                XhciReadOnlyMmioVerified=desktop_media,
                XhciFirmwareHandoff=handoff if desktop_media else None,
                XhciPreflight=preflight if desktop_media else None,
                XhciResetOnlyVerified=reset_probe,
                XhciCommandCompleted=desktop_media and command_probe,
                XhciReservedBytes=pages * 4096 if desktop_media else 0,
                DesktopStagingBytes=staging_pages * 4096 if desktop_media else None,
                DesktopStagingReturnedBytes=(5 - staging_pages) * 4096 if desktop_media else None,
                PayloadSHA256=hashlib.sha256(packet[24:]).hexdigest(),
                SbefSHA256=fixture['sbef_sha256'], CpuL1=cache,
                BootInputIndicatorsVerified=external_image is not None, **closed)
