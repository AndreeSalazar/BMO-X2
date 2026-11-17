"""Observe the external MSVC fixture and its clock from QEMU."""
import json
import hashlib
from pathlib import Path
import struct
import time

from cpu_config import register
from desktop_session_capture import verify_external_rejection


def verify_sections(command, memory, prefix, image, case, symbols_path):
    if case == 'external-permissions':
        result = verify_external_rejection(command, memory, image)
        if memory(0x4000000, 4096, 'msvc-rejected-text') != bytes(4096):
            raise ValueError('MSVC text copied before admission')
        return result
    symbols = json.loads(symbols_path.read_text(encoding='ascii'))
    rw_end = 0x40400000 + struct.unpack_from('<I', image, 112)[0]
    fields = [('phase', 8), ('first_ms', 8), ('second_ms', 8), ('scratch', 6000), ('written', 4)]
    if 'director_pixels' in symbols:
        fields.extend((('director_pixels', 320*200*4), ('director_state', 8)))
    if any(not 0x40400000 <= symbols[name] <= rw_end - size for name, size in fields):
        raise ValueError('MSVC fixture symbols outside RW budget')

    def word(name):
        return struct.unpack('<Q', memory(symbols[name] - 0x3c000000, 8, name))[0]

    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        if word('phase') == 0x53454332:
            if 'director_pixels' not in symbols:
                regs = command('human-monitor-command', {'command-line': 'info registers'})
                if 'CPL=3' not in regs or not 0x40000000 <= register(regs, 'RIP') < 0x40200000:
                    raise ValueError('MSVC fixture outside CPL3')
            first, second = word('first_ms'), word('second_ms')
            scratch = memory(symbols['scratch'] - 0x3c000000, 6000, 'scratch')
            if second < first + 20 or scratch != b'\0M' + bytes(5998):
                raise ValueError('MSVC clock or data verification failed')
            hello = b'Hola mundo desde C++ / MSVC en BMO-X2\r\n'
            serial = Path(str(prefix)+'-serial.log').read_bytes()
            written = struct.unpack('<I', memory(symbols['written'] - 0x3c000000, 4, 'written'))[0]
            if serial.count(hello) != 1 or written != len(hello):
                raise ValueError('MSVC stdout mismatch')
            result = dict(Case='normal', Passed=True, Evidence='QEMU', CPL=3,
                        InitializedDataVerified=True, ZeroFillVerified=True,
                        RustClockVerified=True, FirstMs=first, SecondMs=second,
                        SerialHelloVerified=True, WrittenBytes=written)
            if 'director_pixels' in symbols:
                result.update(verify_director(command, memory, prefix, symbols, word))
            return result
        time.sleep(.03)
    raise ValueError('MSVC session fixture never completed')


def verify_director(command, memory, prefix, symbols, word):
    def wait_for(state):
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if word('director_state') == state:
                return
            time.sleep(.02)
        raise ValueError(f'DIRECTOR did not publish state {state}')

    def key(*names):
        command('send-key', {'keys': [{'type': 'qcode', 'data': name} for name in names],
                             'hold-time': 80})

    address = symbols['director_pixels']
    wait_for(3)
    before = capture_window(command, memory, prefix, address, 'msvc-open', True)
    key('meta_l', 'q')
    wait_for(4)
    closed = capture_window(command, memory, prefix, address, 'msvc-closed', False)
    time.sleep(.12)
    key('f1')
    wait_for(7)
    reopened = capture_window(command, memory, prefix, address, 'msvc-window', True)
    if reopened['ScreenshotSHA256'] != before['ScreenshotSHA256']:
        raise ValueError('DIRECTOR did not reproduce the original frame')
    return dict(DirectorCloseVerified=True, DirectorReopenVerified=True,
                ClosedScreenshotSHA256=closed['ScreenshotSHA256'], **reopened)


def capture_window(command, memory, prefix, address, label, visible):
    if not 0x40400000 <= address <= 0x40600000 - 320*200*4:
        raise ValueError('MSVC frame buffer outside RW region')
    raw = memory(address - 0x3c000000, 320*200*4, label+'-pixels')
    samples = ((26, 50, 0x202c49), (256, 90, 0x74e0ce)) if visible else ((26, 50, 0x0e1325),)
    for x, y, color in ((0, 0, 0x10192b), *samples):
        if struct.unpack_from('<I', raw, (y*320+x)*4)[0] != color:
            raise ValueError('MSVC window color mismatch')
    path = Path(str(prefix)+'-'+label+'.ppm')
    command('screendump', {'filename': str(path)})
    screenshot = path.read_bytes()
    magic, dimensions, maximum, rgb = screenshot.split(b'\n', 3)
    width, height = map(int, dimensions.split())
    if magic != b'P6' or maximum != b'255' or len(rgb) != width*height*3:
        raise ValueError('Invalid MSVC QEMU screenshot')
    scale = min(width // 320, height // 200)
    if not scale:
        raise ValueError('Invalid MSVC GOP scale')
    x, y = (width - 320*scale)//2, (height - 200*scale)//2
    for row in range(200):
        pixels = [raw[n:n+3][::-1] for n in range(row*1280, (row+1)*1280, 4)]
        expected = b''.join(pixel*scale for pixel in pixels)
        for repeat in range(scale):
            at = ((y + row*scale + repeat)*width + x)*3
            if rgb[at:at+len(expected)] != expected:
                raise ValueError(f'MSVC presentation mismatch at row {row}')
    return dict(WindowFrameVerified=True, WindowPixelsVerified=320*200*scale*scale,
                Screenshot=path.name, ScreenshotSHA256=hashlib.sha256(screenshot).hexdigest())
